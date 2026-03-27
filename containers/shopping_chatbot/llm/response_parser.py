"""
Parses the raw LLM text output into structured fields.

Expected LLM output format:
    INTENT: <intent_name>
    SQL: <select query>          ← READ intents only
    ACTION_PARAMS: <json object> ← WRITE intents only
"""

import re
import json
import logging

logger = logging.getLogger(__name__)

READ_INTENTS  = {"search_product", "filter_product", "view_product", "view_cart"}
WRITE_INTENTS = {"add_to_cart", "remove_from_cart", "update_cart_qty",
                 "place_order", "confirm_order", "cancel_order"}
ALL_INTENTS   = READ_INTENTS | WRITE_INTENTS | {"general_question"}


class ParsedLLMResponse:
    def __init__(
        self,
        intent: str,
        sql: str | None             = None,
        action_params: dict | None  = None,
        raw: str                    = "",
    ):
        self.intent        = intent
        self.sql           = sql
        self.action_params = action_params or {}
        self.raw           = raw

    @property
    def is_read(self):  return self.intent in READ_INTENTS
    @property
    def is_write(self): return self.intent in WRITE_INTENTS

    def __repr__(self):
        return (f"<ParsedLLMResponse intent={self.intent} "
                f"sql={'yes' if self.sql else 'no'} "
                f"action_params={self.action_params}>")


# ── JSON parsing helpers ──────────────────────────────────────────────────────

def _safe_parse_json(raw: str) -> dict:
    """
    Try multiple strategies to parse a JSON-like string from LLM output.
    LLMs often produce: single quotes, trailing commas, unquoted keys,
    Python-style True/False/None instead of true/false/null.
    """
    if not raw or not raw.strip():
        return {}

    # Strategy 1 — standard JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — fix common LLM JSON mistakes
    fixed = raw.strip()
    fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)          # single → double quotes
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)           # trailing commas
    fixed = fixed.replace("True", "true").replace("False", "false").replace("None", "null")
    fixed = re.sub(r'(\b\w+\b)\s*:', r'"\1":', fixed)     # unquoted keys
    fixed = re.sub(r'""(\w+)""', r'"\1"', fixed)          # double-double quotes

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Strategy 3 — extract key:value pairs manually with regex
    result = {}
    pairs = re.findall(
        r'''["\']?(\w+)["\']?\s*:\s*(["\']?)([^,}\n]+?)\2\s*(?:[,}]|$)''',
        raw
    )
    for key, _, value in pairs:
        value = value.strip().strip("'\"")
        if value.lower() == "true":       result[key] = True
        elif value.lower() == "false":    result[key] = False
        elif value.lower() in ("null", "none"): result[key] = None
        elif re.match(r"^-?\d+$", value): result[key] = int(value)
        elif re.match(r"^-?\d+\.\d+$", value): result[key] = float(value)
        else:                             result[key] = value

    if result:
        logger.debug(f"ACTION_PARAMS recovered via regex: {result}")
        return result

    logger.warning(f"All JSON parse strategies failed for: {raw[:100]}")
    return {}


def _extract_params_from_text(text: str, intent: str) -> dict:
    """
    Last-resort fallback: extract known fields directly from raw LLM text
    when no JSON block was found at all.
    """
    result = {}

    # product_id
    pid = re.search(r'product_id["\s:]+(\d+)', text, re.IGNORECASE)
    if pid:
        result["product_id"] = int(pid.group(1))

    # ordinal references: "first one" → item_index 0
    ordinal_map = {
        "first": 0, "second": 1, "third": 2, "fourth": 3,
        "fifth": 4, "1st": 0, "2nd": 1, "3rd": 2,
    }
    for word, idx in ordinal_map.items():
        if re.search(rf'\b{word}\b', text, re.IGNORECASE):
            result["item_index"] = idx
            break

    # qty
    qty = re.search(r'\bqty["\s:]+(\d+)', text, re.IGNORECASE)
    if qty:
        result["qty"] = int(qty.group(1))

    # confirm flag
    if intent == "confirm_order":
        result["confirm"] = True
    elif intent == "place_order":
        result["confirm"] = False

    # new_qty
    nq = re.search(r'new_qty["\s:]+(\d+)', text, re.IGNORECASE)
    if nq:
        result["new_qty"] = int(nq.group(1))

    if result:
        logger.debug(f"ACTION_PARAMS recovered from text: {result}")
    return result


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_llm_output(raw_text: str, session_id: str) -> ParsedLLMResponse:
    """
    Parse LLM output into a ParsedLLMResponse.
    Falls back gracefully on malformed output.
    """
    text = raw_text.strip()
    logger.debug(f"Raw LLM output:\n{text[:500]}")

    # ── Extract INTENT ────────────────────────────────────────────────────────
    intent_match = re.search(r"INTENT:\s*(\w+)", text, re.IGNORECASE)
    if not intent_match:
        logger.warning(f"No INTENT found in LLM output: {text[:200]}")
        return ParsedLLMResponse(intent="general_question", raw=text)

    intent = intent_match.group(1).lower().strip()
    if intent not in ALL_INTENTS:
        logger.warning(f"Unknown intent '{intent}', defaulting to general_question")
        intent = "general_question"

    # ── Extract SQL (READ intents) ────────────────────────────────────────────
    sql = None
    if intent in READ_INTENTS:
        sql_match = re.search(
            r"SQL:\s*(SELECT[\s\S]+?)(?:\n\n|ACTION_PARAMS:|$)",
            text, re.IGNORECASE
        )
        if sql_match:
            sql = sql_match.group(1).strip().rstrip(";") + ";"
            # Replace quoted placeholder first to avoid double-quoting
            sql = sql.replace("'{session_id}'", f"'{session_id}'")
            sql = sql.replace("{session_id}", f"'{session_id}'")
            first_word = sql.strip().split()[0].upper()
            if first_word != "SELECT":
                logger.error(f"LLM tried non-SELECT SQL: {sql[:100]}")
                sql = None
        else:
            logger.warning(f"READ intent '{intent}' but no SQL found in output")

    # ── Extract ACTION_PARAMS (WRITE intents) ─────────────────────────────────
    action_params = {}
    if intent in WRITE_INTENTS:

        ap_match = re.search(r"ACTION_PARAMS:\s*(\{[\s\S]+?\})", text, re.IGNORECASE)
        if ap_match:
            action_params = _safe_parse_json(ap_match.group(1))
            if not action_params:
                logger.warning("ACTION_PARAMS block found but could not be parsed")

        # No JSON block found — scan full text for known field patterns
        if not action_params:
            logger.warning("No ACTION_PARAMS block — attempting text extraction")
            action_params = _extract_params_from_text(text, intent)

        logger.info(f"Final action_params for intent={intent}: {action_params}")

    return ParsedLLMResponse(
        intent=intent,
        sql=sql,
        action_params=action_params,
        raw=text,
    )