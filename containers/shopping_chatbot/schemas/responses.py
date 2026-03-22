"""
Pydantic schemas for FastAPI request bodies and response envelopes.
"""

from pydantic import BaseModel, Field
from typing import Any


# ── Requests ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str         = Field(..., min_length=1, max_length=1000,
                                    description="User's chat message")
    session_id: str | None  = Field(None,
                                    description="Existing session ID; omit to start new session")

    class Config:
        json_schema_extra = {
            "example": {
                "message":    "show me cricket bats under 1000 rupees",
                "session_id": None,
            }
        }


class NewSessionRequest(BaseModel):
    session_id: str | None = None


# ── Responses ─────────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    session_id:    str
    response_type: str
    message:       str
    data:          Any
    meta:          dict = {}

    class Config:
        json_schema_extra = {
            "example": {
                "session_id":    "abc-123",
                "response_type": "product_list",
                "message":       "Found 4 products.",
                "data": [
                    {
                        "id":        1,
                        "name":      "SG Campus Cricket Bat",
                        "brand":     "SG",
                        "price":     850,
                        "stock_qty": 45,
                        "rating":    4.2,
                    }
                ],
                "meta": {"total": 4, "filters_applied": {"max_price": 1000}},
            }
        }


class HealthResponse(BaseModel):
    status:      str
    db:          str
    llm:         str
    llm_model:   str
