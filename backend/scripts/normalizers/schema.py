"""Unified document schema for LITIGIA.

Every dataset normalizer MUST output documents conforming to this schema.
This is the contract between raw data and the vector store.
"""

from dataclasses import dataclass, field, asdict
from typing import Self


@dataclass
class LitigiaDocument:
    """Normalized legal document — the single source of truth for the pipeline."""

    # Identity
    id: str                          # deterministic hash of source + source_id
    source: str                      # "saij" | "jurisgpt"
    source_id: str                   # original ID in the source dataset

    # Core content
    texto: str                       # full text of the ruling/document
    sumario: str = ""                # summary (SAIJ) or AI-generated (JurisGPT)

    # Metadata — case identification
    caratula: str = ""               # "García c/ Pérez s/ daños y perjuicios"
    tipo_documento: str = ""         # "fallo", "legislacion", "doctrina"
    tipo_fallo: str = ""             # "sentencia", "interlocutoria", "plenario"

    # Metadata — court
    tribunal: str = ""               # "Cámara Nacional de Apelaciones en lo Civil, Sala A"
    tipo_tribunal: str = ""          # "camara", "juzgado", "corte_suprema"
    sala: str = ""                   # "Sala A", "Sala II"
    magistrados: list[str] = field(default_factory=list)

    # Metadata — classification
    materia: str = ""                # "civil", "laboral", "penal"
    voces: list[str] = field(default_factory=list)  # ["DESPIDO", "INDEMNIZACIÓN"]
    descriptores: list[str] = field(default_factory=list)

    # Metadata — location & time
    fecha: str = ""                  # ISO format preferred: "2024-03-15"
    jurisdiccion: str = ""           # "CABA", "Buenos Aires", "Mendoza"
    provincia: str = ""              # province name
    localidad: str = ""

    # Metadata — parties (anonymizable)
    actor: str = ""
    demandado: str = ""
    sobre: str = ""                  # object of the case

    # Metadata — legal references
    referencias_normativas: list[str] = field(default_factory=list)  # ["art. 245 LCT"]
    citas_jurisprudenciales: list[str] = field(default_factory=list)

    # Computed fields (filled during ingestion)
    texto_embedding: str = ""        # text sent to embedding model
    chunk_index: int = 0             # 0 = full doc, 1+ = chunk number
    total_chunks: int = 1

    def to_dict(self) -> dict:
        """Serialize for JSONL storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Deserialize from JSONL, ignoring unknown fields."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def embedding_text(self) -> str:
        """Build the text we send to the embedding model.

        Combines metadata + content for richer semantic search.
        """
        parts = []
        if self.caratula:
            parts.append(f"Carátula: {self.caratula}")
        if self.materia:
            parts.append(f"Materia: {self.materia}")
        if self.voces:
            parts.append(f"Voces: {', '.join(self.voces[:10])}")
        if self.tribunal:
            parts.append(f"Tribunal: {self.tribunal}")
        if self.sobre:
            parts.append(f"Sobre: {self.sobre}")

        # Content: prefer sumario for embedding (more semantic), fallback to texto
        content = self.sumario if self.sumario and len(self.sumario) > 50 else self.texto
        parts.append(content[:3000])

        return " | ".join(parts)
