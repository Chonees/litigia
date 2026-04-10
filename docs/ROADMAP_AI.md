# LITIGIA — Roadmap: Modelos de IA Propios

## Por qué es posible

Tenemos algo que casi ninguna empresa de IA legal tiene:
- **664,835 fallos reales argentinos** con texto completo (CSJN + SAIJ + JurisGPT)
- **471,511 ya vectorizados** con metadatos estructurados
- **Pipeline que genera training data gratis** — cada análisis que corre produce pares (query → fallo relevante) validables
- **Un abogado real** que puede marcar qué resultados son correctos y cuáles no

Las empresas de IA generan modelos GENÉRICOS. Un modelo entrenado con 664K fallos argentinos reales va a ser MEJOR que Claude para jurisprudencia argentina específica.

---

## Fase 1: Reranker Legal Argentino (2-4 semanas)

### Qué es
Fine-tunear el cross-encoder `bge-reranker-v2-m3` para que entienda relaciones legales argentinas. Hoy es genérico — no sabe que "art. 31 LCT" y "solidaridad del grupo económico" están relacionados.

### Datos necesarios
- ~1,000-3,000 pares (query, fallo, score 0-1)
- Se extraen de los análisis guardados en Supabase
- El abogado marca cuáles fueron realmente útiles (score 1) y cuáles no (score 0)

### Cómo se entrena
```python
from sentence_transformers import CrossEncoder, InputExample
model = CrossEncoder("BAAI/bge-reranker-v2-m3")
# Fine-tune con pares legales argentinos
model.fit(train_dataloader, epochs=3)
model.save("litigia-reranker-v1")
```

### Impacto esperado
- Benchmark de 68% → 85-90%
- La tercerización (hoy 0%) debería subir a 60%+
- Costo: $0 (corre en la 4090 local)
- Cada análisis que se corra después genera más data para mejorar

### Requerimientos
- RTX 4090 Laptop (ya la tenemos)
- 4 horas de validación del abogado
- 2 horas de entrenamiento

---

## Fase 2: Embedding Model Legal Argentino (1-2 meses)

### Qué es
Fine-tunear `multilingual-e5-base` (o upgradear a `e5-large-instruct`) para que entienda terminología legal argentina nativamente.

### Problema actual
- Los documentos se embeddieron sin prefijo "passage:" → 15-20% de pérdida
- El modelo no distingue bien entre "despido genérico" y "despido por embarazo art. 178"
- Los scores están comprimidos (0.79-0.90) — basura y match perfecto están a 0.10 de distancia

### Datos necesarios
- Tripletas: (query, fallo positivo, fallo negativo)
- Los positivos vienen de los análisis donde el reranker dio score alto
- Los negativos vienen de los que el reranker descartó
- ~10,000-50,000 tripletas (se generan semi-automáticamente del pipeline)

### Cómo se entrena
```python
from sentence_transformers import SentenceTransformer, losses
model = SentenceTransformer("intfloat/multilingual-e5-base")
train_loss = losses.TripletLoss(model)
model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=5)
model.save("litigia-embeddings-v1")
```

### Impacto esperado
- Scores con rango amplio (0.3-0.95) → filtros de relevancia funcionan de verdad
- Búsqueda semántica mucho más precisa para temas específicos
- Elimina la necesidad del prefijo "passage:"

### Requerimientos
- Re-ingestión completa de 664K documentos (~6-8 horas en 4090)
- 10K+ pares de entrenamiento (generados del pipeline)
- 4-6 horas de entrenamiento

---

## Fase 3: LLM Legal Argentino — Reemplazo de Claude (3-6 meses)

### Qué es
Fine-tunear un modelo grande (Gemma 4 26B MoE o Llama 3.3 70B) para que sea experto en derecho argentino. Reemplaza a Claude como lector y potencialmente como sintetizador.

### Qué cambia
- Los 100 agentes lectores corren LOCAL → $0 por análisis
- El sintetizador corre LOCAL → $0 por análisis
- Costo total por análisis: ~$0.02 (electricidad)
- Sin rate limits — 100 agentes en paralelo real

### Datos de entrenamiento
- **Corpus base:** 664K fallos completos para continued pre-training
- **Instruction tuning:** Miles de pares (prompt del READER, JSON extraído) generados por Claude
- **RLHF / DPO:** Pares de (análisis bueno, análisis malo) validados por el abogado
- Los análisis Premium de Claude sirven como "teacher" para el modelo local

### Arquitectura
```
Opción A: Gemma 4 26B MoE (solo 4B activos por inferencia)
  - Corre en 1x RTX 4090 (24GB)
  - ~30 tok/s
  - Calidad: ~80% de Sonnet para extracción
  - Costo hardware: $0 (ya lo tenemos)

Opción B: Llama 3.3 70B Q5
  - Necesita 2x RTX 5090 (64GB)
  - ~40 tok/s
  - Calidad: ~90% de Sonnet para extracción
  - Costo hardware: ~$4,000

Opción C: Fine-tune de 70B+ en la nube (Together/Modal/Lambda)
  - Entrenamiento: ~$200-500 en GPU cloud
  - Inferencia: local en 2x 5090
```

### Impacto
- De ~$2.70/análisis (Premium) a ~$0.02/análisis
- Sin dependencia de APIs externas
- Sin rate limits
- Modelo que ENTIENDE derecho argentino, no solo lo procesa

### Requerimientos
- 2x RTX 5090 o equivalente (~$4,000)
- 1-2 meses de preparación de datos
- 1-2 meses de entrenamiento y evaluación
- Validación continua del abogado

---

## Cómo cada análisis genera training data

```
Usuario hace análisis → Pipeline genera:

1. PAR PARA RERANKER:
   (query del usuario, fallo encontrado, rerank_score)
   → Si el abogado valida → training pair confirmado

2. TRIPLETA PARA EMBEDDINGS:
   (query, fallo con rerank alto, fallo con rerank bajo)
   → Generadas automáticamente de cada búsqueda

3. INSTRUCTION PAIR PARA LLM:
   (READER_PROMPT + fallo, JSON extraído por Claude)
   → Claude genera el "ground truth" que entrena al modelo local

4. PREFERENCE PAIR PARA DPO:
   (prompt, respuesta Premium, respuesta Economy)
   → El abogado dice cuál prefiere → entrena preferencias
```

**Cada análisis que Sebastián corra es training data gratis.** En 6 meses de uso moderado (10 análisis/día) vas a tener ~1,800 análisis validados = suficiente para fine-tunear el reranker y empezar con los embeddings.

---

## Timeline estimado

| Fase | Tiempo | Costo | Impacto en benchmark |
|------|--------|-------|---------------------|
| Fase 1: Reranker | 2-4 semanas | $0 | 68% → 85-90% |
| Fase 2: Embeddings | 1-2 meses | $0 | 85% → 90-95% |
| Fase 3: LLM Local | 3-6 meses | $4,000 (hardware) | $0/análisis, sin límites |

## Estado actual de datos (Abril 2026)

| Fuente | Documentos | Período |
|--------|-----------|---------|
| SAIJ | 495,580 | Histórico completo |
| CSJN | 168,516 | Mar 2026 → Mar 2015 |
| JurisGPT | 739 | Varios |
| **Total** | **664,835** | |
| **Vectorizados (ChromaDB)** | **471,511** | |
| **Indexados FTS5** | **664,835** | |

Para Fase 3 idealmente necesitamos CSJN completo (1863-presente) → potencialmente 500K+ fallos más.
