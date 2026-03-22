import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
# DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = "postgresql+psycopg2://ml_playground:ml_playground%40123@localhost:5432/ml_platform"
# For PostgreSQL:
# DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/shopping_db"

# ── Ollama / LLM ──────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "mistral")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_CTX_WINDOW  = int(os.getenv("LLM_CTX_WINDOW", "4096"))
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "300"))

# ── App ───────────────────────────────────────────────────────────────────────
APP_TITLE   = "Shopping Chatbot API"
APP_VERSION = "1.0.0"
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"

# ── Tax ───────────────────────────────────────────────────────────────────────
GST_RATE = 0.18   # 18%

# ── Session ───────────────────────────────────────────────────────────────────
MAX_HISTORY_TURNS = 10   # how many conversation turns to keep in context
