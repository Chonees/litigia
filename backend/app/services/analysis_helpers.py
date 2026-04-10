"""Shared infrastructure for the predictive analysis pipeline.

Rate limiting, API retry logic, input validation, and text parsing utilities.
"""

import asyncio
import json
import random
import re
import time

import anthropic

from app.core.config import settings


# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter
# ---------------------------------------------------------------------------

class TokenBucketLimiter:
    """Async token bucket that enforces RPM limits across concurrent tasks.

    Tokens refill at a steady rate (rpm / 60 per second).  Each API call
    must acquire a token before proceeding.  If the bucket is empty the
    caller sleeps until the next token is available — no busy-waiting.
    """

    def __init__(self, rpm: int) -> None:
        self._rpm = max(rpm, 1)
        self._interval = 60.0 / self._rpm          # seconds between tokens
        self._tokens = float(self._rpm)             # start full
        self._max_tokens = float(self._rpm)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1.0:
                wait = self._interval * (1.0 - self._tokens)
                await asyncio.sleep(wait)
                self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed / self._interval)
        self._last_refill = now


# Module-level limiter — shared across requests, respects RPM
rate_limiter = TokenBucketLimiter(settings.anthropic_rpm)


# ---------------------------------------------------------------------------
# Claude API client
# ---------------------------------------------------------------------------

def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

class CancelledError(Exception):
    """Raised when analysis is cancelled by client."""
    pass


# ---------------------------------------------------------------------------
# API retry with rate limiting
# ---------------------------------------------------------------------------

async def call_with_retry(
    client: anthropic.AsyncAnthropic,
    cancel: asyncio.Event | None = None,
    **kwargs,
) -> anthropic.types.Message:
    """Call Claude with rate limiting + exponential backoff on 429.
    Checks cancel event BEFORE every API call."""
    max_retries = settings.anthropic_max_retries
    for attempt in range(max_retries + 1):
        # CHECK CANCEL before spending money
        if cancel and cancel.is_set():
            raise CancelledError("Analysis cancelled by user")

        await rate_limiter.acquire()

        # CHECK CANCEL again after waiting for rate limit
        if cancel and cancel.is_set():
            raise CancelledError("Analysis cancelled by user")

        try:
            return await client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            if attempt == max_retries:
                raise
            backoff = (10 * (2 ** attempt)) + random.uniform(0, 3)
            print(f"  [Rate limit] retry {attempt + 1}/{max_retries} in {backoff:.0f}s", flush=True)
            # Sleep in small chunks so we can check cancel
            for _ in range(int(backoff)):
                if cancel and cancel.is_set():
                    raise CancelledError("Analysis cancelled during retry backoff")
                await asyncio.sleep(1)
            await asyncio.sleep(backoff % 1)


# ---------------------------------------------------------------------------
# Input validation — prevent garbage queries from burning money
# ---------------------------------------------------------------------------

_LEGAL_KEYWORDS = re.compile(
    r"(?:despido|accidente|daño|responsabilidad|contrato|demanda|recurso|"
    r"amparo|cautelar|ejecuci[oó]n|quiebra|concurso|prescripci[oó]n|"
    r"inconstitucionalidad|alimento|divorcio|usucapi[oó]n|homicidio|"
    r"estafa|habeas|apelaci[oó]n|laboral|penal|civil|comercial|"
    r"tributari[oa]|societari[oa]|mala\s*praxis|indemnizaci[oó]n|"
    r"art[íi]culo|ley\s*\d|c[oó]digo|LCT|CCyCN|CSJN|AFIP|ART\b|"
    r"fallo|sentencia|juzgado|tribunal|c[aá]mara|emplead[oa]|"
    r"imputad[oa]|heredero|locaci[oó]n|desalojo|hipoteca|"
    r"honor[aá]rios|costas|prueba|pericia|embargo|medida)",
    re.IGNORECASE,
)

_MIN_CHARS = 15
_MIN_WORDS = 3


async def validate_case_input(caso: str) -> tuple[bool, str]:
    """Two-layer validation: heuristic + Haiku gate.

    Returns (is_valid, rejection_reason).
    """
    text = caso.strip()

    # Layer 1: hard heuristic — free, instant
    if len(text) < _MIN_CHARS:
        return False, (
            f"La descripción es muy corta ({len(text)} caracteres). "
            "Describí el caso con al menos un par de oraciones."
        )
    if len(text.split()) < _MIN_WORDS:
        return False, (
            "Necesito al menos unas pocas palabras describiendo el caso. "
            "Ej: 'Despido sin causa, empleado con 8 años de antigüedad en comercio.'"
        )

    # Layer 2: if legal keywords found → pass (clearly legal)
    if len(_LEGAL_KEYWORDS.findall(text)) >= 2:
        return True, ""

    # Layer 3: ambiguous input — ask Haiku ($0.0001, ~0.5s)
    try:
        client = get_client()
        resp = await client.messages.create(
            model=settings.anthropic_model_fast,
            max_tokens=5,
            messages=[{"role": "user", "content": (
                "¿El siguiente texto describe un caso legal, situación jurídica "
                "o consulta sobre derecho? Respondé SOLO 'SI' o 'NO'.\n\n"
                f"Texto: \"{text}\""
            )}],
        )
        answer = resp.content[0].text.strip().upper()
        if answer.startswith("SI") or answer.startswith("SÍ"):
            return True, ""
        return False, (
            "No parece una descripción de caso legal. "
            "Describí la situación jurídica que querés analizar."
        )
    except Exception:
        # If Haiku fails, let it through — don't block on validation errors
        return True, ""


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def clean_markup(text: str) -> str:
    text = re.sub(r"\[\[/?[a-z]+(?:\s[^\]]*?)?\]\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_json_response(text: str) -> list | dict:
    """Extract JSON from Claude response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return json.loads(text)
