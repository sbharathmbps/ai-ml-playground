"""
ORM models.
Every column carries an `info` dict with a human-readable description.
These descriptions are harvested by prompt_builder.py to build the
LLM schema context — so the model knows exactly what each field means.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, ForeignKey, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.connection import Base
import enum


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class CartStatus(str, enum.Enum):
    active    = "active"
    ordered   = "ordered"
    abandoned = "abandoned"


class OrderStatus(str, enum.Enum):
    pending   = "pending"
    confirmed = "confirmed"
    shipped   = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY
# ══════════════════════════════════════════════════════════════════════════════

class Category(Base):
    __tablename__ = "categories"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique category ID (int, PK)"}
    )
    name = Column(
        String(100), nullable=False, unique=True,
        info={"desc": "Category display name shown to user e.g. Cricket, Football, Badminton (varchar)"}
    )
    parent_id = Column(
        Integer, ForeignKey("categories.id"), nullable=True,
        info={"desc": "FK → categories.id; NULL if this is a top-level category; used for nested categories e.g. Sports > Cricket > Bats (int, nullable)"}
    )

    parent   = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT
# ══════════════════════════════════════════════════════════════════════════════

class Product(Base):
    __tablename__ = "products"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique product ID (int, PK)"}
    )
    name = Column(
        String(255), nullable=False, index=True,
        info={"desc": "Full product display name shown to customer e.g. 'SG Campus Cricket Bat' (varchar)"}
    )
    category_id = Column(
        Integer, ForeignKey("categories.id"), nullable=False,
        info={"desc": "FK → categories.id; the category this product belongs to (int)"}
    )
    brand = Column(
        String(100), nullable=True,
        info={"desc": "Manufacturer or brand name e.g. SG, SS, Nike, Adidas, Yonex (varchar)"}
    )
    price = Column(
        Integer, nullable=False,
        info={"desc": "Selling price in Indian Rupees (INR), whole numbers only, no decimals (int)"}
    )
    stock_qty = Column(
        Integer, nullable=False, default=0,
        info={"desc": "Number of units currently available in inventory; 0 means out of stock (int)"}
    )
    description = Column(
        Text, nullable=True,
        info={"desc": "Long-form product description for detail view (text)"}
    )
    image_url = Column(
        String(500), nullable=True,
        info={"desc": "Publicly accessible URL to product image (varchar)"}
    )
    rating = Column(
        Float, nullable=True, default=0.0,
        info={"desc": "Average customer rating from 1.0 to 5.0 (float)"}
    )
    created_at = Column(
        DateTime, default=datetime.utcnow,
        info={"desc": "Timestamp when product was added to catalogue (datetime)"}
    )

    category    = relationship("Category", back_populates="products")
    cart_items  = relationship("CartItem",  back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

    def to_dict(self):
        return {
            "id":          self.id,
            "name":        self.name,
            "brand":       self.brand,
            "price":       self.price,
            "stock_qty":   self.stock_qty,
            "description": self.description,
            "image_url":   self.image_url,
            "rating":      self.rating,
            "category":    self.category.name if self.category else None,
        }

    def __repr__(self):
        return f"<Product id={self.id} name={self.name} price={self.price}>"


# ══════════════════════════════════════════════════════════════════════════════
# CART
# ══════════════════════════════════════════════════════════════════════════════

class Cart(Base):
    __tablename__ = "carts"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique cart ID (int, PK)"}
    )
    session_id = Column(
        String(100), nullable=False, index=True,
        info={"desc": "Links to the active user/browser session; one active cart per session (varchar)"}
    )
    status = Column(
        SAEnum(CartStatus), nullable=False, default=CartStatus.active,
        info={"desc": "Current cart state — 'active' (user shopping), 'ordered' (purchase done), 'abandoned' (session expired) (enum)"}
    )
    created_at = Column(
        DateTime, default=datetime.utcnow,
        info={"desc": "Timestamp when cart was first created (datetime)"}
    )

    items  = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    orders = relationship("Order",    back_populates="cart")

    def __repr__(self):
        return f"<Cart id={self.id} session={self.session_id} status={self.status}>"


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique cart item row ID (int, PK)"}
    )
    cart_id = Column(
        Integer, ForeignKey("carts.id"), nullable=False,
        info={"desc": "FK → carts.id; which cart this item belongs to (int)"}
    )
    product_id = Column(
        Integer, ForeignKey("products.id"), nullable=False,
        info={"desc": "FK → products.id; which product was added (int)"}
    )
    qty = Column(
        Integer, nullable=False, default=1,
        info={"desc": "Number of units the user added for this product (int)"}
    )
    price_at_add = Column(
        Integer, nullable=False,
        info={"desc": "Product price in INR at the exact time user added it to cart; stored so price changes after adding don't affect the cart total (int)"}
    )

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )

    cart    = relationship("Cart",    back_populates="items")
    product = relationship("Product", back_populates="cart_items")

    def to_dict(self):
        return {
            "cart_item_id": self.id,
            "product_id":   self.product_id,
            "name":         self.product.name if self.product else None,
            "brand":        self.product.brand if self.product else None,
            "qty":          self.qty,
            "unit_price":   self.price_at_add,
            "subtotal":     self.qty * self.price_at_add,
        }

    def __repr__(self):
        return f"<CartItem cart={self.cart_id} product={self.product_id} qty={self.qty}>"


# ══════════════════════════════════════════════════════════════════════════════
# ORDER
# ══════════════════════════════════════════════════════════════════════════════

class Order(Base):
    __tablename__ = "orders"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique order ID (int, PK)"}
    )
    session_id = Column(
        String(100), nullable=False, index=True,
        info={"desc": "User session that placed this order (varchar)"}
    )
    cart_id = Column(
        Integer, ForeignKey("carts.id"), nullable=False,
        info={"desc": "FK → carts.id; the cart this order was created from (int)"}
    )
    subtotal = Column(
        Integer, nullable=False,
        info={"desc": "Sum of all item prices before tax in INR (int)"}
    )
    tax = Column(
        Integer, nullable=False,
        info={"desc": "Tax amount in INR calculated at 18% GST on subtotal (int)"}
    )
    total = Column(
        Integer, nullable=False,
        info={"desc": "Final amount charged to customer = subtotal + tax in INR (int)"}
    )
    status = Column(
        SAEnum(OrderStatus), nullable=False, default=OrderStatus.confirmed,
        info={"desc": "Order lifecycle state — 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled' (enum)"}
    )
    created_at = Column(
        DateTime, default=datetime.utcnow,
        info={"desc": "Timestamp when order was placed (datetime)"}
    )

    cart        = relationship("Cart",      back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "order_id":   self.id,
            "subtotal":   self.subtotal,
            "tax":        self.tax,
            "total":      self.total,
            "status":     self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [i.to_dict() for i in self.order_items],
        }

    def __repr__(self):
        return f"<Order id={self.id} total={self.total} status={self.status}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(
        Integer, primary_key=True, index=True,
        info={"desc": "Unique order item row ID (int, PK)"}
    )
    order_id = Column(
        Integer, ForeignKey("orders.id"), nullable=False,
        info={"desc": "FK → orders.id; which order this item belongs to (int)"}
    )
    product_id = Column(
        Integer, ForeignKey("products.id"), nullable=False,
        info={"desc": "FK → products.id; which product was ordered (int)"}
    )
    qty = Column(
        Integer, nullable=False,
        info={"desc": "Number of units ordered for this product (int)"}
    )
    unit_price = Column(
        Integer, nullable=False,
        info={"desc": "Price per unit in INR at the time of order placement (int)"}
    )

    order   = relationship("Order",   back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "name":       self.product.name if self.product else None,
            "qty":        self.qty,
            "unit_price": self.unit_price,
            "subtotal":   self.qty * self.unit_price,
        }

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.qty}>"


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATION LOG
# ══════════════════════════════════════════════════════════════════════════════

class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id    = Column(String(100), nullable=False, index=True)
    turn          = Column(Integer, nullable=False)
    user_message  = Column(Text, nullable=False)
    intent        = Column(String(50), nullable=True)
    generated_sql = Column(Text, nullable=True)
    response_type = Column(String(50), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ConversationLog session={self.session_id} turn={self.turn}>"
