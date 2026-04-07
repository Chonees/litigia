"""SAIJ dataset normalizer.

Handles the messy schema from marianbasti/jurisprudencia-Argentina-SAIJ:
- `jurisdiccion` is sometimes a dict, sometimes a string, sometimes null
- `descriptores` is sometimes a list, sometimes a dict, sometimes null
- `referencias-normativas` is a dict with nested structure
- `texto-completo` sometimes exists alongside `texto`
- Field names use hyphens, not underscores
- ~48 fields, many nullable or inconsistent across rows

We stream the dataset to handle 720GB+ without loading into memory.
"""

import hashlib
import re

from scripts.normalizers.schema import LitigiaDocument


def _safe_str(value: object) -> str:
    """Extract a string from whatever SAIJ gives us."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        # jurisdiccion comes as {"nombre": "CABA", ...} or similar
        return value.get("nombre", "") or value.get("descripcion", "") or str(value)
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip()


def _safe_list(value: object) -> list[str]:
    """Extract a list of strings from whatever SAIJ gives us."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, dict):
        # Sometimes descriptores = {"descriptor": ["DESPIDO", "DAÑOS"]}
        for key in ("descriptor", "descriptores", "voz", "voces", "items"):
            if key in value and isinstance(value[key], list):
                return [str(v).strip() for v in value[key] if v]
        return [str(v) for v in value.values() if v]
    if isinstance(value, str):
        # "DESPIDO - DAÑOS - PRUEBA" or "DESPIDO, DAÑOS, PRUEBA"
        if " - " in value:
            return [v.strip() for v in value.split(" - ") if v.strip()]
        if "," in value:
            return [v.strip() for v in value.split(",") if v.strip()]
        return [value.strip()] if value.strip() else []
    return []


def _extract_referencias(value: object) -> list[str]:
    """Extract legal references from the nested SAIJ structure."""
    if value is None:
        return []
    if isinstance(value, list):
        return [_safe_str(v) for v in value if v]
    if isinstance(value, dict):
        refs = []
        # Try common nested patterns
        for key in ("referencia", "referencias", "norma", "normas", "items"):
            if key in value:
                inner = value[key]
                if isinstance(inner, list):
                    for item in inner:
                        if isinstance(item, dict):
                            desc = item.get("descripcion", "") or item.get("texto", "")
                            if desc:
                                refs.append(str(desc).strip())
                        elif item:
                            refs.append(str(item).strip())
                elif inner:
                    refs.append(str(inner).strip())
        if not refs:
            # Fallback: just grab all string values
            refs = [str(v).strip() for v in value.values() if isinstance(v, str) and v.strip()]
        return refs
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_magistrados(value: object) -> list[str]:
    """Parse magistrados field — sometimes a string, sometimes a list."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, str):
        # "Dr. García, Dr. López, Dr. Martínez"
        return [v.strip() for v in re.split(r"[,;/]", value) if v.strip()]
    return []


def _detect_materia(row: dict) -> str:
    """Try to extract materia/fuero from multiple fields."""
    materia = _safe_str(row.get("materia"))
    if materia:
        return materia.lower()

    # Infer from tipo-tribunal or descriptores
    descriptores_str = _safe_str(row.get("descriptores")).lower()
    for keyword, mat in [
        ("laboral", "laboral"),
        ("trabajo", "laboral"),
        ("civil", "civil"),
        ("penal", "penal"),
        ("comercial", "comercial"),
        ("familia", "familia"),
        ("contencioso", "contencioso administrativo"),
    ]:
        if keyword in descriptores_str:
            return mat

    return ""


def _generate_id(source_id: str, texto: str) -> str:
    """Deterministic ID from source + content."""
    raw = f"saij:{source_id or texto[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_saij_row(row: dict) -> LitigiaDocument | None:
    """Normalize a single SAIJ row into a LitigiaDocument.

    Returns None if the document should be skipped (too short, no content).
    """
    # Get the best text available
    texto = _safe_str(row.get("texto-completo")) or _safe_str(row.get("texto"))
    if not texto or len(texto) < 100:
        return None

    source_id = _safe_str(row.get("id-infojus")) or _safe_str(row.get("guid")) or ""

    return LitigiaDocument(
        id=_generate_id(source_id, texto),
        source="saij",
        source_id=source_id,
        texto=texto,
        sumario=_safe_str(row.get("sumario")),
        caratula=_safe_str(row.get("caratula")),
        tipo_documento=_safe_str(row.get("tipo-fallo")).lower() or "fallo",
        tipo_fallo=_safe_str(row.get("tipo-fallo")),
        tribunal=_safe_str(row.get("tribunal")),
        tipo_tribunal=_safe_str(row.get("tipo-tribunal")),
        sala=_safe_str(row.get("sala")),
        magistrados=_extract_magistrados(row.get("magistrados")),
        materia=_detect_materia(row),
        voces=_safe_list(row.get("descriptores")),
        descriptores=_safe_list(row.get("descriptores")),
        fecha=_safe_str(row.get("fecha")),
        jurisdiccion=_safe_str(row.get("jurisdiccion")),
        provincia=_safe_str(row.get("provincia")),
        localidad=_safe_str(row.get("localidad")),
        actor=_safe_str(row.get("actor")),
        demandado=_safe_str(row.get("demandado")),
        sobre=_safe_str(row.get("sobre")),
        referencias_normativas=_extract_referencias(row.get("referencias-normativas")),
    )
