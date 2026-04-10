# LITIGIA — Benchmark de Costos por Tier y Escala

## Fecha: 9-10 de Abril 2026
## Saldo inicial: $26.81 (Anthropic Console)

## Caso de prueba (mismo para todos los tests)

> Director ejecutivo y accionista mayoritario de grupo empresario automotriz (3 sociedades anónimas, facturación anual $15.000M) fue denunciado penalmente por administración fraudulenta art. 173 inc. 7 del Código Penal tras descubrirse que desvió $800M a cuentas offshore mediante facturación apócrifa con sociedades vinculadas. El directorio lo cesó invocando mal desempeño del cargo art. 274 ley 19.550 y reclama USD 5M de daños. Simultáneamente AFIP inició determinación de oficio por evasión fiscal ley 24.769 por los ejercicios 2022-2025 con ajuste de $2.000M en impuesto a las ganancias. La defensa plantea prescripción de la acción penal, nulidad de la determinación por vicios en el procedimiento, y recurso extraordinario ante CSJN por arbitrariedad de la sentencia de Cámara que confirmó el procesamiento. El grupo entró en concurso preventivo y los acreedores piden extensión de quiebra al director por art. 161 ley 24.522. Hay embargo sobre bienes personales por $3.000M incluyendo inmuebles, vehículos de competición y participaciones societarias.

**Fuero:** Todos | **Caso multi-fuero:** penal, comercial, tributario, societario

---

## Grilla de costos

| # | Tier | Agentes | Transp. | Estimado | Tracker | Console real | Estado |
|---|------|---------|:-------:|----------|---------|-------------|--------|
| 1 | Economy | 10 | — | $0.10 | $0.1501 | $0.15 | LISTO |
| 2 | Economy | 30 | — | $0.21 | $0.3836 | $0.39 | LISTO |
| 3 | Economy | 50 | — | $0.32 | $0.60 | $0.61 | LISTO |
| 4 | Economy | 100 | — | $0.75 | $1.1271 | $0.93 | LISTO |
| 5 | Standard | 10 | — | $0.57 | $0.4794 | $0.51 | LISTO |
| 6 | Standard | 30 | — | $0.70 | $0.9736 | $0.97 | LISTO |
| 7 | Standard | 50 | — | $0.83 | $1.5147 | $1.52 | LISTO |
| 8 | Standard | 100 | SI | $1.22 | $3.3264 | $3.32 | LISTO |
| 9 | Premium | 10 | — | $0.79 | $0.4917 | $0.49 | LISTO |
| 10 | Premium | 30 | — | $1.36 | — | — | pendiente |
| 11 | Premium | 50 | — | $1.93 | — | — | pendiente |
| 12 | Premium | 100 | — | $3.35 | — | — | pendiente |
| 13 | Economy | 100 | SI | ~$0.81 | — | — | pendiente |
| 14 | Economy | 10 | SI | $0.12 | $0.2421 | $0.25 | LISTO |
| 15 | Premium | 100 | SI | ~$4.69 | — | — | pendiente |

### Modelos por tier

| Tier | Reader | Sintetizador | Descripcion |
|------|--------|-------------|-------------|
| Economy | Haiku 4.5 | Sonnet 4 | Minimo costo |
| Standard | Haiku 4.5 | Opus 4 | Mejor relacion calidad/precio |
| Premium | Sonnet 4 | Opus 4 | Maxima calidad |

---

## Precision del estimado vs costo real

| Test | Estimado | Console real | Ratio |
|------|----------|-------------|-------|
| Economy 10 | $0.10 | $0.15 | 1.5x |
| Economy 30 | $0.21 | $0.39 | 1.9x |
| Economy 50 | $0.32 | $0.61 | 1.9x |
| Economy 100 | $0.75 | $0.93 | 1.2x |
| Standard 10 | $0.57 | $0.51 | 0.9x |
| Premium 10 | $0.79 | $0.49 | 0.6x |

**Patron:** El estimado del frontend subestima ~1.5-2x en Economy. En Standard/Premium se acerca o sobreestima porque Opus (sintetizador) es el costo dominante y es fijo.

---

## Comparacion de calidad: Economy vs Standard (10 agentes)

Mismos 10 fallos analizados. Mismos readers (Haiku). Solo cambia el sintetizador: Sonnet vs Opus.

### Metricas cuantitativas

| Metrica | Economy (Sonnet) | Standard (Opus) |
|---------|-----------------|-----------------|
| % Favorable | 100% | 62.5% |
| Favorables | 7 | 6 |
| Desfavorables | 0 | 2 |
| Parciales | 0 | 1 |
| Inadmisibles | 3 | 1 |
| Estrategias exitosas | 4 | 4 |
| Estrategias fracasadas | 2 | 2 |
| Riesgos | 3 | 3 |
| Contradicciones | 0 | 2 |
| Costo | $0.15 | $0.51 |

### Diferencias cualitativas criticas (sintesis de los 3 tiers)

**1. Porcentaje favorable — cada tier ve la realidad diferente**

- Economy (Haiku+Sonnet): 100% favorable (7/7 excluyendo 3 inadmisibles). Sobreoptimista — clasifica todo como favorable.
- Standard (Haiku+Opus): 62.5% favorable (6/8 con fondo). Identifica 2 desfavorables y 1 parcial que Economy ignoro.
- Premium (Sonnet+Opus): 55.56% favorable (6/10 con fondo, 3 desfavorables, 1 parcial, 0 inadmisibles). El mas estricto — Sonnet como reader no descarta ningun fallo y Opus sintetiza con datos mas precisos.

**2. Contradicciones jurisprudenciales**

- Economy (Sonnet synth): 0 contradicciones. No las busca.
- Standard (Opus synth): 2 contradicciones reales: (1) Prescripcion penal tributaria: Berni S.A. (2012) prescripcion autonoma por ejercicio vs Lopez (2017) conducta sistematica unitaria. (2) Competencia art. 173: justicia ordinaria penal vs penal economico con componente tributario.
- Premium (Opus synth): 0 contradicciones significativas (Opus reviso y concluyo que no hay en los 10 fallos que leyo Sonnet). Nota: los fallos que leyeron son parcialmente distintos — Sonnet extrajo mas desfavorables y menos inadmisibles.

**3. Riesgos — los 3 tiers comparados**

Economy (Sonnet synth) — genericos, sin impacto directo al caso:
- "Archivo previo de causas fiscales puede bloquear acumulaciones"
- "Desistimiento procesal puede hacer fracasar recursos"
- "Falta de elementos sobre transcendencia federal puede llevar a inadmisibilidad"

Standard (Opus synth) — concretos, con casos y aplicacion al cliente:
- "En Lopez, Cristobal Manuel (2017), el director fue procesado por administracion fraudulenta agravada por desvio sistematico de fondos a sociedades vinculadas"
- "En Oleaginosa Oeste (2024), la CSJN anulo sentencias favorables cuando el contribuyente no pudo demostrar registros contables"
- "En Castro c/ BCRA (2008), se establecio que directores no pueden alegar ignorancia de infracciones comprobadas"

Premium (Opus synth) — concretos, con aplicacion DIRECTA al caso del cliente:
- "En Castro c/ BCRA (2008), los directores fueron condenados porque no pudieron alegar ignorancia — **el cliente no puede alegar desconocimiento del desvio de $800M**"
- "En Oleaginosa Oeste c/ DGI (2024), AFIP gano porque registros deficientes — **las facturas apocrifas del cliente refuerzan la posicion fiscal**"
- "En RPB SA c/ AFIP (2023), el REF fue rechazado por art. 280 — **el REX del cliente debe cumplir estrictamente todos los requisitos formales**"

La diferencia clave: Premium no solo cita el precedente sino que CONECTA el riesgo con los hechos especificos del caso del cliente (desvio $800M, facturas apocrifas, REX pendiente). Standard cita el caso pero la conexion es implicita.

**4. Estrategias fracasadas — Premium las identifica mejor**

Economy (Sonnet synth): 2 genericas ("acumulacion de causas archivadas", "impugnacion por desistimiento") — no sirven para el caso.
Standard (Opus synth): 2 relevantes ("REX sin requisitos formales", "omision de pronunciamiento sobre deficit probatorio") — utiles pero no advierte QUE EVITAR.
Premium (Opus synth): 3 especificas y ACCIONABLES:
1. "Alegar ignorancia/desconocimiento por parte de directores" — EVITAR, porque Castro c/ BCRA lo condeno
2. "REX sin cumplir requisitos formales" — EVITAR, porque RPB c/ AFIP fue rechazado por eso
3. "Cuestionar determinacion AFIP basandose en deficiencias de registros propios" — EVITAR, porque Oleaginosa Oeste perdio por eso

Esto es MUY valioso para un abogado: no solo dice que funciona, dice QUE NO HACER y POR QUE.

**5. Recomendacion estrategica**

Economy (Sonnet synth): "Priorizar recurso extraordinario federal por arbitrariedad invocando defecto de fundamentacion de la Camara" — va directo a una estrategia sin matices ni advertencias.

Standard (Opus synth): "Plantear prescripcion parcial de ejercicios 2022-2023 basandose en Berni S.A... promover incidente de incompetencia si procesamiento no fue dictado por juez penal economico, citando Vera Torres... invocar arbitrariedad por omision de tratamiento de prescripcion y vicios en determinacion de AFIP" — mas completo, multiples ejes, cita precedentes.

Premium (Opus synth): "Prescripcion del ejercicio 2022 invocando Berni S.A... nulidad de determinacion por vicios procedimentales... incompetencia a favor de fuero federal invocando Vera Torres y Bogarin... En subsidio, REX cumpliendo requisitos formales estrictos" — similar a Standard pero agrega Bogarin como precedente adicional y enfatiza los requisitos formales del REX (aprendido de RPB c/ AFIP).

### Comparacion 30 agentes: Economy vs Standard

| Metrica | Economy (Sonnet) | Standard (Opus) |
|---------|-----------------|-----------------|
| % Favorable | 87.5% | 57.89% |
| Fav/Desf/Parc/Inadm | 18/0/0/12 | 12/5/1/12 |
| Estrategias OK | 4 | 5 |
| Estrategias FAIL | 2 | 4 |
| Riesgos | 3 | 4 |
| Contradicciones | 0 | 2 |
| Costo | $0.39 | $0.97 |

**Mismo patron con 30 agentes (confirmado en 2 runs de Standard):**

1. **Sonnet infla el favorable**: 87.5% vs 57.89%. Sonnet encontro 0 desfavorables en 30 fallos. Opus encontro 5 desfavorables y 1 parcial. Sonnet clasifica como "inadmisible" lo que en realidad perdio.
2. **Contradicciones: Sonnet 0, Opus 2** — Art. 161 Ley 24.522 (Trenes de Buenos Aires vs Cablevision sobre extension de quiebra) y prescripcion penal tributaria (Costantini ordena examinar vs Bengen confirma sin examinar).
3. **Riesgos**: Opus cita LUSARDI, BENGEN (presuncion de conocimiento del director), Kseniya Simonova (inversion de carga probatoria), IGJ/AFIP (interrupcion de prescripcion). Sonnet da genericos.
4. **Recomendacion**: Opus da incidente de incompetencia + prescripcion como cuestion previa + REX con vicios AFIP citando Oleaginosa Oeste. Sonnet da una via principal y advertencias genericas.
5. **Opus es consistente entre runs**: Dos corridas de Standard 30 dieron resultados similares (56.25% y 57.89% favorable, 2 contradicciones en ambas, mismos casos citados en riesgos).

### Comparacion de readers: Economy/Standard vs Premium (10 agentes, fallo por fallo)

Economy y Standard usan Haiku como reader. Premium usa Sonnet. Mismos 10 fallos, mismos textos. Solo cambia quien LEE.

| Fallo | Economy (Haiku) | Standard (Haiku) | Premium (Sonnet) |
|-------|----------------|-----------------|-----------------|
| Lopez, Cristobal Manuel (defraudacion) | favorable | favorable | favorable |
| Berni S.A. (ley 24.769) | favorable* | parcial | **desfavorable** |
| Bogarin (competencia) | — | favorable | favorable |
| Vera Torres (damnificado) | favorable | favorable | favorable |
| Rodriguez, Dario (art. 173) | — | favorable | favorable |
| Cia. Seguros Minerva c/ Labunia (19.550) | — | favorable | favorable |
| Oleaginosa Oeste c/ DGI | favorable* | desfavorable | **desfavorable** |
| Castro c/ BCRA (directores) | favorable* | — | **desfavorable** |
| RPB S.A. c/ AFIP (queja) | — | desfavorable | **desfavorable** |
| Branca (incompetencia) | inadmisible | inadmisible | inadmisible |

(*) Economy (Haiku) clasifico como favorable fallos que los otros dos clasifican como desfavorable o parcial. Haiku no leyo que el fallo iba en contra del caso del cliente.

**Hallazgo: Sonnet como reader es el MAS ESTRICTO de los tres**

| Metrica reader | Economy (Haiku) | Standard (Haiku) | Premium (Sonnet) |
|----------------|----------------|-----------------|-----------------|
| % Favorable | 100% | 62.5% | 50% |
| Fallos favorables | 7 | 6 | 5 |
| Fallos desfavorables | 0 | 2 | **4** |
| Fallos parciales | 0 | 1 | 0 |
| Inadmisibles | 3 | 1 | 1 |

**Diferencias clave de los readers:**

1. **Berni S.A.**: Haiku (Economy) lo da como favorable — no entendio el fallo. Haiku (Standard) lo da como parcial. Sonnet (Premium) lo clasifica como **desfavorable** — el voto mayoritario establece prescripcion autonoma por ejercicio fiscal, lo que PERJUDICA al cliente porque impide alegar conducta unitaria. Sonnet fue el unico que interpreto correctamente el impacto para el caso.

2. **Castro c/ BCRA**: Haiku lo clasifico favorable en Economy pero Sonnet lo clasifica **desfavorable** — el fallo establece que directores NO pueden alegar desconocimiento de operaciones, lo cual va directamente contra la defensa del cliente.

3. **RPB S.A. c/ AFIP**: Standard (Haiku) y Premium (Sonnet) coinciden en desfavorable. Economy (Haiku) ni lo incluyo. El recurso fue rechazado por art. 280 — precedente negativo para nuestro REX.

4. **Oleaginosa Oeste**: Standard y Premium coinciden en desfavorable. Economy (Haiku) lo dio como favorable — error grave, la CSJN anulo la sentencia que favorecia al contribuyente.

**NOTA: El primer run de Premium 10 tuvo la sintesis rota (solo stats basicas). Se relanzo y el segundo run completo correctamente.**

### Comparacion completa de los 3 tiers (10 agentes) — readers + sintesis

Segundo run de Premium 10 (sintesis completa). Costo: $0.48.

| Metrica | Economy (Haiku+Sonnet) | Standard (Haiku+Opus) | Premium (Sonnet+Opus) |
|---------|----------------------|---------------------|---------------------|
| % Favorable | 100% | 62.5% | 55.56% |
| Fav/Desf/Parc/Inadm | 7/0/0/3 | 6/2/1/1 | 6/3/1/0 |
| Estrategias exitosas | 4 | 4 | 3 |
| Estrategias fracasadas | 2 | 2 | 3 |
| Riesgos | 3 | 3 | 3 |
| Contradicciones | 0 | 2 | 1* |
| Normas clave | ? | ? | 6 |
| Precedentes para citar | ? | ? | 6 |
| Costo | $0.15 | $0.51 | $0.48 |

(*) Premium reporto 1 contradiccion pero dice "no se detectan contradicciones significativas" — es decir, Opus reviso y concluyo que no hay. En Standard, Opus SI encontro 2 contradicciones reales (prescripcion Berni vs Lopez, competencia art. 173).

**Riesgos Premium (Sonnet readers + Opus synth):**
1. Castro c/ BCRA (2008): directores no pueden alegar ignorancia ante infracciones comprobadas
2. Oleaginosa Oeste c/ DGI (2024): AFIP gano porque registros contables deficientes — facturas apocrifas refuerzan esto
3. RPB SA c/ AFIP (2023): REF rechazado por art. 280 — el REX del cliente debe cumplir requisitos estrictos

**Estrategias exitosas Premium:**
1. Incompetencia territorial/federal invocando afectacion a AFIP y organismos nacionales
2. Prescripcion individual por ejercicio fiscal + doctrina delitos independientes por periodo
3. Administracion fraudulenta agravada demostrando patron sistematico + sociedades vinculadas

**Estrategias fracasadas Premium:**
1. Alegar ignorancia/desconocimiento por parte de directores (Castro c/ BCRA)
2. REX sin cumplir requisitos formales de admisibilidad (RPB c/ AFIP)
3. Cuestionar determinacion de AFIP basandose en deficiencias de registros propios (Oleaginosa Oeste)

**Recomendacion Premium:** Prescripcion inmediata del ejercicio 2022 (Berni S.A.), nulidad de determinacion por vicios, incompetencia a favor de fuero federal (Vera Torres, Bogarin), REX en subsidio cumpliendo requisitos formales estrictos.

### Basura procesal por tier (10 agentes)

| Metrica | Economy (Haiku) | Standard (Haiku) | Premium (Sonnet) |
|---------|----------------|-----------------|-----------------|
| Contenido util | 70% (7/10) | 90% (9/10) | **100% (10/10)** |
| Basura/inadmisibles | 30% (3/10) | 10% (1/10) | **0% (0/10)** |
| Input tokens | 39,639 | 37,807 | **33,183** |
| Output tokens | 12,875 | 12,809 | **8,033** |

Sonnet como reader no descarto ningun fallo — leyo los 10 y les extrajo contenido util. Haiku descarto 3 (Economy) y 1 (Standard) como inadmisibles sin analisis de fondo. Ademas Sonnet es mas conciso: 37% menos output tokens que Haiku (8K vs 12.8K), lo que reduce el costo del sintetizador Opus.

### Conclusion

**Opus (Standard/Premium) es NECESARIO para el sintetizador en un producto legal serio.**

El patron se confirma en AMBAS escalas (10 y 30 agentes):
- Sonnet como synth miente por omision — infla favorable, omite contradicciones, da riesgos genericos.
- Opus como synth dice la verdad incomoda con evidencia — identifica desfavorables reales, encuentra contradicciones, cita casos concretos, recomienda que evitar.

Para un abogado que toma decisiones estrategicas, un 100% favorable falso es PEOR que un 55% real. El abogado necesita saber los riesgos, no escuchar que va a ganar.

**Sonnet como READER (Premium) es superior a Haiku en todas las metricas:**
- Mas preciso: 55.56% favorable vs 62.5% (Standard) vs 100% (Economy) — identifica 3-4 desfavorables que Haiku ignora
- Menos basura: 0% inadmisibles vs 10-30% con Haiku
- Mas conciso: 37% menos output tokens → reduce costo del sintetizador
- Riesgos mas accionables: conecta precedentes con hechos ESPECIFICOS del caso del cliente
- Estrategias fracasadas claras: dice QUE NO HACER y POR QUE con caso concreto

**Ranking de tiers para produccion (10 agentes):**

1. **Premium (Sonnet+Opus) — $0.48** — MEJOR calidad, MENOR costo, 0% basura, riesgos conectados al caso. El tier que deberia ser default.
2. **Standard (Haiku+Opus) — $0.51** — Buena calidad de sintesis pero readers menos precisos. 10% basura. Contradicciones mejor detectadas.
3. **Economy (Haiku+Sonnet) — $0.15** — Solo para volumen masivo donde la precision no importa. 30% basura, 0 contradicciones, riesgos genericos.

**SORPRESA: Premium es MAS BARATO que Standard con 10 agentes** ($0.48 vs $0.51). Sonnet genera outputs mas concisos que Haiku, reduciendo el input al sintetizador Opus. Requiere confirmar con escalas 30/50/100.

---

## HALLAZGO CRITICO: El 70% del gasto es basura procesal

### El problema

En Standard 100 + transparencia ($3.33), de 89 fallos analizados:
- **62 inadmisibles** (70%) — rechazos por art. 280 CPCCN sin entrar al fondo
- 14 favorables, 8 desfavorables, 5 parciales (30% util)

Los agentes con chain of thought confirman el problema. TODOS dicen variaciones de:
- "El fallo es muy breve (2-3 paginas)"
- "Solo decide sobre procedencia del recurso de queja"
- "No aporta doctrina sobre prescripcion penal ni administracion fraudulenta"
- "Relevancia LIMITADA Y NEGATIVA"

Cada agente gasta ~$0.03 en tokens para leer un fallo de 3 lineas que dice "desestimase" y escribir 3 paginas explicando por que no sirve. **El 70% del costo ($2.33 de $3.33) se gasta en analizar fallos que no tienen contenido sustantivo.**

### Por que pasa

1. ChromaDB trae fallos PROCESALES cortos porque son semanticamente similares a la query (mencionan AFIP, art. 173 CP, ley 24.769) pero no tienen contenido de fondo
2. El reranker no distingue entre un fallo sustantivo (Lopez, Costantini, Berni — con doctrina, hechos, estrategia) y uno vacio (RPB SA c/ AFIP — 3 lineas de "art. 280 CPCCN, desestimase")
3. No hay filtro de calidad antes de mandar a los readers

### Solucion propuesta (pre-filtro de calidad)

Antes de enviar fallos a los readers, filtrar:
- **Por largo**: texto < 1000 caracteres → descartar (son rechazos de 1 pagina)
- **Por patron**: contiene "art. 280" + "desestimase" + < 2000 chars → marcar como inadmisible sin gastar reader
- **Por diversidad de contenido**: si el texto no contiene al menos 2 de las keywords del caso → descartar

Impacto estimado: de 100 fallos, descartaria ~50-60 inadmisibles procesales. Los 40-50 restantes serian sustantivos. **Ahorro del 50-60% en readers con mejor calidad de resultado.**

### Datos comparativos de desperdicio por escala

| Escala | Inadmisibles | % basura | Costo en basura (est.) |
|--------|-------------|----------|----------------------|
| Economy 10 | 3/10 | 30% | ~$0.04 |
| Economy 30 | 12/30 | 40% | ~$0.10 |
| Economy 50 | 35/50 | 70% | ~$0.28 |
| Economy 100 | 75/100 | 75% | ~$0.60 |
| Standard 100+transp | 62/89 | 70% | ~$2.33 |

A mayor escala, mayor proporcion de basura. El pipeline de busqueda satura en ~25-30 fallos sustantivos para este caso y rellena con inadmisibles procesales.

### Taxonomia del ruido procesal argentino

El ruido no es homogeneo. Los tipos identificados en el benchmark (ver `docs/NOISE_LEGAL_ARGENTINA.md`):

| Tipo | Causa | Señal principal |
|------|-------|-----------------|
| Art. 280 CPCCN | CSJN rechaza REX sin expresar fundamentos (80-90% de los REX) | "desestimase" + < 2000 chars |
| Queja por REX denegado (art. 285) | La misma basura pero un paso antes | "queja" + "denegacion origina" + < 1500 chars |
| Incidentes de competencia | Decide QUIEN juzga, no el fondo | "competencia" en titulo + < 1500 chars |
| Desistimientos (art. 304/305) | El actor abandona el caso | "desistimiento" o "dase por desistido" + < 1500 chars |
| Caducidades (art. 310) | El expediente no se movio durante el plazo legal | "caducidad de instancia" + < 1500 chars |
| Texto incompleto (SAIJ/CSJN) | El scraper capturo solo el sumario o PDF truncado | Cualquier fallo < 500 chars |

**Diferencia clave con EE.UU.:** Los cert denials de la SCOTUS no se publican como fallos.
En Argentina, cada rechazo art. 280 entra en SAIJ como "fallo" con metadatos completos.
El vector embedding los trata igual que un Fallos: 340:1771 de 30 paginas porque comparten
exactamente el mismo vocabulario juridico.

**Solucion implementada:** Pre-filtro de calidad en `backend/app/services/analysis.py`
(`_filter_low_quality`). Clasifica automaticamente como inadmisible sin gastar readers.
Ahorro estimado: 50-70% en costo de readers para casos multi-fuero.

---

## Incidentes durante el benchmark

1. **Economy 50 (primer intento):** MAX_PER_TRIBUNAL=5 hardcodeado limitaba resultados. Fix: escalar con top_k + backfill.
2. **UnicodeEncodeError:** Caracter unicode (flecha) en print crasheaba en Windows cp1252. Fix: reemplazar por ASCII.
3. **Standard 30 (primer intento):** Haiku devolvio "N/D — texto" como string en `precedentes_citados` en vez de lista. Pydantic crasheo al armar respuesta. Tokens gastados (~$1.08), resultado perdido. Fix: `_ensure_list()` sanitiza campos lista.
4. **autoSave silencioso:** Supabase rechazaba payloads >400KB por agent_thinking. `.catch(() => {})` tragaba el error. Fix: strip campos pesados + log errores.

---

## Saldo Anthropic

| Momento | Saldo |
|---------|-------|
| Inicio | $26.81 |
| Post Economy (4 tests) | $24.49 |
| Post Standard 10 | $23.98 |
| Perdido por crash Standard 30 | -$1.08 |
| Post Standard 30 (rerun) | $20.57 |
| Test transparency Economy 10 | -$0.25 |
| Test chain of thought Economy 10 | -$0.15 |
| Post Standard 50 | $19.05 |
| Post Standard 100 + transparencia | $15.73 |
| Post Premium 10 (sin transp.) | $15.24 |
| **Actual** | **$15.24** |
