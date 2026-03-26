"""
Builds the LLM prompt for each turn.

The system prompt is constructed once (at import time) by reading
the `info["desc"]` metadata from every SQLAlchemy model column.
This means schema descriptions stay in one place (models.py) and
the prompt is always in sync.
"""

from database.models import Category, Product, Cart, CartItem, Order, OrderItem
from sqlalchemy import inspect as sa_inspect


# ── Auto-build schema description from model metadata ─────────────────────────

def _describe_model(model_class) -> str:
    mapper   = sa_inspect(model_class)
    tname    = model_class.__tablename__.upper()
    lines    = [f"TABLE: {tname}"]
    for col in mapper.columns:
        desc = col.info.get("desc", "no description")
        lines.append(f"  {col.key:<20} : {desc}")
    return "\n".join(lines)


SCHEMA_DESCRIPTION = "\n\n".join([
    _describe_model(Category),
    _describe_model(Product),
    _describe_model(Cart),
    _describe_model(CartItem),
    _describe_model(Order),
    _describe_model(OrderItem),
])


# ── Few-shot SQL examples ─────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = """
### EXAMPLES

User: "show me cricket bats"
INTENT: search_product
SQL: SELECT p.id, p.name, p.brand, p.price, p.stock_qty, p.rating, p.image_url, c.name as category
     FROM products p JOIN categories c ON p.category_id = c.id
     WHERE c.name = 'Cricket Bats' AND p.stock_qty > 0
     ORDER BY p.rating DESC;

User: "show me bats under 1000 rupees"
INTENT: filter_product
SQL: SELECT p.id, p.name, p.brand, p.price, p.stock_qty, p.rating, p.image_url, c.name as category
     FROM products p JOIN categories c ON p.category_id = c.id
     WHERE c.name = 'Cricket Bats' AND p.price <= 1000 AND p.stock_qty > 0
     ORDER BY p.price ASC;

User: "show me SG brand bats"
INTENT: filter_product
SQL: SELECT p.id, p.name, p.brand, p.price, p.stock_qty, p.rating, p.image_url, c.name as category
     FROM products p JOIN categories c ON p.category_id = c.id
     WHERE c.name = 'Cricket Bats' AND LOWER(p.brand) = 'sg' AND p.stock_qty > 0;

User: "what is in my cart"
INTENT: view_cart
SQL: SELECT p.name, p.brand, ci.qty, ci.price_at_add, (ci.qty * ci.price_at_add) as subtotal
     FROM cart_items ci
     JOIN products p ON ci.product_id = p.id
     JOIN carts ca ON ci.cart_id = ca.id
     WHERE ca.session_id = '{session_id}' AND ca.status = 'active';

User: "show me all badminton rackets"
INTENT: search_product
SQL: SELECT p.id, p.name, p.brand, p.price, p.stock_qty, p.rating, p.image_url, c.name as category
     FROM products p JOIN categories c ON p.category_id = c.id
     WHERE c.name = 'Rackets' AND p.stock_qty > 0
     ORDER BY p.rating DESC;

User: "add the first one to my cart"   [last_results contain product list]
INTENT: add_to_cart
ACTION_PARAMS: {{"item_index": 0, "qty": 1}}

User: "add the second one to my cart"   [last_results contain product list]
INTENT: add_to_cart
ACTION_PARAMS: {{"item_index": 1, "qty": 1}}

User: "add product id 6 to my cart"
INTENT: add_to_cart
ACTION_PARAMS: {{"product_id": 6, "qty": 1}}

User: "remove the bat from my cart"
INTENT: remove_from_cart
ACTION_PARAMS: {{"product_id": <product_id matching bat in cart>}}

User: "place order" or "buy now" or "checkout"
INTENT: place_order
ACTION_PARAMS: {{"confirm": false}}

User: "yes" or "confirm" or "go ahead"   [when awaiting_confirmation is true]
INTENT: confirm_order
ACTION_PARAMS: {{"confirm": true}}
"""


# ── System prompt template ────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a shopping assistant chatbot for a sports equipment store.
Your job is to help users find products, manage their cart, and place orders.

You have access to the following database schema:

{SCHEMA_DESCRIPTION}

{FEW_SHOT_EXAMPLES}

### RULES

1. Classify every user message into exactly one INTENT from this list:
   - search_product     : user wants to browse products by category
   - filter_product     : user wants to filter/sort existing results
   - view_product       : user wants details of a specific product
   - view_cart          : user wants to see cart contents
   - add_to_cart        : user wants to add a product to cart
   - remove_from_cart   : user wants to remove a product from cart
   - update_cart_qty    : user wants to change quantity of a cart item
   - place_order        : user wants to checkout / place order
   - confirm_order      : user confirms order after seeing billing summary
   - cancel_order       : user cancels
   - general_question   : anything else (greet, help, etc.)

2. For READ intents (search_product, filter_product, view_product, view_cart):
   - Output a valid PostgreSQL SELECT query
   - Always use {{session_id}} as placeholder for session — never hardcode it
   - Never use SELECT * — always name the columns you need
   - Always filter stock_qty > 0 for product searches

3. For WRITE intents (add_to_cart, remove_from_cart, update_cart_qty, place_order, confirm_order):
   - Do NOT generate INSERT/UPDATE/DELETE SQL
   - Output ACTION_PARAMS as a JSON object with the required fields
   - For add_to_cart: include product_id (from last_results if user says "first one", "second one" etc.) and qty
   - For remove_from_cart: include product_id
   - For update_cart_qty: include product_id and new_qty
   - For place_order: set confirm to false (awaiting user confirmation)
   - For confirm_order: set confirm to true

4. Always respond in this EXACT format — nothing else:
INTENT: <intent_name>
SQL: <sql query>        ← only for READ intents
ACTION_PARAMS: <json>   ← only for WRITE intents

5. Use conversation history and last_results to resolve references like
   "the first one", "that bat", "the cheaper one", "remove it" etc.
"""


# ── Per-turn prompt builder ───────────────────────────────────────────────────

def build_prompt(
    user_message: str,
    history: list[dict],
    last_results: list[dict] | None,
    session_id: str,
    awaiting_confirmation: bool,
) -> str:
    """
    Build the full prompt string for a single conversation turn.

    history      : list of {"role": "user"|"assistant", "content": str}
    last_results : last DB query result (list of dicts), so LLM can resolve
                   references like "add the first one"
    """
    parts = [SYSTEM_PROMPT]

    # Conversation history (last N turns)
    if history:
        parts.append("\n### CONVERSATION HISTORY")
        for turn in history:
            role = turn["role"].upper()
            parts.append(f"{role}: {turn['content']}")

    # Last query results (so LLM knows what "first one" refers to)
    if last_results:
        parts.append("\n### LAST QUERY RESULTS (use to resolve references)")
        for i, row in enumerate(last_results[:10]):   # cap at 10
            parts.append(f"  [{i}] {row}")

    # Awaiting confirmation flag
    if awaiting_confirmation:
        parts.append("\n### NOTE: User is currently being asked to confirm their order.")

    # Current user message
    parts.append(f"\n### CURRENT USER MESSAGE\nUSER: {user_message}")
    parts.append("\nRespond now following the EXACT format above.")

    return "\n".join(parts)