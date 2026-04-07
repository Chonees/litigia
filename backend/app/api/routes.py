from fastapi import APIRouter

from app.models.schemas import (
    AnalisisPredictivo,
    AnalisisResponse,
    EscritoRequest,
    EscritoResponse,
    FalloResult,
    JurisprudenciaQuery,
    JurisprudenciaResponse,
    OficioRequest,
    ResumenFalloRequest,
    ResumenFalloResponse,
)
from app.services.document_generator import generate_escrito, generate_oficio, resumir_fallo
from app.services.rag import search_jurisprudencia

router = APIRouter(prefix="/api/v1", tags=["litigia"])


@router.post("/jurisprudencia", response_model=JurisprudenciaResponse)
async def buscar_jurisprudencia(query: JurisprudenciaQuery):
    """Buscar jurisprudencia relevante para un caso."""
    return await search_jurisprudencia(query)


@router.post("/escrito", response_model=EscritoResponse)
async def generar_escrito(request: EscritoRequest):
    """Generar un escrito judicial con jurisprudencia real."""
    return await generate_escrito(request)


@router.post("/resumen", response_model=ResumenFalloResponse)
async def resumir(request: ResumenFalloRequest):
    """Resumir un fallo judicial."""
    return await resumir_fallo(request)


@router.post("/oficio")
async def generar_oficio(request: OficioRequest):
    """Generar un oficio judicial."""
    contenido = await generate_oficio(request)
    return {"contenido": contenido}


@router.post("/analisis", response_model=AnalisisResponse)
async def analisis_predictivo(request: AnalisisPredictivo):
    """Análisis predictivo de chances en un caso."""
    # Search for similar cases
    query = JurisprudenciaQuery(
        descripcion_caso=request.descripcion_caso,
        fuero=request.fuero,
        top_k=15,
    )
    result = await search_jurisprudencia(query)

    # For MVP, return the jurisprudencia found
    # TODO: Add statistical analysis of outcomes
    total = len(result.fallos)
    return AnalisisResponse(
        fallos_analizados=total,
        porcentaje_favorable=0.0,  # needs outcome classification
        argumento_mas_fuerte=result.fallos[0].argumento_clave if result.fallos else "Sin datos",
        riesgos=["Análisis predictivo en desarrollo - basado en jurisprudencia encontrada"],
        estimacion=None,
        fallos_relevantes=result.fallos,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "LITIGIA"}
