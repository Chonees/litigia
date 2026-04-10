"""Orchestrator for the predictive analysis pipeline.

Wires search, filters, agents, and display into a streaming SSE pipeline.
Public API: run_predictive_analysis_stream, run_predictive_analysis.
"""

import asyncio
from typing import AsyncGenerator

from app.core.config import settings
from app.models.schemas import (
    AnalisisResponse,
    EstrategiaRanked,
    FalloAnalizado,
)
from app.services.analysis_helpers import validate_case_input, CancelledError
from app.services.analysis_search import search_cases
from app.services.analysis_filters import filter_low_quality, make_auto_inadmisible
from app.services.analysis_agents import analyze_single, synthesize
from app.services.analysis_display import build_synth_summary


async def run_predictive_analysis_stream(
    caso: str,
    fuero: str | None = None,
    tier: str = "premium",
    top_k: int = 100,
    transparency: bool = False,
    cancel: asyncio.Event | None = None,
) -> AsyncGenerator[dict, None]:
    """Run full 3-layer pipeline, yielding progress events.
    Pass a cancel Event — set it to stop all API calls immediately."""
    from app.services.tiers import get_tier, CostTracker

    if cancel is None:
        cancel = asyncio.Event()

    tier_config = get_tier(tier)
    cost = CostTracker()
    top_k = max(10, min(top_k, 100))  # clamp 10-100

    # --- Input validation (heuristic + Haiku gate) ---
    is_valid, rejection_reason = await validate_case_input(caso)
    if not is_valid:
        yield {
            "step": "error",
            "progress": 0,
            "detail": rejection_reason,
        }
        return

    # --- Log config ---
    print(f"\n[Analysis] tier={tier} reader={tier_config.reader_model} synth={tier_config.synth_model} top_k={top_k}", flush=True)

    # --- Layer 1: Search ---
    yield {"step": "search", "progress": 0, "detail": f"[{tier_config.name}] Buscando {top_k} fallos similares..."}
    results = await search_cases(caso, fuero, top_k=top_k)
    total = len(results)
    yield {"step": "search", "progress": 0, "detail": f"{total} fallos encontrados"}

    if not total:
        yield {
            "step": "done",
            "progress": 100,
            "result": AnalisisResponse(
                fallos_analizados=0,
                porcentaje_favorable=0.0,
                riesgos=["No se encontró jurisprudencia relevante para este caso"],
                recomendacion_estrategica="No se encontró jurisprudencia relevante en la base de datos. Probá con una descripción más específica del caso, incluyendo área del derecho, hechos y normas aplicables.",
            ).model_dump(),
        }
        return

    # --- Layer 1.25: Enrich chunks with full document text ---
    from app.services.fulltext_store import enrich_with_fulltext
    results = enrich_with_fulltext(results)

    # --- Layer 1.5: Quality pre-filter (no LLM, pure text matching) ---
    substantive_results, auto_noise = filter_low_quality(results)
    n_noise = len(auto_noise)
    if n_noise:
        yield {
            "step": "search",
            "progress": 0,
            "detail": (
                f"Pre-filtro: {len(substantive_results)}/{total} fallos sustantivos "
                f"({n_noise} ruido procesal auto-clasificado, ~${n_noise * 0.03:.2f} ahorrado)"
            ),
        }

    # Build pre-classified inadmisibles (no reader cost)
    auto_inadmisibles = [make_auto_inadmisible(f, i) for i, f in enumerate(auto_noise)]

    # Only reader-analyze the substantive results
    results_to_read = substantive_results
    total_to_read = len(results_to_read)

    if not total_to_read and not auto_inadmisibles:
        yield {
            "step": "done",
            "progress": 100,
            "result": AnalisisResponse(
                fallos_analizados=0,
                porcentaje_favorable=0.0,
                riesgos=["No se encontraron fallos similares"],
                recomendacion_estrategica="Sin datos suficientes para análisis.",
            ).model_dump(),
        }
        return

    # --- Layer 2: Reader agents (1 per fallo, rate-limited) ---
    rpm = settings.anthropic_rpm
    yield {
        "step": "analyze",
        "progress": 0,
        "detail": f"Analizando {total_to_read} fallos sustantivos ({rpm} req/min)...",
        "total_agents": total_to_read,
    }

    all_analyses: list[dict] = []
    completed = 0
    event_queue: asyncio.Queue = asyncio.Queue()

    tasks = [
        analyze_single(caso, fallo, i, reader_model=tier_config.reader_model, cost_tracker=cost, event_queue=event_queue, cancel=cancel, transparency=transparency)
        for i, fallo in enumerate(results_to_read)
    ]

    # Run tasks and drain agent events
    pending = set(asyncio.ensure_future(t) for t in tasks)
    cancelled = False
    while pending:
        # CHECK CANCEL — kill all pending tasks
        if cancel.is_set():
            print(f"[Analysis] CANCELLED — killing {len(pending)} pending tasks", flush=True)
            for task in pending:
                task.cancel()
            cancelled = True
            yield {"step": "cancelled", "progress": int(completed / total_to_read * 100) if total_to_read else 100, "detail": f"Cancelado. {completed}/{total_to_read} fallos procesados. Gasto: ${cost.total_cost_usd:.4f}", "cost_usd": cost.total_cost_usd}
            break

        # Drain all queued agent events (including stream_token)
        while not event_queue.empty():
            agent_event = event_queue.get_nowait()
            yield {"step": "agent_event", **agent_event, "cost_usd": cost.total_cost_usd}

        # Wait for next task (with timeout to keep checking cancel)
        done, pending = await asyncio.wait(pending, timeout=0.5, return_when=asyncio.FIRST_COMPLETED)
        for future in done:
            try:
                analysis = future.result()
            except (CancelledError, asyncio.CancelledError):
                analysis = None
            if analysis is not None:
                all_analyses.append(analysis)
            completed += 1
            pct = int(completed / total_to_read * 100) if total_to_read else 100
            yield {
                "step": "analyze",
                "progress": pct,
                "detail": f"{completed}/{total_to_read} fallos leídos ({len(all_analyses)} con resultado)",
                "cost_usd": cost.total_cost_usd,
            }

    if cancelled:
        return

    # Drain remaining events
    while not event_queue.empty():
        agent_event = event_queue.get_nowait()
        yield {"step": "agent_event", **agent_event, "cost_usd": cost.total_cost_usd}

    # Merge auto-classified inadmisibles into the full analyses list so the
    # synthesizer stats (total_analizados, inadmisibles) are accurate.
    all_analyses.extend(auto_inadmisibles)
    if auto_inadmisibles:
        print(
            f"  [QFilter] Merged {len(auto_inadmisibles)} pre-filtered inadmisibles "
            f"into final analyses (total: {len(all_analyses)})",
            flush=True,
        )

    # --- Layer 3: Synthesizer ---
    yield {"step": "synthesize", "progress": 100, "detail": f"Generando informe estratégico...", "cost_usd": cost.total_cost_usd}
    yield {"step": "agent_event", "type": "agent_status", "agent_id": -1, "status": "active", "thinking": f"Sintetizando {len(all_analyses)} analisis ({len(auto_inadmisibles)} pre-filtrados)...\nModelo: {tier_config.synth_model}\nCruzando patrones, estrategias, normas y riesgos...", "cost_usd": cost.total_cost_usd}

    # Only pass substantive analyses to the synthesizer — not the noise
    synthesis_input = [a for a in all_analyses if not a.get("_auto_filtered")]
    synthesis = await synthesize(caso, synthesis_input, synth_model=tier_config.synth_model, cost_tracker=cost, cancel=cancel)

    # Build human-readable synthesizer thinking
    synth_thinking = build_synth_summary(synthesis)

    yield {"step": "agent_event", "type": "agent_status", "agent_id": -1, "status": "done", "thinking": synth_thinking, "cost_usd": cost.total_cost_usd}

    # --- Build response ---
    detalle = []
    best_fav = None
    best_desfav = None
    n_fav = n_desfav = n_parcial = n_inadmisible = 0
    for a in all_analyses:
        resultado = a.get("resultado", "N/D")
        if resultado == "favorable":
            n_fav += 1
        elif resultado == "desfavorable":
            n_desfav += 1
        elif resultado == "parcial":
            n_parcial += 1
        elif resultado == "inadmisible":
            n_inadmisible += 1

        # Sanitize list fields — Claude sometimes returns "N/D" string instead of []
        def _ensure_list(val, fallback=None) -> list:
            if isinstance(val, list):
                return val
            if isinstance(val, str) and val and val != "N/D":
                return [val]
            return fallback or []

        fa = FalloAnalizado(
            caratula=a.get("caratula", "N/D"),
            tribunal=a.get("tribunal", "N/D"),
            fecha=a.get("fecha", "N/D"),
            resultado=resultado,
            normas_citadas=_ensure_list(a.get("normas_citadas", a.get("leyes_citadas", []))),
            precedentes_citados=_ensure_list(a.get("precedentes_citados", [])),
            via_procesal=a.get("via_procesal", ""),
            doctrina_aplicada=a.get("doctrina_aplicada", ""),
            hechos_determinantes=a.get("hechos_determinantes", ""),
            prueba_decisiva=a.get("prueba_decisiva", ""),
            quantum=a.get("quantum", ""),
            votos=a.get("votos", ""),
            estrategia=a.get("estrategia", ""),
            argumento_clave=a.get("argumento_clave", ""),
            razon_resultado=a.get("razon_resultado", ""),
            relevancia_cliente=a.get("relevancia_cliente", ""),
            score=a.get("score", 0.0),
            source_id=a.get("source_id", ""),
            agent_thinking=a.get("agent_thinking", ""),
            reasoning=a.get("reasoning", ""),
        )
        detalle.append(fa)
        if fa.resultado == "favorable" and (best_fav is None or fa.score > best_fav.score):
            best_fav = fa
        if fa.resultado == "desfavorable" and (best_desfav is None or fa.score > best_desfav.score):
            best_desfav = fa

    response = AnalisisResponse(
        fallos_analizados=len(all_analyses),  # includes pre-filtered inadmisibles
        favorables=n_fav,
        desfavorables=n_desfav,
        parciales=n_parcial,
        inadmisibles=n_inadmisible,
        porcentaje_favorable=float(synthesis.get("porcentaje_favorable", 0.0)),
        estrategias_exitosas=[
            EstrategiaRanked(**e) for e in synthesis.get("estrategias_exitosas", [])
        ],
        estrategias_fracasadas=[
            EstrategiaRanked(**e) for e in synthesis.get("estrategias_fracasadas", [])
        ],
        normas_clave=synthesis.get("normas_clave", synthesis.get("leyes_clave", [])),
        precedentes_para_citar=synthesis.get("precedentes_para_citar", []),
        riesgos=synthesis.get("riesgos", []),
        contradicciones=synthesis.get("contradicciones", []),
        recomendacion_estrategica=synthesis.get("recomendacion_estrategica", ""),
        caso_mas_similar_favorable=best_fav,
        caso_mas_similar_desfavorable=best_desfav,
        fallos_analizados_detalle=detalle,
    )

    result = response.model_dump()
    result["cost"] = cost.summary()
    result["cost"]["tier"] = tier
    result["cost"]["reader_model"] = tier_config.reader_model
    result["cost"]["synth_model"] = tier_config.synth_model
    result["synth_thinking"] = synth_thinking

    yield {"step": "done", "progress": 100, "result": result}


async def run_predictive_analysis(
    caso: str,
    fuero: str | None = None,
) -> AnalisisResponse:
    """Run full pipeline, return final result (no streaming)."""
    result = None
    async for event in run_predictive_analysis_stream(caso, fuero):
        if event.get("step") == "error":
            return AnalisisResponse(
                fallos_analizados=0,
                porcentaje_favorable=0.0,
                riesgos=[event.get("detail", "Input inválido")],
                recomendacion_estrategica=event.get("detail", "Input inválido"),
            )
        if event.get("step") == "done":
            result = event.get("result")
            break
        print(f"  [{event.get('step')}] {event.get('detail')}", flush=True)

    if result is None:
        return AnalisisResponse(
            fallos_analizados=0,
            porcentaje_favorable=0.0,
            riesgos=["Pipeline error"],
            recomendacion_estrategica="Error en el análisis.",
        )

    return AnalisisResponse(**result)
