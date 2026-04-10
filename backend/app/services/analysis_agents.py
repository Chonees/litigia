"""Reader and synthesizer agents for the predictive analysis pipeline.

_analyze_single: one reader agent per fallo — extracts structured legal data.
_synthesize: one synthesizer agent — cross-references all analyses into strategy.
"""

import asyncio

from app.core.config import settings
from app.services.analysis_prompts import READER_PROMPT, SYNTHESIZER_PROMPT
from app.services.analysis_helpers import (
    get_client,
    call_with_retry,
    parse_json_response,
    CancelledError,
)
from app.services.analysis_display import build_agent_summary


async def analyze_single(
    caso: str,
    fallo: dict,
    fallo_index: int,
    reader_model: str | None = None,
    cost_tracker=None,
    event_queue: "asyncio.Queue | None" = None,
    cancel: "asyncio.Event | None" = None,
    transparency: bool = False,
) -> dict | None:
    """One reader agent: analyze a single fallo, return structured JSON."""
    model = reader_model or settings.anthropic_model
    agent_id = fallo_index
    caratula = fallo.get("caratula", "N/D")

    # Check cancel before doing anything
    if cancel and cancel.is_set():
        return None

    tribunal = fallo.get("tribunal", "N/D")
    fecha = fallo.get("fecha", "N/D")
    materia = fallo.get("materia", "N/D")

    # Notify: agent starting — step 1
    if event_queue:
        await event_queue.put({
            "type": "agent_status",
            "agent_id": agent_id,
            "status": "active",
            "thinking": f"Leyendo fallo...\n{caratula[:80]}\nTribunal: {tribunal}\nFecha: {fecha}",
        })

    try:
        prompt_text = READER_PROMPT.format(
            caso=caso,
            tribunal=tribunal,
            fecha=fecha,
            caratula=caratula,
            materia=materia,
            texto=fallo.get("texto", ""),
        )

        if transparency:
            prompt_text += """

IMPORTANTE — MODO TRANSPARENCIA:
ANTES del JSON, escribi tu razonamiento paso a paso en texto libre entre las etiquetas <razonamiento> y </razonamiento>. Explicá:
1. Qué partes del fallo leíste y qué te llamó la atención
2. Cómo determinaste el resultado (favorable/desfavorable/parcial/inadmisible)
3. Por qué elegiste las normas y precedentes que elegiste
4. Cómo evaluaste la relevancia para el caso del cliente

Formato:
<razonamiento>
Tu razonamiento paso a paso...
</razonamiento>

{el JSON como siempre}"""

        # max_tokens is a ceiling, not a cost — Anthropic charges only generated tokens.
        # Low caps just truncate JSON mid-string → parse errors.
        # 8192 = Haiku's max output. Model stops naturally when done.
        max_tok = 8192

        response = await call_with_retry(
            get_client(),
            cancel=cancel,
            model=model,
            max_tokens=max_tok,
            messages=[{
                "role": "user",
                "content": prompt_text,
            }],
        )
        raw_response = response.content[0].text
        if cost_tracker:
            cost_tracker.record(model, response.usage.input_tokens, response.usage.output_tokens)

        # Parse reasoning and JSON separately when transparency is on
        reasoning = ""
        json_text = raw_response
        if transparency and "<razonamiento>" in raw_response:
            parts = raw_response.split("</razonamiento>")
            reasoning = parts[0].split("<razonamiento>")[-1].strip()
            json_text = parts[-1].strip() if len(parts) > 1 else raw_response

        analysis = parse_json_response(json_text)
        analysis["_raw_claude_response"] = raw_response
        if reasoning:
            analysis["reasoning"] = reasoning
    except CancelledError:
        return None
    except Exception as e:
        print(f"  [Reader {fallo_index}] Error: {e}", flush=True)
        if event_queue:
            await event_queue.put({
                "type": "agent_status",
                "agent_id": agent_id,
                "status": "error",
                "thinking": f"Error: {str(e)[:100]}",
            })
        return None

    # Enrich with metadata
    analysis["caratula"] = caratula
    analysis["tribunal"] = fallo.get("tribunal", "N/D")
    analysis["fecha"] = fallo.get("fecha", "N/D")
    analysis["score"] = fallo.get("score", 0.0)
    analysis["source_id"] = fallo.get("source_id", fallo.get("id", ""))
    analysis["_original_texto"] = fallo.get("texto", "")  # for synthesizer context

    # Agent thinking: use reasoning (transparency) if available, else build human-readable summary
    if analysis.get("reasoning"):
        analysis["agent_thinking"] = analysis["reasoning"]
    else:
        analysis["agent_thinking"] = build_agent_summary(analysis, caratula)
    resultado = analysis.get("resultado", "N/D")

    if event_queue:
        await event_queue.put({
            "type": "agent_status",
            "agent_id": agent_id,
            "status": "done",
            "thinking": analysis["agent_thinking"],
            "resultado": resultado,
        })

    return analysis


async def synthesize(
    caso: str,
    all_analyses: list[dict],
    synth_model: str | None = None,
    cost_tracker=None,
    cancel: "asyncio.Event | None" = None,
) -> dict:
    """Synthesizer agent: cross-reference patterns and generate strategic report."""
    # Build compact text for synthesizer (structured data, not full text)
    analyses_text = ""
    for i, a in enumerate(all_analyses):
        normas = a.get("normas_citadas", a.get("leyes_citadas", []))
        precedentes = a.get("precedentes_citados", [])
        analyses_text += (
            f"\n[{i+1}] {a.get('caratula', 'N/D')} — {a.get('tribunal', '')} — {a.get('fecha', '')}\n"
            f"  Resultado: {a.get('resultado', 'N/D')}\n"
            f"  Vía procesal: {a.get('via_procesal', 'N/D')}\n"
            f"  Normas: {', '.join(normas) if normas else 'N/D'}\n"
            f"  Precedentes: {', '.join(precedentes) if precedentes else 'N/D'}\n"
            f"  Doctrina: {a.get('doctrina_aplicada', 'N/D')}\n"
            f"  Hechos determinantes: {a.get('hechos_determinantes', 'N/D')}\n"
            f"  Prueba decisiva: {a.get('prueba_decisiva', 'N/D')}\n"
            f"  Quantum/costas: {a.get('quantum', 'N/D')}\n"
            f"  Votos: {a.get('votos', 'N/D')}\n"
            f"  Estrategia: {a.get('estrategia', '')}\n"
            f"  Argumento clave: {a.get('argumento_clave', '')}\n"
            f"  Razón resultado: {a.get('razon_resultado', '')}\n"
            f"  Relevancia cliente: {a.get('relevancia_cliente', '')}\n"
        )

    # --- Top fallos completos para el sintetizador ---
    top_favorable = sorted(
        [a for a in all_analyses if a.get("resultado") == "favorable"],
        key=lambda x: x.get("score", 0), reverse=True,
    )[:3]
    top_desfavorable = sorted(
        [a for a in all_analyses if a.get("resultado") == "desfavorable"],
        key=lambda x: x.get("score", 0), reverse=True,
    )[:2]

    key_texts = ""
    for label, fallos in [("FAVORABLE", top_favorable), ("DESFAVORABLE", top_desfavorable)]:
        for f in fallos:
            texto = f.get("_original_texto", "")[:3000]  # max 3K chars each
            if texto:
                key_texts += f"\n\n--- FALLO COMPLETO ({label}): {f.get('caratula', 'N/D')} ---\n{texto}\n"

    synth_content = SYNTHESIZER_PROMPT.format(
        caso=caso,
        n=len(all_analyses),
        analyses_text=analyses_text,
    )
    if key_texts:
        synth_content += f"\n\nTEXTOS COMPLETOS DE LOS FALLOS MÁS RELEVANTES (para verificar citas y lenguaje doctrinal):{key_texts}"

    model = synth_model or settings.anthropic_model_deep
    try:
        response = await call_with_retry(
            get_client(),
            cancel=cancel,
            model=model,
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": synth_content,
            }],
        )
        raw_synth = response.content[0].text
        if cost_tracker:
            cost_tracker.record(model, response.usage.input_tokens, response.usage.output_tokens)
        result = parse_json_response(raw_synth)
        result["_raw_claude_response"] = raw_synth
        return result
    except Exception as e:
        print(f"  [Synthesizer] Error: {e}", flush=True)
        # Manual fallback: compute basic stats
        favorable = sum(1 for a in all_analyses if a.get("resultado") == "favorable")
        total = len(all_analyses) or 1
        return {
            "porcentaje_favorable": round(favorable / total * 100, 1),
            "estrategias_exitosas": [],
            "estrategias_fracasadas": [],
            "leyes_clave": [],
            "riesgos": ["Error en síntesis — se muestran estadísticas básicas"],
            "recomendacion_estrategica": f"De {total} fallos analizados, {favorable} fueron favorables ({round(favorable/total*100, 1)}%).",
        }
