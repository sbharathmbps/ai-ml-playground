"""
Converts raw DB results and action outcomes into the standardised
JSON response envelope the frontend consumes.

Every response has the shape:
{
    "response_type": "<type>",
    "message":       "<human readable summary>",
    "data":          { ... },
    "meta":          { ... }
}
"""

from __future__ import annotations


def _envelope(response_type: str, message: str, data, meta: dict | None = None) -> dict:
    return {
        "response_type": response_type,
        "message":       message,
        "data":          data,
        "meta":          meta or {},
    }


# ── Product list ──────────────────────────────────────────────────────────────

def fmt_product_list(rows: list[dict], filters_applied: dict | None = None) -> dict:
    count = len(rows)
    if count == 0:
        msg = "No products found matching your search."
    elif count == 1:
        msg = "Found 1 product."
    else:
        msg = f"Found {count} products."

    return _envelope(
        response_type = "product_list",
        message       = msg,
        data          = rows,
        meta          = {
            "total":           count,
            "filters_applied": filters_applied or {},
        },
    )


# ── Single product detail ─────────────────────────────────────────────────────

def fmt_product_detail(row: dict) -> dict:
    return _envelope(
        response_type = "product_detail",
        message       = f"Here are the details for {row.get('name', 'this product')}.",
        data          = row,
    )


# ── Cart view ─────────────────────────────────────────────────────────────────

def fmt_cart_view(rows: list[dict], session_id: str) -> dict:
    if not rows:
        return _envelope(
            response_type = "cart_empty",
            message       = "Your cart is empty.",
            data          = [],
        )

    subtotal = sum(r.get("subtotal", 0) for r in rows)
    return _envelope(
        response_type = "cart_view",
        message       = f"You have {len(rows)} item(s) in your cart.",
        data          = rows,
        meta          = {"subtotal": subtotal},
    )


# ── Cart update (add / remove / qty change) ───────────────────────────────────

def fmt_cart_add(result: dict) -> dict:
    return _envelope(
        response_type = "cart_update",
        message       = (
            f"Added {result['qty_added']}× {result['product_name']} "
            f"(₹{result['unit_price']}) to your cart."
        ),
        data  = result,
        meta  = {"action": "add_to_cart"},
    )


def fmt_cart_remove(result: dict) -> dict:
    return _envelope(
        response_type = "cart_update",
        message       = f"Removed {result['product_name']} from your cart.",
        data  = result,
        meta  = {"action": "remove_from_cart"},
    )


def fmt_cart_qty_update(result: dict) -> dict:
    return _envelope(
        response_type = "cart_update",
        message       = (
            f"Updated {result['product_name']} quantity to {result['new_qty']}."
        ),
        data  = result,
        meta  = {"action": "update_cart_qty"},
    )


# ── Billing / order confirmation prompt ───────────────────────────────────────

def fmt_billing_summary(summary: dict) -> dict:
    return _envelope(
        response_type = "order_confirmation_prompt",
        message       = (
            f"Here is your order summary. Total: ₹{summary['total']} "
            f"(incl. {summary['gst_rate']} GST). Shall I place the order?"
        ),
        data  = summary,
        meta  = {"awaiting_confirmation": True},
    )


# ── Order success ─────────────────────────────────────────────────────────────

def fmt_order_success(order) -> dict:
    return _envelope(
        response_type = "order_success",
        message       = (
            f"Order #{order.id} placed successfully! "
            f"Total charged: ₹{order.total}. "
            "You will receive a confirmation shortly."
        ),
        data  = order.to_dict(),
        meta  = {"order_id": order.id},
    )


# ── Cancellation ──────────────────────────────────────────────────────────────

def fmt_cancelled() -> dict:
    return _envelope(
        response_type = "cancelled",
        message       = "Order cancelled. Your cart is still saved.",
        data          = {},
    )


def fmt_order_cancelled(order) -> dict:
    return _envelope(
        response_type = "order_cancelled",
        message       = f"Order #{order.id} has been cancelled. Total refund: ₹{order.total}.",
        data          = {"order_id": order.id, "total": order.total, "status": "cancelled"},
        meta          = {"order_id": order.id},
    )


# ── General / error ───────────────────────────────────────────────────────────

def fmt_general(message: str) -> dict:
    return _envelope(
        response_type = "general",
        message       = message,
        data          = {},
    )


def fmt_error(message: str) -> dict:
    return _envelope(
        response_type = "error",
        message       = message,
        data          = {},
    )
