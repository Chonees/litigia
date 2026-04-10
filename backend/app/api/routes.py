import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

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
from app.services.analysis import run_predictive_analysis, run_predictive_analysis_stream
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
    """Análisis predictivo completo — 100 fallos, agentes paralelos."""
    return await run_predictive_analysis(request.descripcion_caso, request.fuero)


@router.post("/analisis/stream")
async def analisis_predictivo_stream(request: AnalisisPredictivo, req: Request):
    """Análisis predictivo con progreso vía SSE.
    Sets cancel event when client disconnects — stops all API calls."""
    import asyncio
    cancel = asyncio.Event()

    async def event_generator():
        async for event in run_predictive_analysis_stream(
            request.descripcion_caso, request.fuero, tier=request.tier, top_k=request.top_k,
            transparency=request.transparency, cancel=cancel,
        ):
            # Check disconnect EVERY event — set cancel to stop ALL tasks
            if await req.is_disconnected():
                print("[Analysis] Client disconnected — CANCELLING all tasks", flush=True)
                cancel.set()
                return
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/analisis/tiers")
async def analisis_tiers():
    """Available analysis tiers with pricing info."""
    from app.services.tiers import TIERS
    return {
        name: {
            "name": t.name,
            "description": t.description,
            "reader_model": t.reader_model,
            "synth_model": t.synth_model,
        }
        for name, t in TIERS.items()
    }


@router.get("/scraper/status")
async def scraper_status():
    """Live scraper progress — read from progress JSON."""
    from app.core.config import settings
    progress_file = settings.data_logs / "csjn_progress.json"
    if progress_file.exists():
        return json.loads(progress_file.read_text())
    return {"status": "idle", "scraped": 0}


@router.get("/health")
async def health():
    return {"status": "ok", "service": "LITIGIA"}


# --- Temporary data upload endpoint (remove after initial data load) ---

@router.post("/admin/upload-data")
async def upload_data(request: Request):
    """Receive a tar.gz file and extract to /data using streaming (low memory)."""
    import tarfile
    import tempfile
    import os
    from app.core.config import settings

    secret = request.headers.get("X-Upload-Secret", "")
    if secret != "litigia-upload-2026":
        return {"error": "unauthorized"}, 401

    # Stream to temp file instead of loading all in memory
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz")
    size = 0
    async for chunk in request.stream():
        tmp.write(chunk)
        size += len(chunk)
    tmp.close()

    size_mb = size / (1024 * 1024)
    print(f"[Upload] Received {size_mb:.1f}MB, extracting...", flush=True)

    tar = tarfile.open(tmp.name, mode="r:gz")
    tar.extractall(path=str(settings.data_root))
    tar.close()
    os.unlink(tmp.name)

    files = []
    for root, dirs, filenames in os.walk(str(settings.data_root)):
        for f in filenames:
            full = os.path.join(root, f)
            files.append({"path": full, "size_mb": round(os.path.getsize(full) / (1024*1024), 1)})

    print(f"[Upload] Extracted {len(files)} files to {settings.data_root}", flush=True)
    return {"status": "ok", "files": files[:50], "total_files": len(files)}


@router.post("/admin/upload-file")
async def upload_file(request: Request):
    """Stream a single file to a specific path under /data. Low memory."""
    import os
    from app.core.config import settings

    secret = request.headers.get("X-Upload-Secret", "")
    if secret != "litigia-upload-2026":
        return {"error": "unauthorized"}, 401

    # Target path from header
    target = request.headers.get("X-Target-Path", "")
    if not target:
        return {"error": "X-Target-Path header required"}, 400

    dest = settings.data_root / target
    dest.parent.mkdir(parents=True, exist_ok=True)

    append = request.headers.get("X-Append", "").lower() == "true"
    mode = "ab" if append else "wb"

    size = 0
    with open(dest, mode) as f:
        async for chunk in request.stream():
            f.write(chunk)
            size += len(chunk)

    import os
    total_size = os.path.getsize(dest) / (1024 * 1024)
    size_mb = size / (1024 * 1024)
    print(f"[Upload] {'Appended' if append else 'Saved'} {target} (+{size_mb:.1f}MB, total: {total_size:.1f}MB)", flush=True)
    return {"status": "ok", "path": str(dest), "chunk_mb": round(size_mb, 1), "total_mb": round(total_size, 1)}
