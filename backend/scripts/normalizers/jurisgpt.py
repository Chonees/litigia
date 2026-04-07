"""JurisGPT dataset normalizer.

Handles harpomaxx/jurisgpt — clean dataset, 974 rows, labor law from Mendoza.

Fields:
- sentencia: full ruling text (up to 107k chars)
- resumen: AI-generated summary
- texto: key legal reasoning excerpt
- fallo: numeric case ID
- voces: dash-separated keywords ("DESPIDO - NULIDAD PROCESAL - DERECHO DE DEFENSA")
- sumario: numeric summary ID
- materia: almost always "DERECHO DEL TRABAJO"
"""

import hashlib
import re

from scripts.normalizers.schema import LitigiaDocument

# Map JurisGPT materia values to our normalized categories
MATERIA_MAP = {
    "DERECHO DEL TRABAJO": "laboral",
    "DERECHO CIVIL": "civil",
    "DERECHO PROCESAL": "procesal",
}


def _parse_voces(voces_str: str) -> list[str]:
    """Parse dash-separated voces into a clean list.

    Input: "DESPIDO - NULIDAD PROCESAL - DERECHO DE DEFENSA EN JUICIO"
    Output: ["DESPIDO", "NULIDAD PROCESAL", "DERECHO DE DEFENSA EN JUICIO"]
    """
    if not voces_str:
        return []
    return [v.strip() for v in voces_str.split(" - ") if v.strip()]


def _extract_tribunal_from_text(sentencia: str) -> str:
    """Try to extract tribunal name from the ruling text header."""
    # Common patterns in Argentine rulings
    patterns = [
        r"(?:SUPREMA CORTE DE JUSTICIA|S\.?C\.?J\.?)\s*[-–]\s*(.+?)(?:\n|$)",
        r"(?:CÁMARA|CAMARA)\s+(.+?)(?:\n|$)",
        r"(?:JUZGADO)\s+(.+?)(?:\n|$)",
        r"^(.+?(?:SALA|sala)\s+\w+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, sentencia[:500], re.IGNORECASE)
        if match:
            return match.group(0).strip()[:200]
    return ""


def _extract_fecha_from_text(sentencia: str) -> str:
    """Try to extract date from ruling text."""
    # "Mendoza, 15 de marzo de 2024" or "Buenos Aires, 15/03/2024"
    patterns = [
        r"\d{1,2}\s+de\s+\w+\s+de\s+\d{4}",
        r"\d{1,2}/\d{1,2}/\d{4}",
        r"\d{4}-\d{2}-\d{2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, sentencia[:1000])
        if match:
            return match.group(0).strip()
    return ""


def _generate_id(fallo_id: str, sumario_id: str) -> str:
    """Deterministic ID from JurisGPT IDs."""
    raw = f"jurisgpt:{fallo_id}:{sumario_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_jurisgpt_row(row: dict) -> LitigiaDocument | None:
    """Normalize a single JurisGPT row into a LitigiaDocument.

    Returns None if the document should be skipped.
    """
    sentencia = (row.get("sentencia") or "").strip()
    if not sentencia or len(sentencia) < 100:
        return None

    fallo_id = str(row.get("fallo") or "")
    sumario_id = str(row.get("sumario") or "")
    materia_raw = (row.get("materia") or "").strip()
    voces_raw = (row.get("voces") or "").strip()
    resumen = (row.get("resumen") or "").strip()
    texto_extracto = (row.get("texto") or "").strip()

    return LitigiaDocument(
        id=_generate_id(fallo_id, sumario_id),
        source="jurisgpt",
        source_id=fallo_id,
        texto=sentencia,
        sumario=resumen or texto_extracto,
        caratula="",  # not available in JurisGPT
        tipo_documento="fallo",
        tipo_fallo="sentencia",
        tribunal=_extract_tribunal_from_text(sentencia),
        materia=MATERIA_MAP.get(materia_raw, materia_raw.lower()),
        voces=_parse_voces(voces_raw),
        fecha=_extract_fecha_from_text(sentencia),
        jurisdiccion="Mendoza",  # all JurisGPT data is from Mendoza
        provincia="Mendoza",
    )
