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
from app.services.embeddings import get_query_embedding
from app.services.keyword_search import keyword_search
from app.services.reranker import rerank
from app.services.vector_store import search_similar, get_collection

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

CONTRADICCIONES JURISPRUDENCIALES:
- Identificá casos donde la MISMA norma o doctrina fue aplicada con resultados OPUESTOS
- Para cada contradicción: qué norma, qué fallos, por qué difieren (tribunal distinto, hechos diferentes, evolución temporal)
- Esto es CRÍTICO para el abogado — necesita saber dónde hay jurisprudencia contradictoria para anticipar la postura del tribunal

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
  "contradicciones": ["norma/doctrina X: fallo A (favorable) vs fallo B (desfavorable) — razón de la diferencia"],
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
# Layer 1 — Hybrid search: Vector + BM25 + Cross-encoder rerank
# ---------------------------------------------------------------------------

def _bm25_rerank(query: str, results: list[dict], top_k: int) -> list[dict]:
    """BM25 keyword search over pre-fetched results. Catches exact legal terms."""
    from rank_bm25 import BM25Okapi

    if not results:
        return results

    # Tokenize: simple whitespace + lowercase for Spanish legal text
    query_tokens = query.lower().split()
    corpus = []
    for r in results:
        text = f"{r.get('caratula', '')} {r.get('sumario', '')} {r.get('texto', '')[:1000]}"
        corpus.append(text.lower().split())

    bm25 = BM25Okapi(corpus)
    bm25_scores = bm25.get_scores(query_tokens)

    for r, score in zip(results, bm25_scores):
        r["bm25_score"] = float(score)

    return results


def _rrf_fusion(results: list[dict], k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion — merges vector + BM25 rankings."""
    # Rank by vector score
    by_vector = sorted(results, key=lambda r: r.get("score", 0), reverse=True)
    # Rank by BM25 score
    by_bm25 = sorted(results, key=lambda r: r.get("bm25_score", 0), reverse=True)

    rrf_scores: dict[str, float] = {}
    id_map: dict[str, dict] = {}

    for ranking in [by_vector, by_bm25]:
        for rank, doc in enumerate(ranking, 1):
            doc_id = doc.get("id", str(id(doc)))
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank)
            id_map[doc_id] = doc

    # Sort by RRF score
    sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    for doc_id in sorted_ids:
        id_map[doc_id]["rrf_score"] = rrf_scores[doc_id]

    return [id_map[doc_id] for doc_id in sorted_ids]


async def _search_cases(caso: str, fuero: str | None, top_k: int = 100) -> list[dict]:
    """Hybrid search: Vector + Global FTS5 keywords -> merge -> cross-encoder rerank."""
    search_text = caso
    if fuero:
        search_text += f" fuero {fuero}"

    embedding = await get_query_embedding(search_text)

    # --- Source 1: Vector search ---
    fetch_k = min(top_k * 3, 500)
    vector_results = await search_similar(query_embedding=embedding, top_k=fetch_k, fuero=fuero)
    if not vector_results and fuero:
        vector_results = await search_similar(query_embedding=embedding, top_k=fetch_k)
    print(f"  [Vector] {len(vector_results)} results", flush=True)

    # --- Source 2: Global FTS5 keyword search ---
    fts_ids = []
    try:
        fts_ids = keyword_search(caso, top_k=fetch_k)
        print(f"  [FTS5] {len(fts_ids)} keyword matches", flush=True)
    except Exception as e:
        print(f"  [FTS5] Skipped: {e}", flush=True)

    # Fetch FTS results from ChromaDB by ID
    fts_results = []
    if fts_ids:
        # Deduplicate FTS IDs before fetching from ChromaDB
        fts_ids = list(dict.fromkeys(fts_ids))[:100]
        collection = get_collection()
        try:
            fts_data = collection.get(ids=fts_ids, include=["documents", "metadatas"])
            for i, doc_id in enumerate(fts_data["ids"]):
                meta = fts_data["metadatas"][i] if fts_data["metadatas"] else {}
                fts_results.append({
                    "id": doc_id,
                    "score": 0.85,  # synthetic score for fusion
                    "texto": fts_data["documents"][i] if fts_data["documents"] else "",
                    **meta,
                })
        except Exception as e:
            print(f"  [FTS5>ChromaDB] Error fetching: {str(e).encode('ascii', 'replace').decode()}", flush=True)

    # --- Merge: combine both sources, dedup by ID ---
    seen_ids: set[str] = set()
    merged = []
    for r in vector_results:
        rid = r.get("id", "")
        if rid not in seen_ids:
            seen_ids.add(rid)
            r["_source"] = "vector"
            merged.append(r)
    fts_added = 0
    for r in fts_results:
        rid = r.get("id", "")
        if rid not in seen_ids:
            seen_ids.add(rid)
            r["_source"] = "fts"
            merged.append(r)
            fts_added += 1
    if fts_added:
        print(f"  [Merge] Added {fts_added} FTS-only results (not in vector top-{fetch_k})", flush=True)

    # Clean markup
    for r in merged:
        for key in ("texto", "sumario", "caratula"):
            if r.get(key):
                r[key] = _clean_markup(r[key])

    # --- Dedup by caratula ---
    seen_caratulas: set[str] = set()
    deduped = []
    for r in merged:
        key = r.get("caratula", "")[:60].lower().strip()
        if key and key in seen_caratulas:
            continue
        if key:
            seen_caratulas.add(key)
        deduped.append(r)
    if len(deduped) < len(merged):
        print(f"  [Dedup] {len(merged)} -> {len(deduped)}", flush=True)

    # --- Cross-encoder rerank for final precision ---
    if deduped:
        rerank_k = min(len(deduped), max(top_k * 2, 100), 200)
        print(f"  [Reranker] Scoring {rerank_k} candidates with bge-reranker-v2-m3...", flush=True)
        ranked = rerank(caso, deduped[:rerank_k], top_k=None)

        # --- Recency boost: newer fallos get a score bump ---
        # A 2026 fallo with rerank 0.80 beats a 2005 fallo with rerank 0.82
        # But a 2005 fallo with rerank 0.95 still beats a 2026 fallo with 0.80
        import re as _re
        from datetime import datetime
        current_year = datetime.now().year
        for r in ranked:
            fecha = r.get("fecha", "")
            year = None
            # Try to extract year from various date formats
            m = _re.search(r"(\d{4})", fecha)
            if m:
                year = int(m.group(1))
            if year and 1900 < year <= current_year:
                years_ago = current_year - year
                # Boost: 0.15 for this year, decaying to 0 for 30+ years ago
                recency_boost = max(0, 0.15 * (1 - years_ago / 30))
                r["_final_score"] = r.get("rerank_score", 0) + recency_boost
            else:
                r["_final_score"] = r.get("rerank_score", 0)

        ranked.sort(key=lambda r: r["_final_score"], reverse=True)
        newest = next((r for r in ranked if r.get("fecha")), None)
        if newest:
            print(f"  [Recency] Applied boost. Top result year: {newest.get('fecha','?')}", flush=True)

        # --- Diversity: cap per tribunal, but backfill if not enough ---
        MAX_PER_TRIBUNAL = max(5, top_k // 3)
        tribunal_counts: dict[str, int] = {}
        results = []
        skipped = []
        for r in ranked:
            tribunal = (r.get("tribunal", "") or "").strip()
            if not tribunal:
                results.append(r)
            else:
                count = tribunal_counts.get(tribunal, 0)
                if count < MAX_PER_TRIBUNAL:
                    results.append(r)
                    tribunal_counts[tribunal] = count + 1
                else:
                    skipped.append(r)
            if len(results) >= top_k:
                break

        # Backfill: if diversity filter left us short, add back skipped by rerank score
        if len(results) < top_k and skipped:
            need = top_k - len(results)
            results.extend(skipped[:need])

        print(f"  [Final] {len(results)} results (diversity cap {MAX_PER_TRIBUNAL}/tribunal). Best rerank: {results[0].get('rerank_score', 0):.3f}", flush=True)
        return results

    return deduped[:top_k]


# ---------------------------------------------------------------------------
# Layer 1.5 — Quality pre-filter (no LLM calls, pure text pattern matching)
# ---------------------------------------------------------------------------

def _filter_low_quality(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Classify search results as substantive or auto-inadmisible BEFORE sending to readers.

    Returns (substantive_results, auto_classified_inadmisibles).

    SKIP conditions (any one triggers skip):
    - texto length < 500 chars: too short to contain substantive content
    - "art. 280" or "articulo 280" AND length < 2000 chars: certiorari dismissal
    - "desestimase" or "desestimase" (accent variant) AND length < 1500 chars
    - "desistimiento" or "dase por desistido" AND length < 1500 chars
    - "caducidad de instancia" AND length < 1500 chars

    All skip conditions use lowercase matching on the texto field.
    """
    substantive: list[dict] = []
    noise: list[dict] = []

    for r in results:
        texto = r.get("texto", "") or ""
        texto_lower = texto.lower()
        length = len(texto)
        reason = None

        if length < 500:
            reason = f"texto muy corto ({length} chars)"

        elif (
            ("art. 280" in texto_lower or "articulo 280" in texto_lower or "artículo 280" in texto_lower)
            and length < 2000
        ):
            reason = f"art. 280 CPCCN ({length} chars) - certiorari sin fundamentacion"

        elif (
            ("desestimase" in texto_lower or "desestímase" in texto_lower)
            and length < 1500
        ):
            reason = f"desestimacion breve ({length} chars)"

        elif (
            ("desistimiento" in texto_lower or "dase por desistido" in texto_lower)
            and length < 1500
        ):
            reason = f"desistimiento ({length} chars)"

        elif "caducidad de instancia" in texto_lower and length < 1500:
            reason = f"caducidad de instancia ({length} chars)"

        if reason:
            caratula = r.get("caratula", "N/D")[:60]
            print(
                f"  [QFilter] SKIP: {caratula} -- {reason}",
                flush=True,
            )
            noise.append(r)
        else:
            substantive.append(r)

    total = len(results)
    n_pass = len(substantive)
    n_skip = len(noise)
    print(
        f"  [QFilter] {n_pass}/{total} passed quality check "
        f"({n_skip} auto-classified as inadmisible, saved ~${n_skip * 0.03:.2f})",
        flush=True,
    )
    return substantive, noise


def _make_auto_inadmisible(fallo: dict, index: int) -> dict:
    """Build a minimal FalloAnalizado-compatible dict for a pre-filtered fallo."""
    texto = fallo.get("texto", "") or ""
    length = len(texto)
    return {
        "caratula": fallo.get("caratula", "N/D"),
        "tribunal": fallo.get("tribunal", "N/D"),
        "fecha": fallo.get("fecha", "N/D"),
        "resultado": "inadmisible",
        "normas_citadas": [],
        "precedentes_citados": [],
        "via_procesal": "pre-filtrado automatico",
        "doctrina_aplicada": "",
        "hechos_determinantes": "",
        "prueba_decisiva": "",
        "quantum": "",
        "votos": "",
        "estrategia": "",
        "argumento_clave": "",
        "razon_resultado": (
            f"Pre-filtrado automatico: texto de {length} caracteres. "
            "Sin contenido sustantivo (ruido procesal: art. 280, desestimacion, "
            "desistimiento o caducidad). No se envio a agente lector."
        ),
        "relevancia_cliente": "Ninguna - fallo sin contenido de fondo.",
        "score": fallo.get("score", 0.0),
        "source_id": fallo.get("source_id", fallo.get("id", "")),
        "agent_thinking": "",
        "reasoning": "",
        "_raw_claude_response": "",
        "_original_texto": texto,
        "_auto_filtered": True,
    }


# ---------------------------------------------------------------------------
# Layer 2 — Reader agents (1 per fallo, CONCURRENCY parallel)
# ---------------------------------------------------------------------------

class CancelledError(Exception):
    """Raised when analysis is cancelled by client."""
    pass


async def _call_with_retry(
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

        await _rate_limiter.acquire()

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


async def _analyze_single(
    caso: str,
    fallo: dict,
    fallo_index: int,
    reader_model: str | None = None,
    cost_tracker: "CostTracker | None" = None,
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

    # Notify: agent starting
    if event_queue:
        await event_queue.put({
            "type": "agent_status",
            "agent_id": agent_id,
            "status": "active",
            "thinking": f"Leyendo: {caratula[:80]}...",
        })

    try:
        prompt_text = READER_PROMPT.format(
            caso=caso,
            tribunal=fallo.get("tribunal", "N/D"),
            fecha=fallo.get("fecha", "N/D"),
            caratula=caratula,
            materia=fallo.get("materia", "N/D"),
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

        response = await _call_with_retry(
            _get_client(),
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

        analysis = _parse_json_response(json_text)
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

    # Agent thinking: use reasoning (transparency) if available, else raw response
    analysis["agent_thinking"] = analysis.get("reasoning", analysis.get("_raw_claude_response", ""))
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


# ---------------------------------------------------------------------------
# Layer 3 — Synthesizer agent (1 Claude call)
# ---------------------------------------------------------------------------

async def _synthesize(
    caso: str,
    all_analyses: list[dict],
    synth_model: str | None = None,
    cost_tracker: "CostTracker | None" = None,
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
        response = await _call_with_retry(
            _get_client(),
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
        result = _parse_json_response(raw_synth)
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


# ---------------------------------------------------------------------------
# Orchestrator — streaming with progress
# ---------------------------------------------------------------------------

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

    # --- Log config ---
    print(f"\n[Analysis] tier={tier} reader={tier_config.reader_model} synth={tier_config.synth_model} top_k={top_k}", flush=True)

    # --- Layer 1: Search ---
    yield {"step": "search", "progress": 0, "detail": f"[{tier_config.name}] Buscando {top_k} fallos similares..."}
    results = await _search_cases(caso, fuero, top_k=top_k)
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

    # --- Layer 1.25: Enrich chunks with full document text ---
    from app.services.fulltext_store import enrich_with_fulltext
    results = enrich_with_fulltext(results)

    # --- Layer 1.5: Quality pre-filter (no LLM, pure text matching) ---
    substantive_results, auto_noise = _filter_low_quality(results)
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
    auto_inadmisibles = [_make_auto_inadmisible(f, i) for i, f in enumerate(auto_noise)]

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
        _analyze_single(caso, fallo, i, reader_model=tier_config.reader_model, cost_tracker=cost, event_queue=event_queue, cancel=cancel, transparency=transparency)
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

        # Drain all queued agent events
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
    # They are appended AFTER the reader results so the top fallos sent to the
    # synthesizer are the substantive ones, not noise.
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
    synthesis = await _synthesize(caso, synthesis_input, synth_model=tier_config.synth_model, cost_tracker=cost, cancel=cancel)

    # Build COMPLETE synthesizer thinking — no truncation, full transparency
    import json as _json
    # The COMPLETE raw response from Claude — exactly what the synthesizer thought
    synth_thinking = synthesis.get("_raw_claude_response", _json.dumps(synthesis, ensure_ascii=False, indent=2))

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
