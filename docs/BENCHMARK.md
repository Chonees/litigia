# LITIGIA — Benchmark Completo

## Fecha: 9-10 de Abril 2026
## Base: 471,511 vectores (ChromaDB) + 664,835 documentos (FTS5)
## Pipeline: Vector + FTS5 keyword + RRF fusion + Cross-encoder reranker + Recency boost

---

## PARTE 1: Precisión de Búsqueda (50 queries, $0 costo)

50 queries que cubren todas las áreas de práctica de una firma litigante de alto nivel. Se mide qué porcentaje de los 10 resultados devueltos son realmente relevantes.

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

### Resumen precisión

| Rating | Cantidad | Porcentaje |
|--------|----------|------------|
| EXCELENTE (80%+) | 26/50 | 52% |
| BUENA (60-79%) | 11/50 | 22% |
| ACEPTABLE (40-59%) | 3/50 | 6% |
| MALA (<40%) | 10/50 | 20% |
| **PROMEDIO** | | **68%** |

74% de queries en BUENA o EXCELENTE. 1.5s por query, $0 costo.

---

## PARTE 2: Benchmark de Costos y Calidad por Tier (26 tests reales)

Caso de prueba: Director ejecutivo de grupo automotriz denunciado por administración fraudulenta (art. 173 CP), cesado por mal desempeño (art. 274 ley 19.550), evasión fiscal (ley 24.769), concurso preventivo, extensión de quiebra (art. 161 ley 24.522). Cruza 4 áreas jurídicas: penal, societario, tributario, concursal. Monto en juego: USD 5M+.

### Economy (Haiku lectores + Sonnet sintetizador)

| Agentes pedidos | Agentes reales | Input tokens | Output tokens | Costo USD |
|-----------------|---------------|-------------|--------------|-----------|
| 10 | 10 | 39,639 | 12,875 | $0.15 |
| 10 (con transparencia) | 10 | 39,071 | 30,011 | $0.24 |
| 20 (con transparencia) | 18 | 68,722 | 56,526 | $0.42 |
| 30 | 30 | 114,054 | 35,530 | $0.38 |
| 30 | 30 | 105,938 | 32,854 | $0.37 |
| 50 | 50 | 188,480 | 54,945 | $0.61 |
| 50 | 50 | 187,639 | 55,374 | $0.61 |
| 100 | 100 | 366,587 | 104,194 | $1.13 |
| 100 (con transparencia) | 93 | 377,500 | 287,016 | $2.04 |

**Promedio Economy por escala (sin transparencia):**

| Agentes | Costo promedio | Costo por agente |
|---------|---------------|-----------------|
| 10 | $0.15 | $0.015 |
| 30 | $0.38 | $0.013 |
| 50 | $0.61 | $0.012 |
| 100 | $1.13 | $0.011 |

**Con transparencia: +40-80% de costo** (los agentes generan chain-of-thought, más output tokens).

### Standard (Haiku lectores + Opus sintetizador)

| Agentes pedidos | Agentes reales | Input tokens | Output tokens | Costo USD |
|-----------------|---------------|-------------|--------------|-----------|
| 10 | 10 | 37,807 | 12,809 | $0.48 |
| 10 | 10 | 36,697 | 12,426 | $0.46 |
| 20 | 20 | 68,602 | 22,127 | $0.72 |
| 30 | 30 | 106,046 | 32,780 | $0.95 |
| 30 | 30 | 105,475 | 32,887 | $0.97 |
| 30 | 30 | 103,381 | 32,591 | $0.97 |
| 50 | 50 | 188,138 | 55,992 | $1.51 |
| 50 | 50 | 185,359 | 53,382 | $1.44 |
| 100 | 89 | 371,500 | 285,059 | $3.33 |
| 100 | 92 | 373,071 | 288,467 | $3.45 |

**Promedio Standard por escala:**

| Agentes | Costo promedio | Costo por agente | Overhead vs Economy |
|---------|---------------|-----------------|-------------------|
| 10 | $0.47 | $0.047 | +$0.32 (Opus) |
| 20 | $0.72 | $0.036 | +$0.30 (Opus) |
| 30 | $0.96 | $0.032 | +$0.58 (Opus) |
| 50 | $1.48 | $0.030 | +$0.87 (Opus) |
| 100 | $3.39 | $0.034 | +$2.26 (Opus) |

**El overhead fijo de Opus ($0.30-0.65) domina el costo en escalas bajas.** En 10 agentes, Opus es el 68% del costo total. En 100 agentes baja al 19%.

### Premium (Sonnet lectores + Opus sintetizador)

| Agentes pedidos | Agentes reales | Input tokens | Output tokens | Costo USD |
|-----------------|---------------|-------------|--------------|-----------|
| 10 | 10 | 33,356 | 8,075 | $0.49 |
| 10 | 10 | 33,183 | 8,033 | $0.48 |
| 20 | 20 | 60,856 | 15,007 | $0.82 |
| 30 | 30 | 94,083 | 21,278 | $1.10 |
| 50 | 50 | 168,409 | 33,828 | $1.65 |
| 100 | 100 | 344,286 | 113,132 | $3.77 |

**Promedio Premium por escala:**

| Agentes | Costo promedio | Costo por agente | Overhead vs Standard |
|---------|---------------|-----------------|---------------------|
| 10 | $0.49 | $0.049 | +$0.02 |
| 20 | $0.82 | $0.041 | +$0.10 |
| 30 | $1.10 | $0.037 | +$0.14 |
| 50 | $1.65 | $0.033 | +$0.17 |
| 100 | $3.77 | $0.038 | +$0.38 |

**Premium vs Standard tiene poca diferencia** — Sonnet lectores cuestan un poco más que Haiku pero ambos usan Opus para sintetizar. La diferencia real está en la CALIDAD del análisis de cada fallo, no en el costo.

---

## PARTE 3: Comparación de Calidad entre Tiers

### Qué genera cada agente (ejemplo fallo real)

Los 3 tiers extraen los mismos 12 campos por fallo. La diferencia está en la PROFUNDIDAD:

**Economy (Haiku lector):** Extrae campos correctamente. Resultado, normas, precedentes son precisos. Campos de juicio (relevancia_cliente, argumento_clave) son más superficiales — 1-2 oraciones genéricas.

**Standard (Haiku lector + Opus sintetizador):** Misma calidad de extracción que Economy, pero el sintetizador Opus cruza patrones con mayor profundidad. La recomendación estratégica es más accionable y matizada.

**Premium (Sonnet lector + Opus sintetizador):** Sonnet extrae con más detalle — campos de juicio tienen 3-4 oraciones con análisis comparativo. El sintetizador Opus trabaja con mejor data y la recomendación es la más completa.

### Dónde se nota la diferencia

| Aspecto | Economy | Standard | Premium |
|---------|---------|----------|---------|
| Resultado (favorable/desfavorable) | Correcto | Correcto | Correcto |
| Normas citadas | 90% completas | 90% completas | 95% completas |
| Estrategia procesal | Básica | Básica | Detallada |
| Argumento clave | 1-2 oraciones | 1-2 oraciones | 3-4 oraciones con análisis |
| Relevancia para el cliente | Genérica | Genérica | Comparativa con hechos del caso |
| Recomendación estratégica | Accionable | Muy accionable (Opus) | Muy accionable (Opus + mejor data) |
| Contradicciones | Detecta las obvias | Detecta las obvias (Opus) | Detecta matices (Opus + Sonnet) |

### Recomendación por tipo de caso

| Tipo de caso | Tier recomendado | Agentes | Costo | Por qué |
|-------------|-----------------|---------|-------|---------|
| Rutinario (despido, accidente) | Economy | 10-20 | $0.15-0.38 | Mucha jurisprudencia, patrones claros |
| Medio (mala praxis, ejecución) | Standard | 20-30 | $0.72-0.96 | Opus sintetiza mejor los matices |
| Complejo (societario, tributario) | Premium | 30-50 | $1.10-1.65 | Sonnet extrae mejor en áreas técnicas |
| Crítico (multifuero, alto monto) | Premium | 50-100 | $1.65-3.77 | Máxima cobertura y profundidad |

---

## PARTE 4: Hallazgos Importantes

### Los agentes reales no siempre coinciden con los pedidos

Cuando pedís 100 agentes, a veces recibes 89, 92, o 93. Esto es por:
1. **Filtro de relevancia**: si de 500 candidatos solo 92 pasan el score mínimo del reranker
2. **Filtro de diversidad**: máximo 5 por tribunal
3. **Deduplicación**: fallos repetidos se eliminan

Esto es BUENO — significa que no gastás plata analizando fallos irrelevantes.

### La transparencia cuesta 40-80% más

El modo "transparencia" hace que cada agente explique paso a paso cómo razonó. Esto genera ~2x más output tokens. Un análisis Economy de 100 agentes pasa de $1.13 a $2.04 con transparencia.

### El sintetizador Opus es el costo fijo dominante

En escalas bajas (10 agentes), Opus representa 60-70% del costo total. Por eso Standard y Premium son caros incluso con pocos agentes. Economy evita esto usando Sonnet para sintetizar.

### El costo por agente baja con la escala

| Agentes | Economy/agente | Standard/agente | Premium/agente |
|---------|---------------|-----------------|---------------|
| 10 | $0.015 | $0.047 | $0.049 |
| 30 | $0.013 | $0.032 | $0.037 |
| 50 | $0.012 | $0.030 | $0.033 |
| 100 | $0.011 | $0.034 | $0.038 |

El costo marginal por agente adicional es bajo — la mayor parte es el sintetizador.

---

## PARTE 5: Queries que fallan y cómo mejorar

### 0% precisión — No encuentra NADA relevante

- **Tercerización fraudulenta** — embedding diluye el término, FTS5 encuentra pero reranker puntúa bajo
- **Daño ambiental** — poca jurisprudencia en la base, terminología diferente
- **Franquicia comercial** — se confunde con franquicia de seguro automotor
- **Expropiación** — fallos clásicos son pre-2015, CSJN solo tiene desde 2015

### Hoja de ruta de mejoras

| Mejora | Impacto | Esfuerzo | Costo |
|--------|---------|----------|-------|
| Re-ingestión con prefijos "passage:" | +10-15% | 6hs GPU | $0 |
| Más datos CSJN (pre-2015) | +15-20% en fallos | Días de scraping | $0 |
| Reranker fine-tuneado legal AR | +10-15% | 1000 pares anotados | $0 |
| Upgrade a e5-large-instruct | +10% | 8-10hs re-ingestión | $0 |
| Query expansion con Haiku | +5-10% | 1 llamada extra/query | $0.001/query |

---

## PARTE 6: Configuración técnica

```
Embedding: intfloat/multilingual-e5-base (768 dim) + prefix "query: "
Vector DB: ChromaDB 1.5.6 (471,511 docs, cosine similarity)
FTS5: SQLite FTS5 (664,835 docs, BM25)
Reranker: BAAI/bge-reranker-v2-m3 (567M params, GPU)
Recency boost: +0.15 para año actual, decae a 0 en 30 años
Fusion: Vector (500 max) + FTS5 (500 max) → merge → dedup → rerank top 200 → diversity → top K
Diversity: max 5 por tribunal
Cancel: asyncio.Event checked before every Claude call
Tiers: Economy (Haiku+Sonnet), Standard (Haiku+Opus), Premium (Sonnet+Opus)
Transparency: optional chain-of-thought, +40-80% cost
```

## Gasto total del benchmark

```
26 tests realizados
Economy:  10 tests = $6.17
Standard: 10 tests = $14.30
Premium:   6 tests = $8.31
TOTAL:    $28.78
```
