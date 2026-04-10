# LITIGIA — Qué sigue después de testear con Claude

## Fecha

10 de abril de 2026

## Objetivo

Definir, con datos verificables, qué variantes conviene probar **después del benchmark Claude actual** y **antes** de meterse a una abstracción multi-provider grande.

La idea NO es probar modelos “porque sí”.

La idea es responder tres preguntas concretas:

1. **¿Podemos bajar costo sin perder contradicciones, desfavorables y riesgos concretos?**
2. **¿El cuello está en los readers, en el sintetizador, o en ambos?**
3. **¿Cuál es el próximo benchmark con mejor relación información/costo?**

---

## Lo que ya quedó verificado

### 1) Sonnet como sintetizador legal ya quedó cuestionado

Verificado en `docs/BENCHMARK_COSTOS.md` y en resultados guardados:

- **Economy 10** (Haiku readers + Sonnet synth): **100% favorable**, **0 contradicciones**
- **Standard 10** (Haiku readers + Opus synth): **62.5% favorable**, **2 contradicciones**
- **Economy 30**: **87.5% favorable**, **0 contradicciones**
- **Standard 30**: **57.89% favorable**, **2 contradicciones**

Conclusión práctica: para síntesis legal cruzada, **Sonnet no quedó validado**.

### 2) El benchmark actual también mostró un agujero metodológico

Antes de comparar providers, conviene cerrar 3 puntos:

1. **Retry de reader** cuando devuelve JSON malformado
2. **Checksum/cobertura** del sintetizador (`processed_case_ids`, `total_received`, `total_processed`)
3. **Gold set manual** para contradicciones/riesgos, no solo lectura “a ojo”

Si no hacemos eso, podemos cambiar de modelo y creer que mejoró cuando en realidad **solo perdió menos casos en silencio**.

### 3) El pipeline hoy sigue acoplado a Anthropic

Verificado en:

- `backend/app/services/analysis.py`
- `backend/app/services/tiers.py`
- `backend/app/core/config.py`

Hoy el análisis predictivo usa solo Anthropic. Entonces:

- **cambiar a Opus 4.6** es fácil
- **probar Gemini / GPT-5.4** requiere una capa de abstracción mínima

Por eso el orden importa.

---

## Snapshot de precios oficiales usados para estimar

> Todos los precios son por **1M tokens** y provienen de páginas oficiales consultadas el **10/04/2026**.

| Familia | Modelo | Input | Output | Observación |
|---|---:|---:|---:|---|
| Anthropic | Claude Haiku 4.5 | $1.00 | $5.00 | Reader barato actual |
| Anthropic | Claude Sonnet 4.6 | $3.00 | $15.00 | Sonnet actualizado |
| Anthropic | Claude Opus 4.6 | $5.00 | $25.00 | Mucho más barato que Opus 4 viejo |
| Google | Gemini 2.5 Pro | $1.25 / $2.50* | $10 / $15* | *depende si el prompt supera 200k |
| Google | Gemini 3.1 Pro Preview | $2.00 / $4.00* | $12 / $18* | *depende si el prompt supera 200k |
| Google | Gemini 2.5 Flash | $0.30 | $2.50 | Reader/synth barato con razonamiento |
| Google | Gemini 2.5 Flash-Lite | $0.10 | $0.40 | Reader ultrabarato |
| OpenAI | GPT-5.4 | $1.25 / $2.50** | $7.50 / $11.25** | **short/long context según pricing oficial |

---

## Cómo se estimaron los costos de las variantes

Las estimaciones de abajo NO salen del aire.

Se apoyan en los **costos medidos reales** ya obtenidos:

| Escala | Economy real | Standard real |
|---|---:|---:|
| 10 | $0.15 | $0.51 |
| 30 | $0.39 | $0.97 |
| 50 | $0.61 | $1.52 |

Asumimos esta descomposición:

- `Rk` = costo del bloque de **readers Haiku**
- `Sk` = costo del bloque de **synth Sonnet**

Como **Sonnet 4** y **Opus 4** difieren exactamente **5x** en input y output en la grilla clásica usada por el repo, se puede inferir:

- `R10 ≈ $0.06`, `S10 ≈ $0.09`
- `R30 ≈ $0.245`, `S30 ≈ $0.145`
- `R50 ≈ $0.384`, `S50 ≈ $0.226`

Eso permite reemplazar el componente synth o reader por otro modelo y obtener **estimaciones razonables**.

> Importante: siguen siendo **estimaciones**, no mediciones reales.

---

## Matriz priorizada de variantes para probar

### Leyenda

- **Medido** = ya existe dato real en Claude
- **Estimado** = inferido desde precios oficiales + benchmarks reales
- **Prioridad A** = hay que probarlo primero
- **Prioridad B** = vale la pena, pero después
- **Prioridad C** = solo control o exploración barata

| Variante | Qué responde | 10 | 30 | 50 | Prioridad |
|---|---|---:|---:|---:|---|
| **Baseline actual Economy** — Haiku 4.5 + Sonnet | Piso barato actual | **$0.15** | **$0.39** | **$0.61** | Medido |
| **Baseline actual Standard** — Haiku 4.5 + Opus 4 | Calidad actual validada | **$0.51** | **$0.97** | **$1.52** | Medido |
| **Claude Refresh Standard** — Haiku 4.5 + **Opus 4.6** | ¿Mismo patrón legal con costo mucho menor? | **$0.21** | **$0.49** | **$0.76** | **A** |
| **Claude Refresh Premium** — Sonnet 4.6 + Opus 4.6 | ¿Readers mejores justifican premium? | **$0.33** | **$0.98** | **$1.53** | B |
| **Haiku + Gemini 2.5 Pro synth** | ¿Gemini puede reemplazar a Opus como synth serio? | **$0.10–0.12** | **$0.31–0.34** | **$0.48–0.53** | **A** |
| **Haiku + Gemini 3.1 Pro synth** | Control Google más nuevo/caro | **$0.12–0.13** | **$0.34–0.36** | **$0.53–0.56** | B |
| **Haiku + GPT-5.4 synth** | Control externo adicional | **$0.10–0.11** | **$0.31–0.32** | **$0.48–0.50** | B |
| **Gemini 2.5 Flash readers + Opus 4.6 synth** | ¿Se puede bajar fuerte el reader sin tocar synth fuerte? | **$0.17–0.18** | **$0.32–0.36** | **$0.49–0.57** | **A** |
| **Gemini 2.5 Flash-Lite readers + Opus 4.6 synth** | Reader ultraeconómico con synth fuerte | **$0.17** | **$0.30–0.32** | **$0.47–0.49** | B |
| **Gemini 2.5 Flash readers + Gemini 2.5 Pro synth** | Combo Google barato end-to-end | **$0.06–0.09** | **$0.13–0.22** | **$0.21–0.34** | **A** |
| **Haiku + Gemini 2.5 Flash synth** | Control barato, probablemente flojo para contradicciones | **$0.07–0.08** | **$0.26–0.27** | **$0.41–0.42** | C |
| **Haiku + Haiku synth** | Control negativo: costo mínimo, calidad probablemente inviable | **$0.09** | **$0.29** | **$0.46** | C |

---

## Qué puede ayudarnos cada variante

### Prioridad A — las 4 que más información nos dan por dólar

#### 1) Claude Refresh Standard — Haiku 4.5 + Opus 4.6

**Para qué sirve**

- Aisla el efecto de pasar de **Opus 4 viejo** a **Opus 4.6**
- Mantiene stack conocido
- Casi no agrega riesgo de integración

**Qué puede demostrar**

- Si Opus 4.6 conserva la capacidad de detectar contradicciones y riesgos concretos
- Si Standard puede bajar de ~`$1.52` a ~`$0.76` en 50 fallos

**Si sale bien**

- Se convierte en nuevo Standard por defecto

#### 2) Haiku + Gemini 2.5 Pro synth

**Para qué sirve**

- Es la prueba más limpia de “**Opus vs Gemini como sintetizador**”
- Readers quedan iguales; solo cambia el synth

**Qué puede demostrar**

- Si Gemini 2.5 Pro detecta:
  - contradicciones
  - desfavorables reales
  - riesgos con caso + año
- a costo muy inferior

**Si sale bien**

- Puede ser el primer reemplazo real de Opus en LITIGIA

#### 3) Gemini 2.5 Flash readers + Opus 4.6 synth

**Para qué sirve**

- Ataca el otro componente del costo: los readers
- Mantiene synth fuerte

**Qué puede demostrar**

- Si el reader de Haiku puede ser reemplazado por uno aún más barato sin romper extracción

**Si sale bien**

- Aparece un nuevo tier tipo:
  - `Flash readers + Opus 4.6 synth`

#### 4) Gemini 2.5 Flash readers + Gemini 2.5 Pro synth

**Para qué sirve**

- Es el combo más agresivo costo/valor fuera de Anthropic
- Sirve para medir si Google completo puede competir

**Qué puede demostrar**

- Si existe una arquitectura “mucho más barata que Standard” sin caer en la mentira por omisión de Sonnet synth

**Riesgo**

- Si el synth falla en contradicciones, este combo se mata rápido

---

## Orden recomendado de ejecución

### Fase 0 — integridad del benchmark (antes de gastar en providers)

1. **Retry 1x** al reader si falla por JSON malformado
2. **Checksum de cobertura** en el synth:
   - `total_recibidos`
   - `ids_recibidos`
   - `ids_procesados`
3. **Gold set manual de 20 fallos**

#### Gold set sugerido

Separarlo en 4 bloques de 5:

1. **Contradicciones conocidas**
   - prescripción penal tributaria
   - extensión de quiebra art. 161
2. **Desfavorables claros**
3. **Inadmisibles art. 280**
4. **Favorables sustantivos largos**

La regla es simple:

- si el modelo no detecta bien este set, **ni pasa al benchmark grande**

### Fase 1 — refresh Claude

1. **Haiku 4.5 + Opus 4.6 synth** en 10
2. Si pasa, repetir en 30
3. Si pasa, reemplaza Standard actual

### Fase 2 — challenger synths

1. **Haiku + Gemini 2.5 Pro synth** en 10
2. **Haiku + GPT-5.4 synth** en 10 (control externo opcional)
3. Solo si alguno pasa, subir a 30

### Fase 3 — challenger readers

1. **Gemini 2.5 Flash readers + Opus 4.6 synth** en 10
2. Si no rompe extracción, subir a 30

### Fase 4 — combo barato serio

1. **Gemini 2.5 Flash readers + Gemini 2.5 Pro synth** en 10
2. Si detecta contradicciones y riesgos concretos, subir a 30

---

## Criterios de aprobación / descarte

Una variante solo “vive” si cumple estas condiciones:

### Synth

- **No infla favorable** groseramente
- Encuentra **al menos 80%** de las contradicciones del gold set
- Enumera **riesgos concretos** con caso y año
- Mantiene coherencia entre:
  - favorables
  - desfavorables
  - parciales
  - inadmisibles
  - porcentaje final

### Reader

- No pierde normas/precedentes clave
- No clasifica masivamente sustantivos como inadmisibles
- No aumenta la tasa de JSON roto

### Cobertura

- `total_procesados == total_enviados`
- o, si no, que quede explícitamente logueado cuáles faltaron

---

## Recomendación ejecutiva

Si hubiera que elegir solo **3 tests** para hacer ya mismo, haría estos:

1. **Haiku 4.5 + Opus 4.6 synth**  
   Porque es el upgrade más obvio y de menor riesgo.

2. **Haiku 4.5 + Gemini 2.5 Pro synth**  
   Porque es el challenger externo con mejor promesa costo/calidad.

3. **Gemini 2.5 Flash readers + Opus 4.6 synth**  
   Porque separa el problema reader del problema synth.

Eso te da, con poca plata, respuesta sobre:

- refresh interno
- reemplazo de synth
- reemplazo de readers

y evita quemar saldo en 20 combinaciones a ciegas.

---

## Fuentes oficiales

### Anthropic

- Claude Haiku 4.5: https://www.anthropic.com/claude/haiku
- Claude Sonnet 4.6: https://www.anthropic.com/claude/sonnet
- Claude Opus 4.6: https://www.anthropic.com/claude/opus

### Google

- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini 2.5 Pro announcement: https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-model-thinking-updates-march-2025/

### OpenAI

- GPT-5.4 pricing: https://developers.openai.com/api/docs/pricing
- GPT-5.4 announcement: https://openai.com/index/introducing-gpt-5-4/

---

## TL;DR

- **Primero**: arreglar integridad del benchmark
- **Después**: probar **Opus 4.6**
- **Luego**: probar **Gemini 2.5 Pro como synth**
- **Después**: probar **Gemini Flash como reader**
- **No gastar primero** en combos demasiado baratos sin synth fuerte

El mejor “qué sigue” hoy no es una locura cósmica de 20 providers.

Es un embudo disciplinado:

**integridad -> refresh Claude -> challenger synth -> challenger reader -> combo barato serio**
