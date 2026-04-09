"""RAG pipeline for jurisprudencia search.

Optimized for low API rate limits — uses local embeddings for search,
Claude only for final summary (1 API call per search).
"""

import json
import re

import anthropic


def _clean_saij_markup(text: str) -> str:
    """Remove SAIJ markup tags like [[p]], [[/p]], [[r uuid:...]], etc."""
    text = re.sub(r"\[\[/?[a-z]+(?:\s[^\]]*?)?\]\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

from app.core.config import settings
from app.models.schemas import FalloResult, JurisprudenciaQuery, JurisprudenciaResponse
from app.services.embeddings import get_single_embedding
from app.services.vector_store import search_similar


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


SUMMARIZE_RESULTS_PROMPT = """Sos un abogado argentino experto. Analicé los siguientes fallos encontrados para el caso del usuario.

CASO DEL USUARIO:
{caso}

FALLOS ENCONTRADOS:
{fallos_text}

Para CADA fallo, respondé con un JSON array. Cada elemento debe tener:
- "index": número del fallo (empezando en 0)
- "relevante": true/false
- "resumen": resumen breve del fallo (1-2 oraciones)
- "argumento_clave": el argumento jurídico principal aplicable al caso
- "cita_textual": la frase más relevante del texto (textual, entre comillas)

Respondé SOLO con el JSON array, sin explicación:"""


async def search_jurisprudencia(query: JurisprudenciaQuery) -> JurisprudenciaResponse:
    """Search pipeline: embed query -> vector search -> Claude summarizes results.

    Only 1 Claude API call per search (respects 5 req/min rate limit).
    """
    # Step 1: Embed the query directly (local, no API call)
    search_text = query.descripcion_caso
    if query.fuero:
        search_text += f" fuero {query.fuero}"
    if query.materia:
        search_text += f" materia {query.materia}"

    embedding = await get_single_embedding(search_text)

    # Step 2: Vector search in ChromaDB (local, no API call)
    results = await search_similar(
        query_embedding=embedding,
        top_k=query.top_k * 2,  # fetch extra, Claude will filter
        jurisdiccion=query.jurisdiccion,
        fuero=query.fuero,
        materia=query.materia,
    )

    # Fallback: if strict filters return 0 results, search without filters
    if not results and (query.jurisdiccion or query.fuero or query.materia):
        results = await search_similar(
            query_embedding=embedding,
            top_k=query.top_k * 2,
        )

    if not results:
        return JurisprudenciaResponse(
            query_expandida=[query.descripcion_caso],
            fallos=[],
            total_encontrados=0,
        )

    # Clean SAIJ markup from all results
    for r in results:
        for key in ("texto", "sumario", "caratula"):
            if r.get(key):
                r[key] = _clean_saij_markup(r[key])

    # Step 3: ONE Claude call to summarize and rank all results
    fallos_text = ""
    for i, r in enumerate(results):
        texto = r.get("texto", "")[:1500]
        fallos_text += (
            f"\n--- Fallo {i} ---\n"
            f"Tribunal: {r.get('tribunal', 'N/D')}\n"
            f"Fecha: {r.get('fecha', 'N/D')}\n"
            f"Carátula: {r.get('caratula', 'N/D')}\n"
            f"Materia: {r.get('materia', 'N/D')}\n"
            f"Texto: {texto}\n"
        )

    try:
        response = await _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARIZE_RESULTS_PROMPT.format(
                        caso=query.descripcion_caso,
                        fallos_text=fallos_text,
                    ),
                }
            ],
        )

        analyses = json.loads(response.content[0].text)
    except Exception:
        # If Claude fails (rate limit, etc), return raw results without analysis
        analyses = [
            {
                "index": i,
                "relevante": True,
                "resumen": r.get("sumario", "")[:200] or r.get("texto", "")[:200],
                "argumento_clave": r.get("caratula", ""),
                "cita_textual": "",
            }
            for i, r in enumerate(results)
        ]

    # Step 4: Build response
    fallos: list[FalloResult] = []
    for analysis in analyses:
        if not analysis.get("relevante", True):
            continue

        idx = analysis.get("index", 0)
        if idx >= len(results):
            continue

        r = results[idx]
        fallos.append(
            FalloResult(
                tribunal=r.get("tribunal", "N/D"),
                fecha=r.get("fecha", "N/D"),
                caratula=r.get("caratula", "N/D"),
                resumen=analysis.get("resumen", ""),
                argumento_clave=analysis.get("argumento_clave", ""),
                cita_textual=analysis.get("cita_textual", ""),
                score=r.get("score", 0.0),
                source_id=r.get("source_id", r.get("id", "")),
                texto_completo=r.get("texto", ""),
                materia=r.get("materia", ""),
                fuente=r.get("source", ""),
            )
        )

    # Limit to requested count
    fallos = fallos[: query.top_k]

    return JurisprudenciaResponse(
        query_expandida=[query.descripcion_caso],
        fallos=fallos,
        total_encontrados=len(fallos),
    )
