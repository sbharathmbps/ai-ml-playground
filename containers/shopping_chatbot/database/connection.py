from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# ── Engine ────────────────────────────────────────────────────────────────────
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,          # set True to log all SQL
    pool_pre_ping=True,  # verify connection health before use
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base for all ORM models ───────────────────────────────────────────────────
Base = declarative_base()


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """Yield a DB session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
