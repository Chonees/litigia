from pydantic import BaseModel


# --- Jurisprudencia ---


class JurisprudenciaQuery(BaseModel):
    """Input para búsqueda de jurisprudencia."""

    descripcion_caso: str
    jurisdiccion: str | None = None
    fuero: str | None = None
    materia: str | None = None
    top_k: int = 5


class FalloResult(BaseModel):
    """Un fallo encontrado por el RAG."""

    tribunal: str
    fecha: str
    caratula: str
    resumen: str
    argumento_clave: str
    cita_textual: str
    score: float
    source_id: str


class JurisprudenciaResponse(BaseModel):
    """Respuesta de búsqueda de jurisprudencia."""

    query_expandida: list[str]
    fallos: list[FalloResult]
    total_encontrados: int


# --- Generación de escritos ---


class EscritoRequest(BaseModel):
    """Input para generar un escrito judicial."""

    tipo: str  # contestacion_demanda, oficio, cedula, etc.
    fuero: str  # civil, laboral, penal, comercial
    tema: str  # descripción del tema
    posicion: str  # actor, demandado, tercero
    jurisdiccion: str  # CABA, PBA, etc.
    datos_caso: str  # descripción libre del caso
    datos_partes: dict | None = None  # nombres, CUIT, domicilios


class EscritoResponse(BaseModel):
    """Respuesta con el escrito generado."""

    contenido_texto: str
    jurisprudencia_citada: list[FalloResult]
    archivo_docx_base64: str | None = None


# --- Resumen de fallo ---


class ResumenFalloRequest(BaseModel):
    """Input para resumir un fallo."""

    texto_fallo: str


class ResumenFalloResponse(BaseModel):
    """Resumen estructurado de un fallo."""

    hechos: str
    cuestion_juridica: str
    argumentos_actor: str
    argumentos_demandado: str
    resolucion: str
    doctrina_aplicada: str
    articulos_citados: list[str]


# --- Análisis predictivo ---


class AnalisisPredictivo(BaseModel):
    """Input para análisis de chances."""

    descripcion_caso: str
    fuero: str | None = None


class AnalisisResponse(BaseModel):
    """Resultado del análisis predictivo."""

    fallos_analizados: int
    porcentaje_favorable: float
    argumento_mas_fuerte: str
    riesgos: list[str]
    estimacion: str | None = None
    fallos_relevantes: list[FalloResult]


# --- Oficio ---


class OficioRequest(BaseModel):
    """Input para generar un oficio."""

    destinatario: str  # AFIP, banco, registro, etc.
    motivo: str
    datos_expediente: str  # Nro expte, juzgado, secretaría
    datos_requeridos: str  # qué se pide
    datos_partes: dict | None = None
