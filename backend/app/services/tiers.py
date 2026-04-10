"""Analysis tier configuration and cost tracking.

Tiers:
  premium  — Sonnet readers + Opus synth   (~$2.70/analysis)
  standard — Haiku readers  + Opus synth   (~$0.55/analysis)
  economy  — Haiku readers  + Sonnet synth (~$0.20/analysis)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from app.core.config import settings


@dataclass
class TierConfig:
    name: str
    reader_model: str
    synth_model: str
    description: str


TIERS: dict[str, TierConfig] = {
    "premium": TierConfig(
        name="Premium",
        reader_model=settings.anthropic_model,       # Sonnet
        synth_model=settings.anthropic_model_deep,    # Opus
        description="Sonnet readers + Opus synthesis — maximum quality",
    ),
    "standard": TierConfig(
        name="Standard",
        reader_model=settings.anthropic_model_fast,   # Haiku
        synth_model=settings.anthropic_model_deep,    # Opus
        description="Haiku readers + Opus synthesis — best value",
    ),
    "economy": TierConfig(
        name="Economy",
        reader_model=settings.anthropic_model_fast,   # Haiku
        synth_model=settings.anthropic_model,          # Sonnet
        description="Haiku readers + Sonnet synthesis — lowest cost",
    ),
}


def get_tier(tier_name: str) -> TierConfig:
    return TIERS.get(tier_name, TIERS["premium"])


@dataclass
class CostTracker:
    """Tracks token usage and calculates real USD cost per analysis."""
    input_tokens: int = 0
    output_tokens: int = 0
    calls: list[dict] = field(default_factory=list)

    def record(self, model: str, input_tok: int, output_tok: int) -> None:
        self.input_tokens += input_tok
        self.output_tokens += output_tok
        self.calls.append({
            "model": model,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
        })

    @property
    def total_cost_usd(self) -> float:
        total = 0.0
        for call in self.calls:
            model = call["model"]
            prices = settings.pricing.get(model, {"input": 0, "output": 0})
            total += (call["input_tokens"] / 1_000_000) * prices["input"]
            total += (call["output_tokens"] / 1_000_000) * prices["output"]
        return round(total, 6)

    def summary(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost_usd": self.total_cost_usd,
            "calls": len(self.calls),
        }
