"""
Seed the database with categories and sample sports products.
Run once:  python -m database.seed
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.connection import engine, SessionLocal
from database.models import Base, Category, Product


# ── Schema creation ───────────────────────────────────────────────────────────

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅  Tables created.")


# ── Seed data ─────────────────────────────────────────────────────────────────

CATEGORIES = [
    # top level
    {"id": 1,  "name": "Sports",         "parent_id": None},
    # level 2
    {"id": 2,  "name": "Cricket",        "parent_id": 1},
    {"id": 3,  "name": "Football",       "parent_id": 1},
    {"id": 4,  "name": "Badminton",      "parent_id": 1},
    {"id": 5,  "name": "Tennis",         "parent_id": 1},
    {"id": 6,  "name": "Table Tennis",   "parent_id": 1},
    # level 3
    {"id": 7,  "name": "Cricket Bats",   "parent_id": 2},
    {"id": 8,  "name": "Cricket Balls",  "parent_id": 2},
    {"id": 9,  "name": "Cricket Pads",   "parent_id": 2},
    {"id": 10, "name": "Cricket Gloves", "parent_id": 2},
    {"id": 11, "name": "Footballs",      "parent_id": 3},
    {"id": 12, "name": "Football Boots", "parent_id": 3},
    {"id": 13, "name": "Rackets",        "parent_id": 4},
    {"id": 14, "name": "Shuttlecocks",   "parent_id": 4},
    {"id": 15, "name": "Tennis Rackets", "parent_id": 5},
    {"id": 16, "name": "Tennis Balls",   "parent_id": 5},
]

PRODUCTS = [
    # ── Cricket Bats ──────────────────────────────────────────────────────────
    {
        "name": "SG Campus Cricket Bat",
        "category_id": 7, "brand": "SG",
        "price": 850,  "stock_qty": 45,
        "rating": 4.2,
        "description": "English willow bat ideal for beginners and campus level players. Light pickup with a mid-sweet spot.",
        "image_url": "https://example.com/images/sg-campus-bat.jpg",
    },
    {
        "name": "SS Ton Player Edition Bat",
        "category_id": 7, "brand": "SS",
        "price": 1950, "stock_qty": 20,
        "rating": 4.6,
        "description": "Grade 1 English willow, full profile with thick edges and a high sweet spot. Professional grade.",
        "image_url": "https://example.com/images/ss-ton-player-bat.jpg",
    },
    {
        "name": "Kookaburra Kahuna Pro Bat",
        "category_id": 7, "brand": "Kookaburra",
        "price": 3200, "stock_qty": 10,
        "rating": 4.8,
        "description": "Premium Grade 1 English willow, used by international players. Exceptional power and balance.",
        "image_url": "https://example.com/images/kookaburra-kahuna-bat.jpg",
    },
    {
        "name": "GM Sparq 303 Cricket Bat",
        "category_id": 7, "brand": "GM",
        "price": 2400, "stock_qty": 15,
        "rating": 4.5,
        "description": "Handled for power hitting. Large sweet spot ideal for T20 style play.",
        "image_url": "https://example.com/images/gm-sparq-bat.jpg",
    },
    {
        "name": "MRF Genius Grand Edition Bat",
        "category_id": 7, "brand": "MRF",
        "price": 4500, "stock_qty": 8,
        "rating": 4.9,
        "description": "Used by Virat Kohli. Top grade English willow with oval handle for maximum control.",
        "image_url": "https://example.com/images/mrf-genius-bat.jpg",
    },
    {
        "name": "DSC Intense Speed Bat",
        "category_id": 7, "brand": "DSC",
        "price": 699,  "stock_qty": 60,
        "rating": 3.9,
        "description": "Kashmir willow bat for net practice and tape ball cricket. Affordable and durable.",
        "image_url": "https://example.com/images/dsc-intense-bat.jpg",
    },
    {
        "name": "Puma evoSpeed Cricket Bat",
        "category_id": 7, "brand": "Puma",
        "price": 1400, "stock_qty": 25,
        "rating": 4.3,
        "description": "Grade 2 English willow. Balanced pickup with concave back profile for club cricket.",
        "image_url": "https://example.com/images/puma-evospeed-bat.jpg",
    },
    # ── Cricket Balls ─────────────────────────────────────────────────────────
    {
        "name": "SG Club Cricket Ball (Red)",
        "category_id": 8, "brand": "SG",
        "price": 250,  "stock_qty": 200,
        "rating": 4.1,
        "description": "4-piece construction, alum tanned leather. Ideal for club matches.",
        "image_url": "https://example.com/images/sg-club-ball.jpg",
    },
    {
        "name": "Kookaburra Turf Cricket Ball",
        "category_id": 8, "brand": "Kookaburra",
        "price": 850,  "stock_qty": 80,
        "rating": 4.7,
        "description": "Official match ball used in international ODI and Test matches.",
        "image_url": "https://example.com/images/kookaburra-turfball.jpg",
    },
    {
        "name": "Cosco Rubber Cricket Ball",
        "category_id": 8, "brand": "Cosco",
        "price": 120,  "stock_qty": 500,
        "rating": 3.8,
        "description": "Tennis ball style rubber cricket ball for tape ball and gully cricket.",
        "image_url": "https://example.com/images/cosco-rubber-ball.jpg",
    },
    # ── Cricket Pads ─────────────────────────────────────────────────────────
    {
        "name": "SG Ecolite Batting Pads",
        "category_id": 9, "brand": "SG",
        "price": 750,  "stock_qty": 30,
        "rating": 4.0,
        "description": "Lightweight PVC pads with high-density foam. Suitable for club-level batsmen.",
        "image_url": "https://example.com/images/sg-ecolite-pads.jpg",
    },
    {
        "name": "GM Original LE Batting Pads",
        "category_id": 9, "brand": "GM",
        "price": 2200, "stock_qty": 12,
        "rating": 4.6,
        "description": "Premium leather outer with multi-layer foam protection. Professional grade.",
        "image_url": "https://example.com/images/gm-original-pads.jpg",
    },
    # ── Cricket Gloves ────────────────────────────────────────────────────────
    {
        "name": "SS Matrix Batting Gloves",
        "category_id": 10, "brand": "SS",
        "price": 550,  "stock_qty": 40,
        "rating": 4.2,
        "description": "Genuine leather palm with padded finger protection. Right hand only.",
        "image_url": "https://example.com/images/ss-matrix-gloves.jpg",
    },
    {
        "name": "Kookaburra Pro 1000 Batting Gloves",
        "category_id": 10, "brand": "Kookaburra",
        "price": 1800, "stock_qty": 18,
        "rating": 4.7,
        "description": "International grade gloves with cane and foam protection on each finger.",
        "image_url": "https://example.com/images/kookaburra-pro-gloves.jpg",
    },
    # ── Footballs ─────────────────────────────────────────────────────────────
    {
        "name": "Nivia Storm Football Size 5",
        "category_id": 11, "brand": "Nivia",
        "price": 450,  "stock_qty": 75,
        "rating": 4.0,
        "description": "Machine-stitched PVC football. Suitable for training and casual matches.",
        "image_url": "https://example.com/images/nivia-storm-football.jpg",
    },
    {
        "name": "Adidas Tiro League Football",
        "category_id": 11, "brand": "Adidas",
        "price": 1200, "stock_qty": 40,
        "rating": 4.5,
        "description": "Thermally bonded match ball with FIFA Basic quality approval.",
        "image_url": "https://example.com/images/adidas-tiro-football.jpg",
    },
    {
        "name": "Nike Strike Football Size 5",
        "category_id": 11, "brand": "Nike",
        "price": 1500, "stock_qty": 35,
        "rating": 4.6,
        "description": "High visibility graphic design for play in low light. Machine stitched for durability.",
        "image_url": "https://example.com/images/nike-strike-football.jpg",
    },
    # ── Football Boots ────────────────────────────────────────────────────────
    {
        "name": "Nivia Carbonite Football Boots",
        "category_id": 12, "brand": "Nivia",
        "price": 899,  "stock_qty": 55,
        "rating": 3.9,
        "description": "PVC upper with molded studs. Suitable for hard ground and turf.",
        "image_url": "https://example.com/images/nivia-carbonite-boots.jpg",
    },
    {
        "name": "Adidas Copa Pure.3 FG Boots",
        "category_id": 12, "brand": "Adidas",
        "price": 4500, "stock_qty": 20,
        "rating": 4.8,
        "description": "Genuine leather upper for touch and feel. FG studs for natural grass.",
        "image_url": "https://example.com/images/adidas-copa-pure-boots.jpg",
    },
    # ── Badminton Rackets ─────────────────────────────────────────────────────
    {
        "name": "Yonex Astrox 2 Badminton Racket",
        "category_id": 13, "brand": "Yonex",
        "price": 1100, "stock_qty": 30,
        "rating": 4.4,
        "description": "Head-heavy balance for powerful smashes. Graphite frame, 4U weight.",
        "image_url": "https://example.com/images/yonex-astrox2.jpg",
    },
    {
        "name": "Li-Ning G-Force 3900 Racket",
        "category_id": 13, "brand": "Li-Ning",
        "price": 2800, "stock_qty": 15,
        "rating": 4.6,
        "description": "High modulus graphite with aerodynamic frame. Used in national level tournaments.",
        "image_url": "https://example.com/images/lining-gforce3900.jpg",
    },
    {
        "name": "Victor Thruster K Badminton Racket",
        "category_id": 13, "brand": "Victor",
        "price": 3500, "stock_qty": 10,
        "rating": 4.7,
        "description": "Carbon nano tube construction. Extra stiff shaft for pro smash players.",
        "image_url": "https://example.com/images/victor-thrusterk.jpg",
    },
    {
        "name": "Cosco CBX 450 Badminton Racket",
        "category_id": 13, "brand": "Cosco",
        "price": 350,  "stock_qty": 100,
        "rating": 3.7,
        "description": "Aluminium frame, beginner-friendly. Good for park and casual play.",
        "image_url": "https://example.com/images/cosco-cbx450.jpg",
    },
    # ── Shuttlecocks ──────────────────────────────────────────────────────────
    {
        "name": "Yonex Mavis 350 Shuttlecock (Pack of 6)",
        "category_id": 14, "brand": "Yonex",
        "price": 480,  "stock_qty": 120,
        "rating": 4.5,
        "description": "Nylon shuttlecock for medium speed play. Durable for outdoor conditions.",
        "image_url": "https://example.com/images/yonex-mavis350.jpg",
    },
    {
        "name": "Victor NS 3000 Feather Shuttlecock (Pack of 12)",
        "category_id": 14, "brand": "Victor",
        "price": 950,  "stock_qty": 60,
        "rating": 4.3,
        "description": "Natural goose feather shuttlecock for tournament play. 77 speed.",
        "image_url": "https://example.com/images/victor-ns3000.jpg",
    },
    # ── Tennis Rackets ────────────────────────────────────────────────────────
    {
        "name": "Wilson Clash 100 Tennis Racket",
        "category_id": 15, "brand": "Wilson",
        "price": 8500, "stock_qty": 8,
        "rating": 4.9,
        "description": "Carbon mapping technology for flexible power. Used by top ATP players.",
        "image_url": "https://example.com/images/wilson-clash100.jpg",
    },
    {
        "name": "Head Ti S6 Tennis Racket",
        "category_id": 15, "brand": "Head",
        "price": 2200, "stock_qty": 20,
        "rating": 4.4,
        "description": "Titanium composite frame. Oversized head for larger sweet spot. Beginner-friendly.",
        "image_url": "https://example.com/images/head-tis6.jpg",
    },
    # ── Tennis Balls ──────────────────────────────────────────────────────────
    {
        "name": "Wilson Championship Tennis Balls (Pack of 3)",
        "category_id": 16, "brand": "Wilson",
        "price": 380,  "stock_qty": 150,
        "rating": 4.3,
        "description": "Extra duty felt for hard court. Consistent bounce and feel.",
        "image_url": "https://example.com/images/wilson-championship-balls.jpg",
    },
    {
        "name": "Penn Championship Tennis Balls (Pack of 4)",
        "category_id": 16, "brand": "Penn",
        "price": 420,  "stock_qty": 130,
        "rating": 4.2,
        "description": "Official ball of USTA. Natural rubber core with Intensa felt.",
        "image_url": "https://example.com/images/penn-championship-balls.jpg",
    },
]


# ── Seed function ─────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        # Skip if already seeded
        if db.query(Category).count() > 0:
            print("ℹ️   Database already seeded. Skipping.")
            return

        # Insert categories
        for cat in CATEGORIES:
            db.add(Category(**cat))
        db.commit()
        print(f"✅  Inserted {len(CATEGORIES)} categories.")

        # Insert products
        for prod in PRODUCTS:
            db.add(Product(**prod))
        db.commit()
        print(f"✅  Inserted {len(PRODUCTS)} products.")

    except Exception as e:
        db.rollback()
        print(f"❌  Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_tables()
    seed()
    print("🎉  Seed complete.")
