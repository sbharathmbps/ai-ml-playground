"""
Shopping Chatbot — FastAPI entry point.

Routes:
  POST /chat                → main chatbot endpoint
  GET  /session/{id}        → inspect session state
  DELETE /session/{id}      → clear session
  GET  /products            → browse products (REST fallback)
  GET  /products/{id}       → product detail
  GET  /cart/{session_id}   → view cart
  GET  /orders/{session_id} → order history
  GET  /health              → health check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import APP_TITLE, APP_VERSION, DEBUG
from database.connection import engine, get_db
from database.models import Base, Product, Category, Cart, CartItem, Order
from database.seed import create_tables, seed
from chatbot.handler import handle_turn
from chatbot import session as session_store
from chatbot.executor import execute_select
from schemas.responses import ChatRequest, ChatResponse, HealthResponse
from llm.client import llm_client

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables and seeding data …")
    create_tables()
    seed()
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title    = APP_TITLE,
    version  = APP_VERSION,
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # tighten in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check(db: Session = Depends(get_db)):
    # DB check
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    # LLM check
    llm_ok = llm_client.health_check()

    return HealthResponse(
        status    = "ok" if db_status == "ok" and llm_ok else "degraded",
        db        = db_status,
        llm       = "ok" if llm_ok else "unreachable",
        llm_model = llm_client.model,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CHAT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chatbot endpoint.
    Send a message and receive a structured JSON response.
    Pass `session_id` from a previous response to continue the conversation.
    """
    response = handle_turn(
        user_message = req.message,
        session_id   = req.session_id,
        db           = db,
    )
    return response


# ══════════════════════════════════════════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/session/{session_id}", tags=["Session"])
def get_session(session_id: str):
    """Inspect current session state (for debugging)."""
    sess = session_store.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    # Don't expose full last_results — just count
    return {
        "session_id":            sess["session_id"],
        "history_turns":         len(sess["history"]) // 2,
        "cart_id":               sess["cart_id"],
        "awaiting_confirmation": sess["awaiting_confirmation"],
        "last_results_count":    len(sess.get("last_results", [])),
    }


@app.delete("/session/{session_id}", tags=["Session"])
def delete_session(session_id: str):
    """Clear a session (start fresh)."""
    session_store.clear_session(session_id)
    return {"detail": f"Session {session_id} cleared."}


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS (REST fallback — useful for frontend browsing without chatbot)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/products", tags=["Products"])
def list_products(
    category: str | None = Query(None, description="Filter by category name"),
    brand:    str | None = Query(None, description="Filter by brand name"),
    min_price: int | None = Query(None),
    max_price: int | None = Query(None),
    in_stock:  bool       = Query(True, description="Only show in-stock items"),
    sort_by:   str        = Query("rating", description="rating | price_asc | price_desc"),
    db: Session = Depends(get_db),
):
    q = db.query(Product)

    if in_stock:
        q = q.filter(Product.stock_qty > 0)
    if brand:
        q = q.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        q = q.filter(Product.price >= min_price)
    if max_price is not None:
        q = q.filter(Product.price <= max_price)
    if category:
        q = q.join(Category).filter(Category.name.ilike(f"%{category}%"))

    if sort_by == "price_asc":
        q = q.order_by(Product.price.asc())
    elif sort_by == "price_desc":
        q = q.order_by(Product.price.desc())
    else:
        q = q.order_by(Product.rating.desc())

    products = q.all()
    return {
        "response_type": "product_list",
        "total":         len(products),
        "data":          [p.to_dict() for p in products],
    }


@app.get("/products/{product_id}", tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter_by(id=product_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"response_type": "product_detail", "data": p.to_dict()}


@app.get("/categories", tags=["Products"])
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return {
        "data": [
            {"id": c.id, "name": c.name, "parent_id": c.parent_id}
            for c in cats
        ]
    }


# ══════════════════════════════════════════════════════════════════════════════
# CART (REST read — writes happen through /chat)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/cart/{session_id}", tags=["Cart"])
def get_cart(session_id: str, db: Session = Depends(get_db)):
    cart = (
        db.query(Cart)
        .filter_by(session_id=session_id, status="active")
        .first()
    )
    if not cart or not cart.items:
        return {"response_type": "cart_empty", "data": [], "subtotal": 0}

    items    = [ci.to_dict() for ci in cart.items]
    subtotal = sum(i["subtotal"] for i in items)
    return {
        "response_type": "cart_view",
        "cart_id":       cart.id,
        "data":          items,
        "subtotal":      subtotal,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/orders/{session_id}", tags=["Orders"])
def get_orders(session_id: str, db: Session = Depends(get_db)):
    orders = (
        db.query(Order)
        .filter_by(session_id=session_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return {
        "response_type": "order_history",
        "total":         len(orders),
        "data":          [o.to_dict() for o in orders],
    }


@app.get("/orders/{session_id}/{order_id}", tags=["Orders"])
def get_order_detail(session_id: str, order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter_by(id=order_id, session_id=session_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"response_type": "order_detail", "data": order.to_dict()}
