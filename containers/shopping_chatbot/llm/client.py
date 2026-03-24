"""
Thin wrapper around the Ollama REST API.
Handles timeouts, retries, and response extraction.
"""

import requests
import logging
import time
from config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_TEMPERATURE,
    LLM_CTX_WINDOW,
    LLM_TIMEOUT_SEC,
    LLM_NUM_PREDICT,
    OLLAMA_KEEP_ALIVE,
)

logger = logging.getLogger(__name__)


class OllamaClient:

    def __init__(
        self,
        base_url: str  = OLLAMA_BASE_URL,
        model: str     = OLLAMA_MODEL,
        temperature: float = LLM_TEMPERATURE,
        ctx_window: int    = LLM_CTX_WINDOW,
        timeout: int       = LLM_TIMEOUT_SEC,
        num_predict: int   = LLM_NUM_PREDICT,
        keep_alive: str    = OLLAMA_KEEP_ALIVE,
    ):
        self.base_url    = base_url.rstrip("/")
        self.model       = model
        self.temperature = temperature
        self.ctx_window  = ctx_window
        self.timeout     = timeout
        self.num_predict = num_predict
        self.keep_alive  = keep_alive

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
            "keep_alive": int(self.keep_alive) if str(self.keep_alive).lstrip('-').isdigit() else self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "num_ctx":     self.ctx_window,
                "num_predict": self.num_predict,
            },
        }

        start = time.perf_counter()
        logger.info(
            "LLM request started: prompt_chars=%s num_ctx=%s num_predict=%s model=%s",
            len(prompt),
            self.ctx_window,
            self.num_predict,
            self.model,
        )

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "").strip()
            elapsed = time.perf_counter() - start
            logger.info(
                "LLM request finished in %.3fs: response_chars=%s total_duration_ns=%s load_duration_ns=%s prompt_eval_count=%s prompt_eval_duration_ns=%s eval_count=%s eval_duration_ns=%s",
                elapsed,
                len(text),
                data.get("total_duration"),
                data.get("load_duration"),
                data.get("prompt_eval_count"),
                data.get("prompt_eval_duration"),
                data.get("eval_count"),
                data.get("eval_duration"),
            )
            return text

        except requests.exceptions.Timeout:
            elapsed = time.perf_counter() - start
            logger.error("LLM request timed out in %.3fs", elapsed)
            raise RuntimeError(f"Ollama timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            elapsed = time.perf_counter() - start
            logger.error("LLM connection failed in %.3fs", elapsed)
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. "
                "Make sure Ollama is running: `ollama serve`"
            )
        except requests.exceptions.HTTPError as e:
            elapsed = time.perf_counter() - start
            logger.error("LLM HTTP error in %.3fs: %s", elapsed, e)
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
