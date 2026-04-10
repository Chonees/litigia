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
| 6 | Standard | 30 | — | $0.70 | — | — | pendiente |
| 7 | Standard | 50 | — | $0.83 | — | — | pendiente |
| 8 | Standard | 100 | — | $1.15 | — | — | pendiente |
| 9 | Premium | 10 | — | $0.79 | — | — | pendiente |
| 10 | Premium | 30 | — | $1.36 | — | — | pendiente |
| 11 | Premium | 50 | — | $1.93 | — | — | pendiente |
| 12 | Premium | 100 | — | $3.35 | — | — | pendiente |
| 13 | Economy | 100 | SI | ~$0.81 | — | — | pendiente |
| 14 | Standard | 100 | SI | ~$1.61 | — | — | pendiente |
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

**Patron:** El estimado del frontend subestima ~1.5-2x en Economy. En Standard se acerca mas porque Opus (sintetizador) es el costo dominante y es fijo.

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

### Diferencias cualitativas criticas

**1. Porcentaje favorable — Opus es mas realista**

- Sonnet: 100% favorable (7/7 excluyendo inadmisibles). Sobreoptimista — clasifica todo como favorable.
- Opus: 62.5% favorable (6/8 con fondo). Identifica 2 desfavorables y 1 parcial que Sonnet ignoro.

**2. Contradicciones jurisprudenciales — Opus las encuentra, Sonnet no**

Opus identifico 2 contradicciones que Sonnet omitio por completo:
- Prescripcion penal tributaria: Berni S.A. (2012) establece prescripcion autonoma por ejercicio fiscal vs Lopez (2017) sugiere conducta sistematica unitaria.
- Competencia en art. 173: algunos fallos van a justicia ordinaria penal vs otros a penal economico cuando hay componente tributario.

**3. Riesgos — Opus cita casos concretos, Sonnet es generico**

- Opus: "En Lopez, Cristobal Manuel (2017), el director fue procesado por administracion fraudulenta agravada por desvio sistematico de fondos a sociedades vinculadas"
- Sonnet: "Falta de elementos suficientes sobre transcendencia federal puede llevar a inadmisibilidad"

**4. Recomendacion estrategica — Opus es mas matizada**

- Sonnet: "Priorizar recurso extraordinario federal por arbitrariedad" — va derecho a una estrategia.
- Opus: "Plantear prescripcion parcial de ejercicios 2022-2023 basandose en Berni S.A... Evitar alegar desconocimiento de operaciones (Castro c/ BCRA)... La defensa debe enfocarse en aspectos procesales mas que en negar la materialidad" — identifica que hay que evitar, cita casos especificos, y da una recomendacion mas completa.

### Comparacion 30 agentes: Economy vs Standard

| Metrica | Economy (Sonnet) | Standard (Opus) |
|---------|-----------------|-----------------|
| % Favorable | 87.5% | 56.25% |
| Fav/Desf/Parc/Inadm | 18/0/0/12 | 13/6/0/11 |
| Estrategias OK | 4 | 4 |
| Estrategias FAIL | 2 | 3 |
| Riesgos | 3 | 4 |
| Contradicciones | 0 | 2 |
| Costo | $0.39 | $0.95 |

**Mismo patron con 30 agentes:**

1. **Sonnet infla el favorable**: 87.5% vs 56.25%. Sonnet encontro 0 desfavorables en 30 fallos. Opus encontro 6. Sonnet clasifica como "inadmisible" lo que en realidad perdio.
2. **Contradicciones: Sonnet 0, Opus 2** — Art. 274 LGS ("mal desempeno" como causal autonoma vs responsabilidad amplia) y competencia federal (ordinaria vs penal economico automatico).
3. **Riesgos**: Opus cita BENGEN (2007), LUSARDI (2007), Kseniya Simonova (2018) con doctrina. Sonnet da genericos.
4. **Recomendacion**: Opus da 3 vias simultaneas con caso para cada una + que evitar. Sonnet da una via principal y advertencias genericas.

### Conclusion

**Opus (Standard/Premium) es NECESARIO para el sintetizador en un producto legal serio.**

El patron se confirma en AMBAS escalas (10 y 30 agentes):
- Sonnet miente por omision — infla favorable, omite contradicciones, da riesgos genericos.
- Opus dice la verdad incomoda con evidencia — identifica desfavorables reales, encuentra contradicciones, cita casos concretos, recomienda que evitar.

Para un abogado que toma decisiones estrategicas, un 87.5% favorable falso es PEOR que un 56.25% real. El abogado necesita saber los riesgos, no escuchar que va a ganar.

El sweet spot para produccion es **Standard** (Haiku readers + Opus synth): calidad de sintesis de Opus a ~$0.51-0.95/analisis, vs Premium que solo mejora la extraccion (readers Sonnet vs Haiku).

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
| **Actual** | **$22.90** |
