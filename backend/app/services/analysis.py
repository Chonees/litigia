"""Análisis predictivo — pipeline de agentes orquestados.

3 capas:
  1. Búsqueda vectorial (ChromaDB, local)
  2. 100 agentes lectores — 1 fallo cada uno, rate-limited (Sonnet)
  3. 1 agente sintetizador (Opus, genera informe estratégico)
"""

import asyncio
import json
import random
import re
import time
from typing import AsyncGenerator

import anthropic

from app.core.config import settings
from app.models.schemas import (
    AnalisisResponse,
    EstrategiaRanked,
    FalloAnalizado,
    JurisprudenciaQuery,
)
from app.services.embeddings import get_single_embedding
from app.services.vector_store import search_similar

TOP_K = 100

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

READER_PROMPT = """Sos un abogado litigante argentino con 15 años de experiencia en tribunales. Tu trabajo es leer un fallo completo y extraer TODO lo que un litigante necesita saber para usar este precedente en un caso similar.

CASO DEL CLIENTE:
{caso}

FALLO A ANALIZAR:
Tribunal: {tribunal}
Fecha: {fecha}
Carátula: {caratula}
Materia: {materia}

TEXTO COMPLETO:
{texto}

INSTRUCCIONES — Leé el fallo como un litigante que prepara su caso:

1. RESULTADO: Clasificá desde la perspectiva del ACTOR (quien demanda/recurre):
   - "favorable": el actor obtuvo lo que pidió (total o sustancialmente)
   - "desfavorable": el actor perdió en el fondo
   - "parcial": se hizo lugar parcialmente (ej: se reconoció el derecho pero se redujo el monto)
   - "inadmisible": rechazado por cuestiones formales sin entrar al fondo (art. 280 CPCCN, acordada 4/2007, art. 14 ley 48, defectos de fundamentación)

2. NORMAS CITADAS: Extraé TODAS las que el tribunal invoca en los Considerandos y la parte resolutiva:
   - Artículos de códigos con nombre (ej: "Art. 245 LCT", "Art. 1078 CCyCN", "Art. 18 CN")
   - Leyes con número (ej: "Ley 20.744", "Ley 24.557")
   - Tratados internacionales y convenios (ej: "Convenio OIT 158", "CADH art. 25")
   - Acordadas de la CSJN (ej: "Acordada 4/2007")

3. PRECEDENTES CITADOS: Extraé los fallos que el tribunal cita como fundamento:
   - Formato Fallos: (ej: "Fallos: 337:315")
   - Por carátula (ej: "Vizzoti c/ AMSA", "Aquino")
   - Dictámenes de la Procuración General citados

4. VÍA PROCESAL: ¿Cómo llegó el caso a este tribunal?
   - Recurso extraordinario federal (art. 14 ley 48)
   - Recurso de queja por REX denegado (art. 285 CPCCN)
   - Amparo (art. 43 CN)
   - Acción declarativa de inconstitucionalidad
   - Acción de daños y perjuicios
   - Competencia originaria CSJN (art. 117 CN)
   - Incidente de verificación en quiebra
   - Otra (especificar)

5. DOCTRINA APLICADA: ¿Qué principio jurídico fundamentó la resolución?
   (ej: arbitrariedad de sentencia, gravedad institucional, cuestión federal, in dubio pro operario, reparación integral, interés superior del niño, principio protectorio, irrenunciabilidad, etc.)

6. HECHOS DETERMINANTES: ¿Qué hechos del caso fueron decisivos para el resultado? Esto es clave para saber si el precedente aplica al caso del cliente. (2-3 oraciones)

7. PRUEBA DECISIVA: ¿Qué prueba mencionó el tribunal como determinante? ¿Hubo déficit probatorio que perjudicó a alguna parte? (1-2 oraciones, "N/D" si no surge del texto)

8. QUANTUM Y COSTAS: Si el fallo menciona montos de condena, indemnización, rubros liquidados, tasa de interés o imposición de costas, extraelos. Si no se mencionan, poné "N/D".

9. VOTOS Y DISIDENCIAS: ¿Fue unánime o hubo disidencia? Si hubo, ¿qué postura tenía la disidencia? (1 oración, "unánime" si no hubo)

10. RELEVANCIA PARA EL CLIENTE: En 1-2 oraciones, explicá POR QUÉ este fallo le sirve (o no) al caso del cliente. ¿Los hechos son análogos? ¿La doctrina aplica? ¿Hay un distinguishing importante?

Respondé con un JSON object:
{{
  "resultado": "favorable|desfavorable|parcial|inadmisible",
  "normas_citadas": ["Art. X Ley Y", ...],
  "precedentes_citados": ["Fallos: XXX:YYY", "Carátula", ...],
  "via_procesal": "descripción de la vía",
  "doctrina_aplicada": "principio jurídico central",
  "hechos_determinantes": "qué hechos fueron decisivos (2-3 oraciones)",
  "prueba_decisiva": "qué prueba fue clave o qué faltó probar",
  "quantum": "montos, rubros, tasa de interés, costas — o N/D",
  "votos": "unánime | mayoría X-Y, disidencia de [nombre]: [postura breve]",
  "estrategia": "estrategia procesal de la parte ganadora (1-2 oraciones)",
  "argumento_clave": "el argumento que convenció al tribunal (1-2 oraciones)",
  "razon_resultado": "por qué se resolvió así, específicamente (2-3 oraciones)",
  "relevancia_cliente": "por qué le sirve o no al caso del cliente (1-2 oraciones)"
}}

Respondé SOLO con el JSON, sin texto adicional."""

SYNTHESIZER_PROMPT = """Sos un abogado litigante argentino senior con 20 años de experiencia ante la CSJN, cámaras federales y tribunales de todo el país. Un cliente te consulta sobre un caso. Tu equipo de asociados ya leyó y clasificó {n} fallos similares. Ahora tenés que cruzar toda esa información y armar la TEORÍA DEL CASO.

CASO DEL CLIENTE:
{caso}

FALLOS ANALIZADOS POR TU EQUIPO:
{analyses_text}

INSTRUCCIONES — Pensá como un litigante que prepara su caso:

ESTADÍSTICAS:
- Contá favorables, desfavorables, parciales e inadmisibles por separado.
- El % favorable se calcula SOLO sobre los que entraron al fondo (excluí inadmisibles).

ANÁLISIS DE ESTRATEGIAS — LISTÁ TODAS, sin excepción:
- Agrupá las estrategias por VÍA PROCESAL (REX, queja, amparo, daños, etc.).
- Dentro de cada vía, agrupá por DOCTRINA APLICADA (arbitrariedad, gravedad institucional, etc.).
- Para cada estrategia, calculá cuántas veces se usó y cuántas fueron exitosas.
- IMPORTANTE: Listá TODAS las estrategias que encontraste, no solo las top 3. Ordenalas de mayor a menor tasa de éxito.
- Hacé lo mismo con las fracasadas: TODAS, ordenadas de menor a mayor tasa de éxito.

ANÁLISIS NORMATIVO:
- Las normas más citadas en fallos FAVORABLES son las que el abogado DEBE invocar.
- Distinguí entre normas sustantivas (derechos de fondo) y procesales (vías recursivas).

ANÁLISIS DE PRECEDENTES:
- Identificá los 5-10 precedentes más fuertes para citar en el escrito.
- Priorizá los más recientes, los de la CSJN, y los que tienen hechos más análogos al caso del cliente.

ANÁLISIS DE HECHOS:
- ¿Qué patrón fáctico comparten los casos favorables? (ej: todos tenían prueba pericial, todos demostraron el nexo causal, etc.)
- ¿Qué faltó en los desfavorables? (ej: déficit probatorio, falta de reclamo previo, etc.)

ANÁLISIS DE QUANTUM (si aplica):
- Si hay datos de montos/rubros/intereses, ¿cuál es el rango? ¿Hay un piso y un techo estimable?

ANÁLISIS DE COSTAS:
- ¿Cuál es el patrón de imposición de costas?

RIESGOS:
- Cada riesgo debe citar un caso CONCRETO que perdió y POR QUÉ. No quiero genéricos como "podría ser rechazado" — quiero "en el caso Pérez c/ ANSES (2024), se rechazó porque no se acreditó la relación laboral por falta de recibos de sueldo".

RECOMENDACIÓN ESTRATÉGICA:
- Armá un párrafo de 5-10 oraciones que funcione como GUÍA DE ACCIÓN para el abogado:
  (1) Qué vía procesal elegir y por qué
  (2) Qué normas invocar en el escrito (las más citadas en fallos favorables)
  (3) Qué precedentes citar y cómo usarlos
  (4) Qué doctrina plantear
  (5) Qué prueba es imprescindible producir (basado en lo que fue decisivo en casos similares)
  (6) Qué argumentos EVITAR (basado en lo que fracasó)
  (7) Si hay disidencias relevantes que podrían anticipar un cambio de jurisprudencia

Respondé con un JSON:
{{
  "total_analizados": {n},
  "favorables": (int),
  "desfavorables": (int),
  "parciales": (int),
  "inadmisibles": (int),
  "porcentaje_favorable": (float, excluye inadmisibles),
  "patron_factico_favorable": "qué tienen en común los casos que ganaron (2-3 oraciones)",
  "patron_factico_desfavorable": "qué tienen en común los que perdieron (2-3 oraciones)",
  "estrategias_exitosas": [
    {{
      "estrategia": "Vía procesal + doctrina + cómo se aplicó",
      "frecuencia": (int),
      "tasa_exito": (float),
      "leyes_asociadas": ["Art. X Ley Y", ...],
      "precedentes_clave": ["Fallos: XXX:YYY", ...],
      "caso_ejemplo": "carátula del caso más representativo"
    }}
    // TODAS las estrategias con tasa_exito > 0, ordenadas de mayor a menor tasa_exito
  ],
  "estrategias_fracasadas": [
    // mismo formato, TODAS las que tuvieron tasa_exito == 0 o < 50%, de menor a mayor
  ],
  "normas_clave": ["normas más citadas en favorables, orden de frecuencia"],
  "precedentes_para_citar": ["los 5-10 mejores precedentes para el escrito"],
  "prueba_necesaria": ["qué prueba debe producir el abogado basado en los patrones"],
  "rango_quantum": "estimación de montos si hay datos, o N/D",
  "patron_costas": "cómo se impusieron las costas en la mayoría de los casos",
  "riesgos": ["riesgo concreto citando caso que perdió y por qué", ...],
  "disidencias_relevantes": ["si alguna disidencia anticipa cambio de jurisprudencia"],
  "recomendacion_estrategica": "párrafo de 5-10 oraciones — guía de acción completa"
}}

Respondé SOLO con el JSON, sin texto adicional."""


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
_rate_limiter = TokenBucketLimiter(settings.anthropic_rpm)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _clean_markup(text: str) -> str:
    text = re.sub(r"\[\[/?[a-z]+(?:\s[^\]]*?)?\]\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_json_response(text: str) -> list | dict:
    """Extract JSON from Claude response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Layer 1 — Vector search (local, no API)
# ---------------------------------------------------------------------------

async def _search_cases(caso: str, fuero: str | None) -> list[dict]:
    """Search ChromaDB for similar cases. Returns raw result dicts."""
    search_text = caso
    if fuero:
        search_text += f" fuero {fuero}"

    embedding = await get_single_embedding(search_text)

    results = await search_similar(
        query_embedding=embedding,
        top_k=TOP_K,
        fuero=fuero,
    )

    # Fallback without filters
    if not results and fuero:
        results = await search_similar(
            query_embedding=embedding,
            top_k=TOP_K,
        )

    # Clean markup
    for r in results:
        for key in ("texto", "sumario", "caratula"):
            if r.get(key):
                r[key] = _clean_markup(r[key])

    return results


# ---------------------------------------------------------------------------
# Layer 2 — Reader agents (1 per fallo, CONCURRENCY parallel)
# ---------------------------------------------------------------------------

async def _call_with_retry(
    client: anthropic.AsyncAnthropic,
    **kwargs,
) -> anthropic.types.Message:
    """Call Claude with rate limiting + exponential backoff on 429."""
    max_retries = settings.anthropic_max_retries
    for attempt in range(max_retries + 1):
        await _rate_limiter.acquire()
        try:
            return await client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            if attempt == max_retries:
                raise
            # Backoff: 10s, 20s, 40s, 80s, 160s + jitter 0-3s
            backoff = (10 * (2 ** attempt)) + random.uniform(0, 3)
            print(f"  [Rate limit] retry {attempt + 1}/{max_retries} in {backoff:.0f}s", flush=True)
            await asyncio.sleep(backoff)


async def _analyze_single(
    caso: str,
    fallo: dict,
    fallo_index: int,
) -> dict | None:
    """One reader agent: analyze a single fallo, return structured JSON."""
    try:
        response = await _call_with_retry(
            _get_client(),
            model=settings.anthropic_model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": READER_PROMPT.format(
                    caso=caso,
                    tribunal=fallo.get("tribunal", "N/D"),
                    fecha=fallo.get("fecha", "N/D"),
                    caratula=fallo.get("caratula", "N/D"),
                    materia=fallo.get("materia", "N/D"),
                    texto=fallo.get("texto", ""),
                ),
            }],
        )
        analysis = _parse_json_response(response.content[0].text)
    except Exception as e:
        print(f"  [Reader {fallo_index}] Error: {e}", flush=True)
        return None

    # Enrich with metadata from original result
    analysis["caratula"] = fallo.get("caratula", "N/D")
    analysis["tribunal"] = fallo.get("tribunal", "N/D")
    analysis["fecha"] = fallo.get("fecha", "N/D")
    analysis["score"] = fallo.get("score", 0.0)
    analysis["source_id"] = fallo.get("source_id", fallo.get("id", ""))
    return analysis


# ---------------------------------------------------------------------------
# Layer 3 — Synthesizer agent (1 Claude call)
# ---------------------------------------------------------------------------

async def _synthesize(caso: str, all_analyses: list[dict]) -> dict:
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

    try:
        response = await _call_with_retry(
            _get_client(),
            model=settings.anthropic_model_deep,
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": SYNTHESIZER_PROMPT.format(
                    caso=caso,
                    n=len(all_analyses),
                    analyses_text=analyses_text,
                ),
            }],
        )
        return _parse_json_response(response.content[0].text)
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


# ---------------------------------------------------------------------------
# Orchestrator — streaming with progress
# ---------------------------------------------------------------------------

async def run_predictive_analysis_stream(
    caso: str,
    fuero: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Run full 3-layer pipeline, yielding progress events."""

    # --- Layer 1: Search ---
    yield {"step": "search", "progress": 0, "detail": "Buscando fallos similares..."}
    results = await _search_cases(caso, fuero)
    total = len(results)
    yield {"step": "search", "progress": 0, "detail": f"{total} fallos encontrados"}

    if not total:
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
    yield {"step": "analyze", "progress": 0, "detail": f"Analizando {total} fallos ({rpm} req/min)..."}

    all_analyses: list[dict] = []
    completed = 0

    tasks = [
        _analyze_single(caso, fallo, i)
        for i, fallo in enumerate(results)
    ]

    for coro in asyncio.as_completed(tasks):
        analysis = await coro
        if analysis is not None:
            all_analyses.append(analysis)
        completed += 1
        pct = int(completed / total * 100)
        yield {
            "step": "analyze",
            "progress": pct,
            "detail": f"{completed}/{total} fallos leídos ({len(all_analyses)} con resultado)",
        }

    # --- Layer 3: Synthesizer ---
    yield {"step": "synthesize", "progress": 100, "detail": "Generando informe estratégico..."}
    synthesis = await _synthesize(caso, all_analyses)

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

        fa = FalloAnalizado(
            caratula=a.get("caratula", "N/D"),
            tribunal=a.get("tribunal", "N/D"),
            fecha=a.get("fecha", "N/D"),
            resultado=resultado,
            normas_citadas=a.get("normas_citadas", a.get("leyes_citadas", [])),
            precedentes_citados=a.get("precedentes_citados", []),
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
        )
        detalle.append(fa)
        if fa.resultado == "favorable" and (best_fav is None or fa.score > best_fav.score):
            best_fav = fa
        if fa.resultado == "desfavorable" and (best_desfav is None or fa.score > best_desfav.score):
            best_desfav = fa

    response = AnalisisResponse(
        fallos_analizados=len(all_analyses),
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
        recomendacion_estrategica=synthesis.get("recomendacion_estrategica", ""),
        caso_mas_similar_favorable=best_fav,
        caso_mas_similar_desfavorable=best_desfav,
        fallos_analizados_detalle=detalle,
    )

    yield {"step": "done", "progress": 100, "result": response.model_dump()}


# ---------------------------------------------------------------------------
# Non-streaming wrapper (for the regular POST endpoint)
# ---------------------------------------------------------------------------

async def run_predictive_analysis(
    caso: str,
    fuero: str | None = None,
) -> AnalisisResponse:
    """Run full pipeline, return final result (no streaming)."""
    result = None
    async for event in run_predictive_analysis_stream(caso, fuero):
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
