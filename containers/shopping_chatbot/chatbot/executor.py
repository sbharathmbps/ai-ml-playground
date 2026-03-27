"""
Two responsibilities:
1. execute_select  — run LLM-generated SELECT queries safely
2. execute_write   — perform all cart/order writes via SQLAlchemy ORM
                     (no LLM-generated SQL ever touches writes)
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.models import Cart, CartItem, Order, OrderItem, Product, CartStatus, OrderStatus
from config import GST_RATE

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# READ — execute LLM-generated SELECT
# ══════════════════════════════════════════════════════════════════════════════

def execute_select(db: Session, sql: str) -> list[dict]:
    """
    Execute a SELECT statement and return rows as a list of dicts.
    Raises ValueError if the statement is not a SELECT.
    """
    clean = sql.strip()
    if not clean.upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed.")

    try:
        result = db.execute(text(clean))
        columns = list(result.keys())
        rows    = [dict(zip(columns, row)) for row in result.fetchall()]
        logger.info(f"SELECT returned {len(rows)} rows")
        return rows
    except Exception as e:
        logger.error(f"SQL execution error: {e}\nSQL: {clean}")
        raise


# ══════════════════════════════════════════════════════════════════════════════
# WRITE — cart operations
# ══════════════════════════════════════════════════════════════════════════════

def get_or_create_cart(db: Session, session_id: str) -> Cart:
    """Return the active cart for this session, creating one if needed."""
    cart = (
        db.query(Cart)
        .filter_by(session_id=session_id, status=CartStatus.active)
        .first()
    )
    if not cart:
        cart = Cart(session_id=session_id, status=CartStatus.active)
        db.add(cart)
        db.flush()   # get cart.id without full commit
        logger.info(f"Created new cart id={cart.id} for session={session_id}")
    return cart


def add_to_cart(db: Session, session_id: str, product_id: int, qty: int = 1) -> dict:
    """
    Add a product to the active cart.
    If the product is already in the cart, increment qty instead.
    Returns a summary dict.
    """
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        raise ValueError("Product not found.")
    if product.stock_qty < qty:
        raise ValueError(f"Only {product.stock_qty} units in stock for '{product.name}'")

    cart = get_or_create_cart(db, session_id)

    existing = (
        db.query(CartItem)
        .filter_by(cart_id=cart.id, product_id=product_id)
        .first()
    )
    if existing:
        existing.qty += qty
        logger.info(f"Updated cart item product={product_id} new qty={existing.qty}")
    else:
        item = CartItem(
            cart_id      = cart.id,
            product_id   = product_id,
            qty          = qty,
            price_at_add = product.price,
        )
        db.add(item)
        logger.info(f"Added product={product_id} to cart={cart.id}")

    db.commit()

    # Return updated cart item count
    total_items = db.query(CartItem).filter_by(cart_id=cart.id).count()
    return {
        "cart_id":           cart.id,
        "product_id":        product_id,
        "product_name":      product.name,
        "unit_price":        product.price,
        "qty_added":         qty,
        "cart_total_items":  total_items,
    }


def remove_from_cart(db: Session, session_id: str, product_id: int) -> dict:
    """Remove a product entirely from the active cart."""
    cart = (
        db.query(Cart)
        .filter_by(session_id=session_id, status=CartStatus.active)
        .first()
    )
    if not cart:
        raise ValueError("No active cart found")

    item = db.query(CartItem).filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        raise ValueError("That product is not in your cart.")

    product_name = item.product.name if item.product else "Unknown product"
    db.delete(item)
    db.commit()
    logger.info(f"Removed product={product_id} from cart={cart.id}")
    return {"removed_product_id": product_id, "product_name": product_name}


def update_cart_qty(db: Session, session_id: str, product_id: int, new_qty: int) -> dict:
    """Update the quantity of an item in the active cart."""
    if new_qty <= 0:
        return remove_from_cart(db, session_id, product_id)

    cart = (
        db.query(Cart)
        .filter_by(session_id=session_id, status=CartStatus.active)
        .first()
    )
    if not cart:
        raise ValueError("No active cart found")

    item = db.query(CartItem).filter_by(cart_id=cart.id, product_id=product_id).first()
    if not item:
        raise ValueError("That product is not in your cart.")

    item.qty = new_qty
    db.commit()
    logger.info(f"Updated product={product_id} qty to {new_qty} in cart={cart.id}")
    return {
        "product_id":   product_id,
        "product_name": item.product.name if item.product else str(product_id),
        "new_qty":      new_qty,
        "new_subtotal": new_qty * item.price_at_add,
    }


# ══════════════════════════════════════════════════════════════════════════════
# WRITE — billing preview (no DB write)
# ══════════════════════════════════════════════════════════════════════════════

def build_billing_summary(db: Session, session_id: str) -> dict:
    """
    Build a billing summary from the active cart WITHOUT writing to DB.
    Used to show user the order total before confirmation.
    """
    cart = (
        db.query(Cart)
        .filter_by(session_id=session_id, status=CartStatus.active)
        .first()
    )
    if not cart or not cart.items:
        raise ValueError("Cart is empty — nothing to order")

    items = []
    subtotal = 0
    for ci in cart.items:
        line = ci.to_dict()
        items.append(line)
        subtotal += line["subtotal"]

    tax   = int(subtotal * GST_RATE)
    total = subtotal + tax

    return {
        "cart_id":  cart.id,
        "items":    items,
        "subtotal": subtotal,
        "tax":      tax,
        "total":    total,
        "gst_rate": f"{int(GST_RATE * 100)}%",
    }


# ══════════════════════════════════════════════════════════════════════════════
# WRITE — place order
# ══════════════════════════════════════════════════════════════════════════════

def place_order(db: Session, session_id: str, cart_id: int) -> Order:
    """
    Convert active cart into a confirmed order.
    Writes to orders + order_items, marks cart as 'ordered'.
    """
    cart = db.query(Cart).filter_by(id=cart_id, session_id=session_id).first()
    if not cart:
        raise ValueError("Could not find your cart.")
    if cart.status != CartStatus.active:
        raise ValueError("Your cart is no longer active.")
    if not cart.items:
        raise ValueError("Cart is empty — cannot place order")

    subtotal = sum(ci.qty * ci.price_at_add for ci in cart.items)
    tax      = int(subtotal * GST_RATE)
    total    = subtotal + tax

    order = Order(
        session_id = session_id,
        cart_id    = cart_id,
        subtotal   = subtotal,
        tax        = tax,
        total      = total,
        status     = OrderStatus.confirmed,
    )
    db.add(order)
    db.flush()   # get order.id

    for ci in cart.items:
        db.add(OrderItem(
            order_id   = order.id,
            product_id = ci.product_id,
            qty        = ci.qty,
            unit_price = ci.price_at_add,
        ))

    cart.status = CartStatus.ordered
    db.commit()

    logger.info(f"Order placed: id={order.id} total={order.total} session={session_id}")
    return order


def cancel_last_order(db: Session, session_id: str) -> Order:
    """Cancel the most recent confirmed order for this session."""
    order = (
        db.query(Order)
        .filter_by(session_id=session_id, status=OrderStatus.confirmed)
        .order_by(Order.created_at.desc())
        .first()
    )
    if not order:
        raise ValueError("No confirmed order found to cancel.")

    order.status = OrderStatus.cancelled
    db.commit()
    logger.info(f"Order cancelled: id={order.id} session={session_id}")
    return order
