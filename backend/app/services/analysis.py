"""Predictive analysis pipeline — public API facade.

Internal implementation is split across analysis_* modules by responsibility:
  analysis_prompts.py   — prompt templates
  analysis_helpers.py   — rate limiter, retry, validation, parsing
  analysis_search.py    — hybrid search + relevance threshold
  analysis_filters.py   — quality pre-filter
  analysis_display.py   — summary formatters
  analysis_agents.py    — reader + synthesizer agents
  analysis_pipeline.py  — orchestrator (stream + non-stream)
"""

from app.services.analysis_pipeline import (  # noqa: F401
    run_predictive_analysis_stream,
    run_predictive_analysis,
)
from app.services.analysis_search import search_cases as _search_cases  # noqa: F401

__all__ = [
    "run_predictive_analysis_stream",
    "run_predictive_analysis",
    "_search_cases",
]
