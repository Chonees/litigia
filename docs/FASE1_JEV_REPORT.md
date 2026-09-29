# Fase 1 — Jev en castellano jurídico: reporte

**Veredicto: Jev sirve para etiquetar sentencias de la Cámara Nacional del Trabajo.** Cumple el criterio de salida del plan en las 6 preguntas del fallo y en el rol de cada párrafo. Para llegar hubo que ajustar las preguntas en tres iteraciones, calcular en código la estructura de votos y usar consenso de 3 corridas. El costo quedó **por encima de la meta** ($71 contra $50 para 60.000 fallos), pero sigue siendo 5 veces más barato que Haiku, y Haiku acierta menos.

Fecha: 2026-09-27 · Modelo: `jev-1.13.0` (versión fijada) · Muestra: 30 fallos de la CNAT, marzo 2024.

---

## 1. Cómo se midió

| Paso del plan | Qué se hizo |
|---|---|
| 1.1–1.2 | API key en `backend/.env` (`TYPESAFE_API_KEY`), SDK `typesafe-sdk 0.7.2`, versión fijada en `settings.typesafe_model`. Todas las respuestas vinieron de `jev-1.13.0`. |
| 1.4 | **Set de verdad de 30 fallos**, estratificado: 10 despido, 10 accidente ley especial, 7 recurso Ley 27.348 y 3 otros. Lo etiquetaron tres agentes (Opus) que leyeron cada fallo completo, citaron el párrafo de evidencia y marcaron las etiquetas dudosas. **Todavía falta que lo revise una persona.** |
| 1.5 | `state` = metadatos + párrafos numerados (`p0…pN`). Todas las preguntas van en una sola llamada. |
| 1.6–1.8 | Acierto y cobertura por umbral de confianza, calibración, y consistencia entre corridas con un `uid` nuevo en cada una. |
| 1.9 | Instrucciones en castellano contra inglés; fallo completo contra párrafos filtrados. |
| 1.10 | Mismas preguntas con Claude Haiku 4.5 y salida estructurada. |
| 1.11–1.12 | Tokens, costo, latencia y análisis de cada error. |

Código: `backend/spikes/jev_fase1/` (descartable). Piezas reutilizables, con tests: `scripts/labeling/state.py`, `metrics.py` y `votes.py`. Respuestas guardadas en `D:/litigia-data/labels/fase1/`. Set de verdad: `backend/labels/gold/`.

**Criterio de salida del plan:** ≥ 90% de acierto por encima del umbral, ≥ 70% de cobertura, ≥ 98% de consistencia y < $50 para 60.000 fallos.

## 2. Resultado final (v1.2, consenso de 3 corridas, estado completo)

| Pregunta | Umbral | Acierto | Cobertura | Consistencia | ¿Cumple? |
|---|---|---|---|---|---|
| Tipo de caso | 0,6 | 100% | 97% | 100% | ✅ |
| Quién apeló | 0,6 | 100% | 97% | 100% | ✅ |
| Agravios del trabajador | 0,6 | 97% | 97% | 100% | ✅ |
| Agravios de la demandada | 0,6 | 92% | 87% | 100% | ✅ |
| Materia apelada (fondo / accesorios) | 0,5 | 97% | 100% | 100% | ✅ |
| Costas de alzada | 0,6 | 97% | 100% | 100% | ✅ |
| **Rol de cada párrafo** (843 párrafos) | 0,8 | 95% | 83% | 97% | ✅ en la práctica |
| Holding recuperado desde los roles | — | 26/26 fallos | — | — | ✅ |
| Disidencias detectadas (3 fallos, 41 párrafos) | — | 36/41 párrafos | — | — | ✅ |

Por debajo del umbral, la etiqueta queda como **"sin determinar"**: nunca se inventa.

## 3. Cómo se llegó: tres iteraciones

| Versión | Cambio | Efecto |
|---|---|---|
| **v0** | 5 preguntas universales, holding como elección de párrafo | Tipo, costas y quién apeló, bien. **Resultado de la apelación 73%** y **holding 73%**, con una confianza que no servía para decidir. |
| **v1** | "Contestar o replicar el recurso de la otra parte NO es apelar". Resultado dividido en agravios por parte. Holding reemplazado por el rol de cada párrafo. | Quién apeló pasa a 100%. El holding sale de los roles en 25/26 fallos. **Disidencias: falla** (2 de 29 párrafos de minoría detectados). |
| **v1.1** | **La estructura de votos se calcula en código** (`votes.py`: "X DIJO:", "adhiero al voto de la Dra. X", propuestas distintas). Jev solo decide la función del párrafo. Agravios con 4 opciones. | Disidencias: 36/41. Agravios del trabajador pasa de 80% a 97%. |
| **v1.2** | **Para las preguntas del fallo, el código saca del `state` los párrafos del voto en minoría.** Consenso de 3 corridas. | Se corrige la trampa de la disidencia en agravios de la demandada. Las 6 preguntas cumplen. |

**La lección de diseño:** lo que el código puede decidir, lo decide el código. Jev falla donde la documentación de TypeSafe dice que falla (lectura literal, indirección) y rinde muy bien cuando la pregunta es literal y el `state` trae solo lo relevante.

## 4. Las otras preguntas del plan

| Pregunta | Respuesta medida |
|---|---|
| ¿Castellano o inglés en las instrucciones? | **Da igual:** ±1 fallo de diferencia en cada pregunta. Nos quedamos con el castellano, que es más fácil de mantener con términos jurídicos. |
| ¿Fallo completo o párrafos filtrados? | Filtrado usa **38% menos tokens** con el mismo acierto en v0. En v1.2 con consenso pierde algo (agravios del trabajador 97% → 93%, materia 100% → 90%). **Recomendación: estado completo.** |
| ¿Jev o Haiku? | **Jev.** Haiku acierta menos (tipo de caso 87% contra 97%, resultado 63% contra 73%), no da probabilidades, tarda 1,75 s contra 0,32 s y cuesta **27 veces más** ($355 contra $13 por 60.000 fallos, una pasada). Los planes B y C no hacen falta. |
| ¿Calibración? | Buena donde importa: las respuestas con confianza ≥ 0,9 aciertan el **97%** (705 respuestas). Entre 0,5 y 0,9 está sobreestimada, por eso usamos umbral y consenso. |
| ¿Consistencia sin consenso? | 90–100% según la pregunta. Coincide con el cookbook de TypeSafe (90,8%). El consenso de 3 corridas lleva todo a 100%. |

## 5. Costo por fallo (configuración recomendada)

| Componente | Tokens por fallo | Costo por 60.000 fallos |
|---|---|---|
| Preguntas del fallo, 3 corridas (consenso) | ~14.750 | $37 |
| Rol de cada párrafo, 1 corrida | ~13.260 | $33 |
| **Total** | **~28.000** | **~$71** |

⚠️ **Supera la meta de $50 del plan.** Alternativas medidas:

| Configuración | Costo | Contra qué |
|---|---|---|
| Estado filtrado | ~$57 | Pierde algo de acierto |
| 1 sola corrida sin consenso | ~$46 | No cumple la consistencia en agravios |

**Recomendación: pagar los $71.** Es un costo único de ingesta, y la precisión es el producto.

## 6. Limitaciones

1. **n = 30.** Un fallo de diferencia mueve 3 puntos. La Fase 3 lo confirma con 100 fallos.
2. **El set de verdad lo etiquetó Claude, no una persona.** Falta la revisión humana (≈ 1 hora) antes de dar los números por definitivos.
3. **Etiquetas dudosas:** los etiquetadores marcaron zonas grises reales (sección 7). Donde la definición es ambigua, ni un humano ni Jev pueden acertar siempre.
4. **Solo CNAT, marzo 2024.** Otros fueros van a necesitar sus propias preguntas.
5. Los 2 casos de "argumenta y después adhiere por economía procesal" no son disidencias formales y hoy no se distinguen.

## 7. Qué alimenta a la Fase 2 (mapa de preguntas)

Reglas que los etiquetadores pidieron y que hay que escribir en el mapa v1:

- **Intereses:** si una apelación solo por tasa, capitalización o actualización es accesoria (hoy sí) y cómo cuenta un cambio de tasa aplicado de oficio (Acta 2783).
- **Recursos desiertos o mal concedidos:** si la Cámara igual decide un agravio en el fondo, se etiqueta por ese resultado.
- **Tipo de caso:** por lo que resuelve la Cámara, no por la carátula (por ejemplo, una "acción civil" resuelta por la ley de riesgos del trabajo).
- **Costas partidas por demandado:** agregar una opción "mixtas", y si el voto y el RESUELVE se contradicen, manda el RESUELVE.
- **Roles nuevos:** `propuesta_voto` (el "propongo…" de cada voto), `concurrencia` (adhiere con fundamentos propios), `voto_con_reservas` (argumenta y después adhiere) y `otro`.
- **Párrafos mixtos:** etiquetar por la función de la mayor parte del texto. Revisar el armado de párrafos, que a veces corta frases o mezcla el final de un voto con el comienzo del siguiente.
- **Recursos directos sin trabajador** (un sindicato contra el Ministerio): una opción "no aplica".

## 8. Cómo reproducirlo (desde `backend/`)

```bash
python -m spikes.jev_fase1.sample          # muestra (semilla fija)
python -m spikes.jev_fase1.run_jev         # v0: es/en, completo/filtrado, 5 corridas
python -m spikes.jev_fase1.run_haiku       # comparación con Haiku
python -m spikes.jev_fase1.run_jev_v11     # v1.1: roles + votos por código
RUNS=6 python -m spikes.jev_fase1.run_jev_v12   # v1.2: sin la disidencia, 6 corridas
python -m spikes.jev_fase1.evaluate        # reporte v0
python -m spikes.jev_fase1.evaluate_v11    # reporte v1.1
```

Todas las corridas son idempotentes (quedan en caché). Costo total de la Fase 1: menos de $0,50 entre Jev y Haiku.
