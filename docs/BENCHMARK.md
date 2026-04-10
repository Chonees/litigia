# LITIGIA — Benchmark de Precisión de Búsqueda

## Fecha: 9 de Abril 2026
## Base: 471,511 vectores (ChromaDB) + 664,835 documentos indexados (FTS5)
## Pipeline: Vector search + FTS5 keyword + RRF fusion + Cross-encoder reranker (bge-reranker-v2-m3)

---

## Resultados: 50 queries de firma litigante de alto nivel

| # | Query | Precisión | Rating |
|---|-------|-----------|--------|
| 1 | Despido embarazada art. 178 LCT | 100% | EXCELENTE |
| 2 | Despido delegado gremial tutela sindical 23.551 | 90% | EXCELENTE |
| 3 | Tercerización fraudulenta grupo económico art. 31 | 0% | MALA |
| 4 | Accidente laboral ART rechaza siniestro 24.557 | 100% | EXCELENTE |
| 5 | Inconstitucionalidad art. 39 ley 24.557 | 70% | BUENA |
| 6 | Despido licencia enfermedad inculpable art. 213 | 70% | BUENA |
| 7 | Diferencias salariales categorización convenio | 60% | BUENA |
| 8 | Mobbing acoso laboral daño moral | 80% | EXCELENTE |
| 9 | Horas extras jornada art. 201 LCT nocturno | 60% | BUENA |
| 10 | Despido por matrimonio art. 182 LCT | 70% | BUENA |
| 11 | Trabajo no registrado multas ley 24.013 | 90% | EXCELENTE |
| 12 | Accidente in itinere desvío trayecto | 100% | EXCELENTE |
| 13 | Despido discriminatorio HIV SIDA 23.798 | 50% | ACEPTABLE |
| 14 | Contrato eventual fraude art. 99 LCT | 30% | MALA |
| 15 | Viajante de comercio comisiones 14.546 | 100% | EXCELENTE |
| 16 | Mala praxis médica consentimiento informado | 90% | EXCELENTE |
| 17 | Daños accidente tránsito art. 1757 CCyCN | 100% | EXCELENTE |
| 18 | Ejecución hipotecaria subasta precio vil | 70% | BUENA |
| 19 | Daño ambiental colectivo art. 41 ley 25.675 | 0% | MALA |
| 20 | Responsabilidad Estado falta de servicio | 100% | EXCELENTE |
| 21 | Prescripción adquisitiva usucapión | 80% | EXCELENTE |
| 22 | Alimentos cuota alimentaria interés superior niño | 100% | EXCELENTE |
| 23 | Divorcio bienes gananciales sociedad conyugal | 100% | EXCELENTE |
| 24 | Daños punitivos 52 bis ley 24.240 consumidor | 40% | ACEPTABLE |
| 25 | Ruidos molestos inmisiones art. 1973 CCyCN | 60% | BUENA |
| 26 | Responsabilidad directores SA art. 274 ley 19.550 | 80% | EXCELENTE |
| 27 | Medida cautelar asamblea accionistas | 70% | BUENA |
| 28 | Concurso preventivo cramdown salvataje | 90% | EXCELENTE |
| 29 | Quiebra extensión responsabilidad art. 161 ley 24.522 | 90% | EXCELENTE |
| 30 | Contrato franquicia resolución abusiva | 0% | MALA |
| 31 | Recurso extraordinario CSJN arbitrariedad ley 48 | 80% | EXCELENTE |
| 32 | Amparo art. 43 CN autoridad pública | 20% | MALA |
| 33 | Competencia originaria CSJN art. 117 CN | 100% | EXCELENTE |
| 34 | Habeas corpus privación libertad | 100% | EXCELENTE |
| 35 | Declarativa inconstitucionalidad ley impositiva | 100% | EXCELENTE |
| 36 | Empleo público cesantía estabilidad reincorporación | 90% | EXCELENTE |
| 37 | Expropiación irregular indemnización art. 17 CN | 0% | MALA |
| 38 | Evasión fiscal ley 24.769 penal tributario | 90% | EXCELENTE |
| 39 | Lavado de activos ley 25.246 UIF | 50% | ACEPTABLE |
| 40 | Estafa procesal falsedad documental art. 172 | 60% | BUENA |
| 41 | Seguro de vida reticencia ley 17.418 | 30% | MALA |
| 42 | Seguro automotor franquicia oponibilidad tercero | 20% | MALA |
| 43 | Marca registrada confusión marcaria ley 22.362 | 60% | BUENA |
| 44 | Derecho de autor plagio ley 11.723 | 90% | EXCELENTE |
| 45 | Resolución contrato incumplimiento art. 1083 CCyCN | 70% | BUENA |
| 46 | Distribución comercial rescisión intempestiva | 90% | EXCELENTE |
| 47 | Locación desalojo falta de pago ley 27.551 | 90% | EXCELENTE |
| 48 | Fideicomiso inmobiliario incumplimiento escriturar | 20% | MALA |
| 49 | Determinación de oficio AFIP tribunal fiscal | 80% | EXCELENTE |
| 50 | Repetición pago indebido tributo inconstitucional | 20% | MALA |

---

## Resumen

| Rating | Cantidad | Porcentaje |
|--------|----------|------------|
| EXCELENTE (80%+) | 26/50 | 52% |
| BUENA (60-79%) | 11/50 | 22% |
| ACEPTABLE (40-59%) | 3/50 | 6% |
| MALA (<40%) | 10/50 | 20% |
| **PROMEDIO** | | **68%** |

**74% de las queries son BUENAS o EXCELENTES** — usable para producción en la mayoría de áreas de práctica.

---

## Queries que fallan y POR QUÉ

### 0% — No encuentra NADA relevante

**Tercerización fraudulenta (0%)**
- Hay 5,116 fallos sobre el tema en la base cruda
- El vector search no los captura porque el embedding diluye "tercerización" en "derecho laboral genérico"
- FTS5 los encuentra por keyword pero el reranker los puntúa bajo porque el texto de los documentos no tiene suficiente overlap con la query completa
- La query combina 3 conceptos (tercerización + grupo económico + art. 31) y pocos fallos hablan de los 3 juntos

**Daño ambiental colectivo (0%)**
- Tema muy específico con poca jurisprudencia en SAIJ/CSJN
- Los fallos que existen usan terminología diferente ("contaminación", "medio ambiente") vs la query ("remediación", "daño ambiental")
- FTS5 no pudo traer resultados porque los IDs tenían duplicados en ChromaDB

**Franquicia comercial (0%)**
- Tema nicho con muy pocos fallos en la base
- "Franquicia" aparece más en contexto de seguros (franquicia de seguro automotor) que en contratos de franquicia comercial
- El reranker confunde ambos significados

**Expropiación irregular (0%)**
- Tema constitucional/administrativo con jurisprudencia histórica (pre-2015)
- CSJN scrapeada solo desde 2015 — los fallos clásicos de expropiación son anteriores
- Necesita más datos históricos

### 20-30% — Encuentra algo pero la mayoría es ruido

**Amparo (20%)** — Query demasiado genérica, "amparo" matchea con muchos fallos que no son sobre amparo contra el Estado
**Seguro automotor (20%)** — El reranker no distingue bien entre franquicia de seguro y franquicia comercial
**Seguro de vida reticencia (30%)** — Tema muy técnico de derecho de seguros, pocos fallos en la base
**Fideicomiso inmobiliario (20%)** — Tema inmobiliario-comercial nicho
**Repetición de tributo (20%)** — Los keywords son demasiado genéricos ("pago", "prescripción")
**Contrato eventual (30%)** — "Eventual" y "permanente" aparecen en todo tipo de fallos laborales

---

## Cómo mejorar REALMENTE — Hoja de ruta

### Mejora 1: Re-ingestión con prefijos E5 (impacto estimado: +10-15%)

**El problema:** Los 471K documentos en ChromaDB fueron embedidos SIN el prefijo `"passage: "` que el modelo multilingual-e5-base requiere. La query SÍ usa `"query: "`. Esta asimetría reduce la calidad del cosine similarity un 15-20%.

**La solución:** Re-embedar todos los documentos con `"passage: "` antes del texto. Tarda ~6 horas en RTX 4090.

**Cómo hacerlo:**
1. Modificar `scripts/ingest_embeddings.py` → en `_embed_and_upsert()` agregar `prefix="passage: "` a la llamada de `get_embeddings()`
2. Borrar la colección de ChromaDB: `chromadb.PersistentClient(path).delete_collection("jurisprudencia")`
3. Re-correr: `python -m scripts.ingest_embeddings`
4. Re-construir FTS: `python -m scripts.build_fts_index`

**Impacto:** Los scores de cosine van a tener un rango más amplio (0.5-0.95 vs el actual 0.79-0.90), lo que permite filtrar mejor y el reranker trabaja sobre candidatos más diversos.

### Mejora 2: Más datos (impacto estimado: +15-20% en queries que hoy fallan)

**Queries que fallan por falta de datos:**
- Expropiación → fallos clásicos son pre-2015, CSJN solo tiene desde 2015
- Daño ambiental → pocos fallos en SAIJ, necesita fuentes especializadas
- Franquicia comercial → nicho, necesita scraping de cámaras comerciales

**Cómo hacerlo:**
1. Correr scraper CSJN sin límite: `python -m scripts.scrapers.csjn` (sin --limit). Baja TODO desde 1863.
2. Agregar fuentes: InfoJus, CIJ (Centro de Información Judicial), bases provinciales
3. Scraping dirigido: buscar en CSJN específicamente "expropiación", "daño ambiental", "franquicia"

### Mejora 3: Reranker fine-tuneado en legal argentino (impacto estimado: +10-15%)

**El problema:** `bge-reranker-v2-m3` es genérico — no entiende que "art. 31 LCT" y "solidaridad del grupo" son conceptos relacionados en derecho argentino.

**Cómo hacerlo:**
1. Armar un dataset de ~1000 pares: (query legal, fallo relevante, score 0-1)
2. Fine-tunear el cross-encoder con `sentence-transformers` y el trainer de CrossEncoder
3. Los pares se pueden generar semi-automáticamente: tomar los resultados del benchmark y que un abogado marque cuáles son relevantes

**Costo:** ~4 horas de trabajo de un abogado + ~2 horas de entrenamiento en GPU

### Mejora 4: Upgrade a multilingual-e5-large-instruct (impacto estimado: +10%)

**El problema:** e5-base tiene 768 dimensiones. e5-large-instruct tiene 1024 y acepta instrucciones como: "Retrieve Argentine court rulings relevant to: {query}"

**Cómo hacerlo:**
1. Cambiar `MODEL_NAME` en `embeddings.py`
2. Re-ingestar todo (las dimensiones cambian, no es compatible con la colección actual)
3. Tarda ~8-10 horas en RTX 4090 (modelo más grande)

**Tradeoff:** Más precisión pero más lento y más memoria. Solo vale la pena si las mejoras 1-3 no alcanzan.

### Mejora 5: Query expansion (impacto estimado: +5-10% en queries genéricas)

**El problema:** "Amparo art. 43" es demasiado genérico y matchea con muchos fallos que no son sobre amparo contra el Estado.

**Cómo hacerlo:**
1. Antes de buscar, usar un LLM (Haiku, $0.001) para expandir la query: "Amparo art. 43 CN" → "acción de amparo contra acto de autoridad pública administrativa, plazo 15 días, legitimación activa colectiva, vía sumarísima"
2. Buscar con la query expandida — más keywords para FTS5, más contexto para el vector

---

## Configuración del pipeline al momento del benchmark

```
Embedding: intfloat/multilingual-e5-base (768 dim) con prefix "query: " para queries
Vector DB: ChromaDB 1.5.6 (471,511 docs, cosine similarity)
FTS5: SQLite FTS5 (664,835 docs)
Reranker: BAAI/bge-reranker-v2-m3 (567M params, GPU)
Fusion: Vector (200 candidates) + FTS5 (200 candidates) → merge → dedup → rerank top 20 → diversity filter
Diversity: max 5 por tribunal, empty tribunal = unlimited
Score threshold: ninguno (eliminado, el reranker se encarga)
```

## Tiempo de ejecución

```
50 queries en 77 segundos = 1.5 segundos por query
Breakdown: ~0.3s embedding + ~0.2s ChromaDB + ~0.1s FTS5 + ~0.5s reranker + ~0.4s overhead
Todo local, $0 de costo
```
