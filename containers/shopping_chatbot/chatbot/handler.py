"""
Main chatbot turn handler.
Orchestrates: session → LLM → parse → execute → format → response
"""

import logging
from sqlalchemy.orm import Session

from chatbot import session as session_store
from chatbot import executor, formatter
from database.models import ConversationLog
from llm.client import llm_client
from llm.prompt_builder import build_prompt
from llm.response_parser import parse_llm_output, READ_INTENTS

logger = logging.getLogger(__name__)


def _handle_turn_inner(user_message: str, session_id: str, db: Session) -> dict:
    """
    Process one user message end-to-end and return a response dict.

    Flow:
      1. Load session state
      2. Build LLM prompt with history + last results
      3. Call LLM → parse intent + SQL/action_params
      4. Execute (SELECT or ORM write)
      5. Format structured JSON response
      6. Persist turn to conversation log
      7. Update session state
    """

    # ── 1. Session ─────────────────────────────────────────────────────────────
    try:
        sess = session_store.get_or_create_session(session_id)
    except Exception as e:
        logger.error(f"Session init failed: {e}")
        return formatter.fmt_error("Something went wrong. Please try again.")
    sid  = sess["session_id"]   # may differ if a new session was created

    # ── 2. Build prompt ────────────────────────────────────────────────────────
    try:
        prompt = build_prompt(
            user_message          = user_message,
            history               = sess["history"],
            last_results          = sess["last_results"],
            session_id            = sid,
            awaiting_confirmation = sess["awaiting_confirmation"],
        )
    except Exception as e:
        logger.error(f"Prompt build failed: {e}")
        resp = formatter.fmt_error("Something went wrong. Please try again.")
        resp["session_id"] = sid
        return resp

    # ── 3. LLM call ────────────────────────────────────────────────────────────
    try:
        raw_llm = llm_client.generate(prompt)
    except RuntimeError as e:
        logger.error(f"LLM call failed: {e}")
        resp = formatter.fmt_error("Something went wrong. Please try again.")
        resp["session_id"] = sid
        return resp

    parsed = parse_llm_output(raw_llm, session_id=sid)
    logger.info(f"[{sid}] intent={parsed.intent}")

    # ── 4a. READ intents ────────────────────────────────────────────────────────
    response = None

    if parsed.is_read:
        if not parsed.sql:
            response = formatter.fmt_error("Could not generate a query for your request.")
        else:
            try:
                rows = executor.execute_select(db, parsed.sql)
                session_store.update_session(sid, last_results=rows)
            except Exception as e:
                logger.error(f"SELECT failed: {e}")
                response = formatter.fmt_error("Something went wrong. Please try again.")

            if response is None:
                if parsed.intent == "view_cart":
                    response = formatter.fmt_cart_view(rows, sid)
                elif parsed.intent == "view_product" and len(rows) == 1:
                    response = formatter.fmt_product_detail(rows[0])
                else:
                    response = formatter.fmt_product_list(rows)

    # ── 4b. WRITE intents ───────────────────────────────────────────────────────
    elif parsed.is_write:
        ap = parsed.action_params

        # ── add_to_cart ──────────────────────────────────────────────────────
        if parsed.intent == "add_to_cart":
            product_id = _resolve_product_id(ap, sess)
            qty        = int(ap.get("qty", 1))
            if product_id is None:
                response = formatter.fmt_error(
                    "I'm not sure which product to add. "
                    "Please mention the product name or number."
                )
            else:
                try:
                    result = executor.add_to_cart(db, sid, product_id, qty)
                    # keep cart_id in session
                    session_store.update_session(sid, cart_id=result["cart_id"])
                    response = formatter.fmt_cart_add(result)
                except ValueError as e:
                    response = formatter.fmt_error(str(e))

        # ── remove_from_cart ─────────────────────────────────────────────────
        elif parsed.intent == "remove_from_cart":
            product_id = _resolve_product_id(ap, sess)
            if product_id is None:
                response = formatter.fmt_error("Which product would you like to remove?")
            else:
                try:
                    result = executor.remove_from_cart(db, sid, product_id)
                    response = formatter.fmt_cart_remove(result)
                except ValueError as e:
                    response = formatter.fmt_error(str(e))

        # ── update_cart_qty ──────────────────────────────────────────────────
        elif parsed.intent == "update_cart_qty":
            product_id = _resolve_product_id(ap, sess)
            new_qty    = int(ap.get("new_qty", 1))
            if product_id is None:
                response = formatter.fmt_error("Which product quantity would you like to update?")
            else:
                try:
                    result = executor.update_cart_qty(db, sid, product_id, new_qty)
                    response = formatter.fmt_cart_qty_update(result)
                except ValueError as e:
                    response = formatter.fmt_error(str(e))

        # ── place_order (first time — show billing, don't confirm yet) ────────
        elif parsed.intent == "place_order":
            try:
                summary = executor.build_billing_summary(db, sid)
                session_store.update_session(
                    sid,
                    awaiting_confirmation = True,
                    pending_order_summary = summary,
                )
                response = formatter.fmt_billing_summary(summary)
            except ValueError as e:
                response = formatter.fmt_error(str(e))

        # ── confirm_order ────────────────────────────────────────────────────
        elif parsed.intent == "confirm_order":
            if not sess["awaiting_confirmation"]:
                response = formatter.fmt_general(
                    "There is no pending order to confirm."
                )
            else:
                cart_id = sess.get("cart_id") or (
                    sess["pending_order_summary"] or {}
                ).get("cart_id")
                if not cart_id:
                    response = formatter.fmt_error("Could not find your cart.")
                else:
                    try:
                        order = executor.place_order(db, sid, cart_id)
                        session_store.update_session(
                            sid,
                            awaiting_confirmation = False,
                            pending_order_summary = None,
                            cart_id               = None,
                        )
                        response = formatter.fmt_order_success(order)
                    except ValueError as e:
                        response = formatter.fmt_error(str(e))

        # ── cancel_order ─────────────────────────────────────────────────────
        elif parsed.intent == "cancel_order":
            session_store.update_session(
                sid,
                awaiting_confirmation = False,
                pending_order_summary = None,
            )
            response = formatter.fmt_cancelled()

        else:
            response = formatter.fmt_general(
                "I can help you shop! Try: 'show me cricket bats', "
                "'add to cart', or 'place order'."
            )

    # ── 4c. general_question ────────────────────────────────────────────────────
    else:
        response = formatter.fmt_general(
            "I'm your shopping assistant! Ask me to find products, "
            "add them to your cart, or place an order."
        )

    # ── 5. Log turn ─────────────────────────────────────────────────────────────
    turn_number = len(sess["history"]) // 2 + 1
    try:
        db.add(ConversationLog(
            session_id    = sid,
            turn          = turn_number,
            user_message  = user_message,
            intent        = parsed.intent,
            generated_sql = parsed.sql,
            response_type = response.get("response_type"),
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save conversation log: {e}")

    # ── 6. Update session history ───────────────────────────────────────────────
    session_store.append_history(sid, "user",      user_message)
    session_store.append_history(sid, "assistant", response.get("message", ""))

    # Attach session_id so client can track it
    response["session_id"] = sid
    return response


def handle_turn(user_message: str, session_id: str, db: Session) -> dict:
    """Wrapper that guarantees a safe chat-shaped response even on unexpected errors."""
    try:
        return _handle_turn_inner(user_message, session_id, db)
    except Exception as e:
        logger.exception(f"Unhandled error in handle_turn: {e}")
        return formatter.fmt_error("Something went wrong. Please try again.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_product_id(action_params: dict, sess: dict) -> int | None:
    """
    Resolve product_id from action_params.
    Handles:
      - Direct product_id integer in action_params
      - item_index reference ("first one" -> index 0 in last_results)
      - Gracefully ignores non-integer placeholder strings from LLM
    """
    last_results = sess.get("last_results", [])

    # Direct product_id — guard against LLM returning placeholder strings
    if "product_id" in action_params:
        raw = action_params["product_id"]
        try:
            pid = int(raw)
            return pid
        except (ValueError, TypeError):
            # LLM returned a placeholder like "<id of first product>" — ignore it
            # and fall through to item_index or positional fallback
            import logging
            logging.getLogger(__name__).warning(
                f"product_id '{raw}' is not a valid integer — falling back to index"
            )

    # item_index reference
    if "item_index" in action_params:
        try:
            idx = int(action_params["item_index"])
            if 0 <= idx < len(last_results):
                return last_results[idx].get("id")
        except (ValueError, TypeError):
            pass

    # Last resort: if no explicit index given but last_results has items,
    # default to first result (covers "add it" / "add that one" phrasing)
    if last_results and "product_id" not in action_params and "item_index" not in action_params:
        import logging
        logging.getLogger(__name__).info(
            "No product_id or item_index — defaulting to first result"
        )
        return last_results[0].get("id")

    return None