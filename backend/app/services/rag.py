import anthropic

from app.core.config import settings
from app.models.schemas import FalloResult, JurisprudenciaQuery, JurisprudenciaResponse
from app.services.embeddings import get_single_embedding
from app.services.vector_store import search_similar

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


QUERY_EXPANSION_PROMPT = """Sos un experto en derecho argentino. Dado el siguiente caso, extraé los conceptos jurídicos clave para buscar jurisprudencia relevante.

Caso: {descripcion}
{filtros}

Devolvé SOLO una lista JSON de 3-5 términos de búsqueda jurídica en español, sin explicación.
Ejemplo: ["responsabilidad civil extracontractual", "daño moral accidente de tránsito", "culpa concurrente"]"""

RERANK_PROMPT = """Sos un abogado argentino experto. Evaluá si el siguiente fallo es RELEVANTE para el caso del usuario.

CASO DEL USUARIO:
{caso}

FALLO ENCONTRADO:
Tribunal: {tribunal}
Fecha: {fecha}
Carátula: {caratula}
Texto: {texto}

Respondé con un JSON:
{{
  "relevante": true/false,
  "score": 0.0-1.0,
  "resumen": "resumen breve del fallo",
  "argumento_clave": "el argumento jurídico principal aplicable al caso",
  "cita_textual": "la frase más relevante del fallo (textual)"
}}

SOLO el JSON, sin explicación."""


async def expand_query(query: JurisprudenciaQuery) -> list[str]:
    """Use Claude to extract legal concepts from the case description."""
    filtros = ""
    if query.jurisdiccion:
        filtros += f"\nJurisdicción: {query.jurisdiccion}"
    if query.fuero:
        filtros += f"\nFuero: {query.fuero}"
    if query.materia:
        filtros += f"\nMateria: {query.materia}"

    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": QUERY_EXPANSION_PROMPT.format(
                    descripcion=query.descripcion_caso, filtros=filtros
                ),
            }
        ],
    )

    import json

    try:
        return json.loads(response.content[0].text)
    except (json.JSONDecodeError, IndexError):
        return [query.descripcion_caso]


async def rerank_result(caso: str, fallo: dict) -> dict | None:
    """Use Claude to evaluate if a result is truly relevant."""
    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": RERANK_PROMPT.format(
                    caso=caso,
                    tribunal=fallo.get("tribunal", "N/D"),
                    fecha=fallo.get("fecha", "N/D"),
                    caratula=fallo.get("caratula", "N/D"),
                    texto=fallo.get("texto", "")[:2000],
                ),
            }
        ],
    )

    import json

    try:
        result = json.loads(response.content[0].text)
        if result.get("relevante"):
            return result
    except (json.JSONDecodeError, IndexError):
        pass
    return None


async def search_jurisprudencia(query: JurisprudenciaQuery) -> JurisprudenciaResponse:
    """Full RAG pipeline: expand query -> vector search -> rerank."""
    # Step 1: Expand query into legal concepts
    expanded_terms = await expand_query(query)

    # Step 2: Get embeddings for each expanded term and search
    all_results: list[dict] = []
    seen_ids: set[str] = set()

    for term in expanded_terms:
        embedding = await get_single_embedding(term)
        filters = {}
        if query.jurisdiccion:
            filters["jurisdiccion"] = query.jurisdiccion
        if query.fuero:
            filters["fuero"] = query.fuero

        results = await search_similar(
            query_embedding=embedding,
            top_k=query.top_k * 2,  # fetch more, rerank will filter
            filters=filters if filters else None,
        )

        for r in results:
            rid = r.get("source_id", r.get("id", ""))
            if rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append(r)

    # Step 3: Rerank with Claude
    fallos: list[FalloResult] = []
    for result in all_results[: query.top_k * 3]:  # cap reranking calls
        reranked = await rerank_result(query.descripcion_caso, result)
        if reranked:
            fallos.append(
                FalloResult(
                    tribunal=result.get("tribunal", "N/D"),
                    fecha=result.get("fecha", "N/D"),
                    caratula=result.get("caratula", "N/D"),
                    resumen=reranked.get("resumen", ""),
                    argumento_clave=reranked.get("argumento_clave", ""),
                    cita_textual=reranked.get("cita_textual", ""),
                    score=reranked.get("score", 0.0),
                    source_id=result.get("source_id", result.get("id", "")),
                )
            )

    # Sort by score and limit
    fallos.sort(key=lambda f: f.score, reverse=True)
    fallos = fallos[: query.top_k]

    return JurisprudenciaResponse(
        query_expandida=expanded_terms,
        fallos=fallos,
        total_encontrados=len(fallos),
    )
