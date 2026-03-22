"""
Thin wrapper around the Ollama REST API.
Handles timeouts, retries, and response extraction.
"""

import requests
import logging
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE, LLM_CTX_WINDOW, LLM_TIMEOUT_SEC

logger = logging.getLogger(__name__)


class OllamaClient:

    def __init__(
        self,
        base_url: str  = OLLAMA_BASE_URL,
        model: str     = OLLAMA_MODEL,
        temperature: float = LLM_TEMPERATURE,
        ctx_window: int    = LLM_CTX_WINDOW,
        timeout: int       = LLM_TIMEOUT_SEC,
    ):
        self.base_url    = base_url.rstrip("/")
        self.model       = model
        self.temperature = temperature
        self.ctx_window  = ctx_window
        self.timeout     = timeout

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the raw text response.
        Raises RuntimeError on failure.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model":  self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx":     self.ctx_window,
                "num_predict": 1024,
            },
        }

        logger.debug(f"LLM prompt ({len(prompt)} chars) → {url}")

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "").strip()
            logger.debug(f"LLM response ({len(text)} chars)")
            return text

        except requests.exceptions.Timeout:
            raise RuntimeError(f"Ollama timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Make sure Ollama is running: `ollama serve`"
            )
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error: {e}")

    def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False


# Singleton used throughout the app
llm_client = OllamaClient()
