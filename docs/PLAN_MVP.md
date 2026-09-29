# LITIGIA — Plan hasta el MVP

Plan de ejecución, en pasos chicos y en orden de prioridad. Cada paso dice qué se hace, cómo sabemos que vamos bien, cuándo está terminado y qué hacemos si algo sale mal.

El diseño del sistema está en el [README](../README.md). Este documento es el **orden de construcción**.

Estado de partida (2026-09-27): capa de datos construida y probada. Scraper PJN al 100% de completitud, contrato de calidad, catálogo, enriquecimiento por regex, auditoría y 71 tests. 932 fallos indexables activos, casi todos de la Cámara Nacional del Trabajo (CNAT), marzo 2024.

---

## 1. Qué es el MVP

**Una sola frase:** un abogado laboralista de CABA describe su caso en 5 campos y en menos de 10 segundos recibe los fallos de la Cámara Nacional del Trabajo que resolvieron su misma cuestión, separados en a favor y en contra, cada uno con el párrafo literal para citar.

| Entra en el MVP | Queda afuera (después del MVP) |
|---|---|
| Fuero laboral, **Cámara Nacional del Trabajo** (CABA) | Otras cámaras, la CSJN, las justicias provinciales |
| Sentencias definitivas de **2022 a hoy** (~50.000 a 60.000 fallos, estimado) | Años anteriores e interlocutorias |
| Etiquetado por tipo de caso con Jev, más regex | Etiquetas por tipo de caso fuera de laboral |
| Búsqueda híbrida por párrafo, filtrada por etiquetas | Alertas, historial y carpetas por cliente |
| Fichas a favor / en contra, con cita copiable y link al PDF oficial | Texto generado (resúmenes, escritos) |
| Job diario que mantiene la base al día | Cuentas, pagos, multiusuario |
| **Piloto con 2 o 3 laboralistas reales** | Lanzamiento público |

**Por qué este recorte:**
- **El scraper del PJN ya funciona** para esta cámara (100% de completitud, 0 errores). Es la base más sólida que tenemos.
- **Es un fuero de alto volumen y muy repetitivo:** 4 tipos de caso cubren el 92% de los fallos, y las Salas reiteran votos modelo. Eso permite llegar a precisión alta rápido.
- **Hay muchos laboralistas,** y buscan jurisprudencia todo el tiempo (tasa, RIPTE, multas, incapacidad).
- **2022 en adelante** deja fuera el derecho viejo (antes de la Ley 27.348 y de las actas de tasa recientes), que confunde más de lo que ayuda.

---

## 2. La experiencia de usuario del MVP

### El recorrido del abogado

1. **Entra** y ve un formulario de 5 campos: fuero (fijo en laboral), jurisdicción (fija en CABA), represento a (actor / demandado), cuestión jurídica, hechos clave (hasta 3).
2. **Escribe la cuestión con la plantilla** *"¿Procede [qué] cuando [hecho determinante], según [norma]?"*. Si no la sigue, el campo se marca y muestra un ejemplo.
3. **Toca Buscar.** En menos de 10 segundos ve dos columnas: **A FAVOR** y **EN CONTRA**.
4. **Cada ficha** muestra: certeza · Sala · fecha · carátula · N° de sentencia · resultado · etiquetas del caso (por ejemplo: *despido · apeló la demandada · multa art. 80: procede*) · el **párrafo literal** que responde su cuestión · "criterio reiterado en N fallos" cuando aplica.
5. **Primero aparece lo de su misma Sala**, si la indicó.
6. **Acciones:** Ver PDF oficial · Copiar cita (formato listo para pegar en el escrito) · **¿Sirvió? sí / no**.
7. **Si no hay nada con certeza suficiente**, no se muestra ruido: *"No hay fallos con precisión suficiente"*, con sugerencias (quitar un hecho, reformular la cuestión).

### Reglas de la experiencia

| Regla | Por qué |
|---|---|
| Nada de texto generado | El abogado cita; un resumen inventado le puede costar el caso |
| Toda afirmación con su fuente (párrafo + PDF) | Tiene que poder verificarlo en 10 segundos |
| Pocos resultados buenos antes que muchos regulares | Su tiempo es lo más caro |
| El caso del cliente no se guarda más allá de la sesión | Secreto profesional |
| "¿Sirvió?" en cada ficha | Cada clic alimenta el set de evaluación |

Maqueta visual de las pantallas: [Flujo LITIGIA v2](https://claude.ai/artifact/W1W1wUnQc8TEuAiBtGXRc8).

---

## 3. Por dónde empezar, y por qué

**Primero se ataca el riesgo más grande, no la parte más fácil.**

| Riesgo | Tamaño | Qué pasa si falla | Cuándo lo probamos |
|---|---|---|---|
| **Jev no rinde en castellano jurídico.** La documentación dice que el inglés es su idioma principal y que otros idiomas "funcionan, pero no igual de bien". | 🔴 Máximo: todo el etiquetado depende de esto | Cambiar de etiquetador (Haiku, un modelo local) y recalcular costos | **Fase 1, primero que nada** |
| Las preguntas del mapa no se pueden contestar con los fallos | 🟠 Alto | Etiquetas vacías o poco útiles | Fase 2 |
| La búsqueda no encuentra el fallo correcto con casos reales | 🟠 Alto | El producto no sirve aunque los datos estén bien | Fase 5 |
| El sitio del PJN cambia o nos bloquea | 🟡 Medio | Se frena el volumen | Fase 4, con monitoreo |
| Los abogados no lo usan | 🟡 Medio | Producto sin mercado | Fase 6 (piloto) |

Por eso el orden: **probar Jev (1) → mapa (2) → medir el etiquetador (3) → volumen (4) → búsqueda (5) → piloto (6) → job diario (7).** Construir el volumen o la interfaz antes de saber si el etiquetado funciona sería construir la casa antes de probar el suelo.

---

## 4. Principios que aplican a todas las fases

1. **Un paso a la vez.** No se arranca el siguiente hasta cumplir el criterio de salida del actual.
2. **Todo se mide contra datos,** nunca contra lo que dice un proveedor o nuestra intuición.
3. **Todo es reversible:** deshabilitar en vez de borrar, versionar el mapa y el etiquetador, reetiquetar sin volver a scrapear.
4. **TDD** en todo el código, con fallos reales como fixtures.
5. **Costos visibles:** cada corrida registra tokens y dólares.
6. **Las etiquetas no fluctúan:** mapa congelado, etiquetado una sola vez, umbral de certeza, modelo con versión fijada (ver README, "Estabilidad").

---

## 5. Fases, pasos y subpasos

### Fase 0 — Base de datos confiable ✅ HECHA

Scraper PJN (filtro `tid`, paginación con token, crawl adaptativo, partición por Sala), contrato de calidad, catálogo SQLite en modo WAL con deshabilitado, enriquecimiento por regex (objeto, resultado, normas, votos, N° de sentencia) y auditoría con delta. 71 tests.

---

### Fase 1 — Probar Jev en castellano jurídico (riesgo #1) ✅ HECHA (2026-09-27)

**Resultado:** Jev cumple el criterio de salida en las 6 preguntas del fallo y en el rol de cada párrafo, con tres ajustes: preguntas más literales, **estructura de votos calculada en código** (sin el voto en minoría en el `state`) y **consenso de 3 corridas**. Es mejor y 27 veces más barato que Haiku. El costo queda en ~$71 por 60.000 fallos (la meta era $50). Detalle completo: [FASE1_JEV_REPORT.md](FASE1_JEV_REPORT.md). **Pendiente:** revisión humana del set de verdad de 30 fallos (~1 hora).

Plan original de la fase (referencia):

**Objetivo:** saber, con números, si Jev sirve para etiquetar nuestros fallos. Es un spike: código descartable, conclusión que no se descarta.

| # | Subpaso | Detalle |
|---|---|---|
| 1.1 | Cuenta y acceso | Crear la cuenta, generar la API key en `console.typesafe.ai/keys`, guardarla como `TYPESAFE_API_KEY` en `backend/.env`. `pip install typesafe-sdk`. Probar `GET /v1/models`. |
| 1.2 | Fijar la versión | Usar `jev-1.13.0`, no el alias `jev-latest`, y registrar el campo `model` de cada respuesta. |
| 1.3 | Primer contacto en el Playground | Pegar 3 fallos reales y hacer las preguntas universales a mano. Mirar si las respuestas tienen sentido antes de escribir código. |
| 1.4 | Mini set de verdad: 30 fallos | Muestra estratificada: 10 despido, 10 accidente ley especial, 7 recurso Ley 27.348, 3 de otros tipos. Yo los preetiqueto; vos (o un abogado) revisás. Preguntas: tipo de caso · quién apeló · a favor de quién resultó · costas · párrafo del holding. |
| 1.5 | Adaptador mínimo | Script que arma el `state` (metadatos + párrafos numerados) y manda **todas las preguntas universales en una sola llamada** (la documentación indica que es ~12 veces más barato). |
| 1.6 | Precisión por pregunta | % de aciertos contra el mini set, pregunta por pregunta. |
| 1.7 | Calibración | Agrupar las respuestas por nivel de confianza y comparar: ¿las de 0,9 aciertan ~90%? |
| 1.8 | Consistencia | 5 corridas del mismo fallo con un campo `uid` nuevo en cada una (como el cookbook de TypeSafe). % de respuestas que no cambian, con y sin umbral. |
| 1.9 | Variantes que conviene comparar | a) instrucciones en castellano vs. en inglés (el fallo siempre en castellano); b) fallo completo vs. solo los párrafos relevantes (la documentación advierte que el texto irrelevante le baja la precisión). |
| 1.10 | Comparación | Mismas preguntas con Haiku 4.5 con salida estructurada, sobre los mismos 30 fallos. |
| 1.11 | Costo y latencia | Tokens por fallo, $ por fallo, segundos por llamada, proyectado a 60.000 fallos. |
| 1.12 | Análisis de errores | Clasificar cada error: falta de evidencia en el texto / pregunta mal formulada / error del modelo / error de código / falla del servicio. |

**Cómo sabemos que vamos bien:** después de 1.3 las respuestas del Playground tienen sentido; después de 1.6 tenemos números por pregunta.

**Criterio de salida (metas iniciales, ajustables):**
- Tipo de caso, quién apeló y resultado: **≥ 90% de aciertos** en las respuestas por encima del umbral, **y ≥ 70%** de los fallos por encima del umbral.
- Consistencia con umbral: **≥ 98%**.
- Costo proyectado para 60.000 fallos: **< $50**.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| No conseguimos acceso a la API | Arrancamos la Fase 2 (no depende de Jev) y usamos Haiku como etiquetador provisorio |
| Jev falla en castellano en alguna pregunta | Probamos instrucciones en inglés, criterios más detallados y dividir la pregunta en dos más literales |
| Jev falla en general | **Plan B:** Haiku o Sonnet con salida estructurada detrás de la misma interfaz (~$25–30 por pasada completa). **Plan C:** modelo local (Qwen) en tu GPU. |
| Aciertos buenos pero consistencia baja | Subir el umbral y aceptar más "sin determinar" |
| Fallos más largos que el contexto (32K tokens) | Mandar solo los párrafos relevantes, preseleccionados con regex o búsqueda |

---

### Fase 2 — Mapa de preguntas de la Cámara del Trabajo

**Objetivo:** el archivo `labels/cnat_v1.yaml` con los tipos de caso y las preguntas cerradas de cada uno.

| # | Subpaso | Detalle |
|---|---|---|
| 2.1 | Familias de caso | Agrupar los objetos de juicio de la CNAT (25 en la muestra) en familias. Ampliar la muestra para ver objetos raros (ver 4.1). |
| 2.2 | Extraer agravios | Código que detecta los párrafos de agravio (*"se agravia la demandada porque…"*) y los guarda por familia. |
| 2.3 | Contar temas de agravio | Agrupar y contar: *"despido: 60% discute la justa causa, 35% la multa del art. 80…"*. |
| 2.4 | Investigar fuentes | Leyes comentadas, doctrina, criterios y actas de la CNAT, publicaciones de colegios de abogados: qué se discute en cada familia. Con registro de fuentes. |
| 2.5a | Incorporar lo aprendido en la Fase 1 | Reglas pedidas por los etiquetadores: intereses, recursos desiertos, tipo según lo que resuelve la Cámara, costas mixtas, roles nuevos (`propuesta_voto`, `concurrencia`, `voto_con_reservas`). Ver la sección 7 del reporte de la Fase 1. |
| 2.5 | Redactar las preguntas (Claude) | Preguntas universales + específicas por familia. Cada una con: tipo (Choice / Noul / Score), instrucción literal, opciones con definición y una opción "no tratado / no aplica". Aplicando las reglas de Jev: condición exacta, casos límite en los criterios, sin números ni fechas. |
| 2.6 | Medir cobertura | ¿En qué % de los fallos de la familia aparece el tema? Si es muy bajo, la pregunta se descarta. |
| 2.7 | Congelar | `cnat_v1.yaml` versionado en git, con tests que validan su estructura (≤ 255 opciones, opción de salida presente, ids únicos). |

**Cómo sabemos que vamos bien:** en 2.3 los temas más frecuentes coinciden con lo que un laboralista reconocería (tasa, RIPTE, incapacidad, multas, costas).

**Criterio de salida:** preguntas universales + específicas para las familias que cubren **≥ 95%** de los fallos de la CNAT.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| Los agravios no se detectan bien con regex | Detectarlos con una pregunta de Jev ("¿este párrafo es un agravio?"), que además ya es una etiqueta que necesitamos |
| Una familia tiene muy pocos fallos | Queda como "otro", solo con preguntas universales |
| Preguntas demasiado abstractas para Jev | Dividirlas en dos más literales y combinarlas en código |

---

### Fase 3 — Set de verdad y etiquetador medido

**Objetivo:** un etiquetador en producción cuyas etiquetas sabemos que son correctas, pregunta por pregunta.

| # | Subpaso | Detalle |
|---|---|---|
| 3.1 | Set de verdad: 100 fallos | 25 por familia principal. Preetiquetados por el sistema, corregidos a mano. Incluye los 30 de la Fase 1. |
| 3.2 | Interfaz de etiquetador | `Labeler` con backends intercambiables (Jev, Haiku). TDD con respuestas simuladas. |
| 3.3 | Tabla de etiquetas | En el catálogo: fallo · pregunta · respuesta · probabilidad · párrafo de respaldo · versión del mapa · versión del etiquetador · modelo que respondió. |
| 3.4 | Dos pasadas | Pasada 1 (tipo + universales) → el código elige el set → pasada 2 (específicas). Según la Fase 1: **estructura de votos en código** (`scripts/labeling/votes.py`), preguntas del fallo **sin el voto en minoría**, **consenso de 3 corridas**, y roles de párrafo en una llamada aparte. |
| 3.5 | Medición por pregunta | Precisión, calibración y consistencia (3 corridas) contra el set. Reporte automático. |
| 3.6 | Umbral por pregunta | Elegido con los datos: el más bajo que mantiene la precisión objetivo. |
| 3.7 | Cruce con regex | Donde hay dos fuentes (por ejemplo, el resultado), marcar las discrepancias para revisión. |
| 3.8 | Publicar solo lo que pasa | Las preguntas que no alcanzan el criterio quedan desactivadas en el mapa. |

**Criterio de salida:** cada pregunta publicada tiene **≥ 90% de aciertos** por encima de su umbral y **≥ 98% de consistencia**. Se publica el reporte.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| Una pregunta clave no pasa (por ejemplo, "a favor de quién") | Reformularla; dividirla ("¿apeló el actor?" + "¿se admitió su agravio?") y combinar en código |
| El set de verdad tiene errores | Doble revisión en los casos donde el etiquetador y el set discrepan |
| TypeSafe publica una versión nueva | Corre en sombra sobre el set; se cambia solo si mide igual o mejor |

---

### Fase 4 — Volumen: la Cámara del Trabajo 2022 a hoy

**Objetivo:** ~50.000 a 60.000 fallos scrapeados, con contrato, enriquecidos y etiquetados.

| # | Subpaso | Detalle |
|---|---|---|
| 4.1 | Prueba de un mes completo | Scrapear un mes y auditarlo (completitud, % indexable, errores) antes de escalar. |
| 4.2 | Arreglar la auditoría | No contar dos veces un día completado por Sala (hoy marca 97,3% cuando es 100%). |
| 4.3 | Actualizar `deploy_parallel.py` | Que despliegue el paquete completo, no un solo archivo. Probarlo con 1 VPS antes de usar 10. |
| 4.4 | Scrapear en paralelo | 2022 a hoy, una IP por rango de fechas. Monitoreo en vivo. |
| 4.5 | Reactivar los viejos | Volver a listar los 38.000 fallos viejos del PJN que caen en el rango; se reactivan solos sin bajar los PDFs de nuevo. |
| 4.6 | Etiquetar todo | Proceso por lotes, idempotente (no reetiqueta lo ya hecho), con registro de costos. |
| 4.7 | Auditoría final | Completitud por mes, % indexable, cobertura de cada etiqueta, % en "otro", alarmas de deriva. |

**Criterio de salida:** completitud ≥ 99% contra el sitio en todo el rango, **0 fallos sin etiquetar**, costo dentro de lo proyectado.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| El sitio cambia el HTML o el captcha | Los tests con fixtures fallan enseguida. Actualizar el parser con una página nueva guardada como fixture. |
| Nos bloquean una IP | Bajar la velocidad, rotar IPs, espaciar las búsquedas |
| Suben los errores de PDF | Pausar, investigar una muestra, reintentar con backoff |
| Se dispara el costo de etiquetado | Cortar el lote (idempotente, se retoma después) y revisar el tamaño del `state` |

---

### Fase 5 — Búsqueda

**Objetivo:** dada la consulta del formulario, devolver las fichas correctas. Primero como CLI o API, sin interfaz.

| # | Subpaso | Detalle |
|---|---|---|
| 5.1 | Índice por párrafo | Solo párrafos de fallos activos. BM25 (FTS5) + vectores bge-m3. Incremental, para que el job diario solo agregue lo nuevo. |
| 5.2 | Agrupar párrafos repetidos | "Criterio reiterado en N fallos": se muestra uno, con el contador. |
| 5.3 | Filtros por etiqueta | Fuero, tipo de caso, resultado, Sala, y excluir los párrafos que son agravio de parte. |
| 5.4 | Recuperación | Híbrido RRF + reranker local → top 30. |
| 5.5 | Juez final | Jev por par (consulta, candidato): ¿misma cuestión? ¿favorable a mi parte? ¿qué párrafo? Es el patrón del cookbook de reranking legal de TypeSafe. |
| 5.6 | Armar las fichas | Solo con datos existentes: metadatos, etiquetas, el párrafo literal. |
| 5.7 | Set de consultas reales | 30 consultas escritas como las escribe un abogado, con los fallos correctos marcados. |
| 5.8 | Medir | P@5, cobertura de los 30 primeros, latencia (< 10 s) y costo por consulta. |

**Criterio de salida:** **P@5 ≥ 0,8** en las consultas reales, **< 10 s** de latencia, **< $0,05** por consulta.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| El fallo correcto no entra en los 30 primeros | El problema es la recuperación, no el juez: revisar filtros, BM25 y vectores |
| Entra pero queda abajo | Ajustar las preguntas del juez; más contexto del caso en el `state` |
| Latencia alta | Paralelizar las llamadas al juez; reducir de 30 a 20 candidatos |

---

### Fase 6 — Interfaz y piloto con abogados

**Objetivo:** 2 o 3 laboralistas usándolo en causas reales durante 2 semanas.

| # | Subpaso | Detalle |
|---|---|---|
| 6.1 | Interfaz web mínima | Las dos pantallas de la maqueta. Sin cuentas complejas: acceso por invitación. |
| 6.2 | Privacidad | El caso del cliente no se guarda. Antes de mandarlo al juez se quitan los nombres propios. Revisar los términos de TypeSafe (la retención cero es solo para planes enterprise). |
| 6.3 | Registro | Consultas (anonimizadas), resultados mostrados, clics en "¿Sirvió?". |
| 6.4 | Piloto | 2 o 3 laboralistas, 2 semanas. Una charla corta al empezar y otra al terminar. |
| 6.5 | Iterar | Ajustar según el feedback: campos del formulario, orden de los resultados, etiquetas visibles. |

**Criterio de salida:** **≥ 70% de "sirvió"** en las fichas que abren, y los abogados lo quieren seguir usando.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| Buscan cosas que el formulario no permite | Registrar esos casos y evaluar un campo nuevo |
| "No encuentro lo que sé que existe" | Esa consulta entra al set de evaluación y se investiga como en la Fase 5 |
| No les sirven las etiquetas que mostramos | Mostrar menos; priorizar las que usan |

---

### Fase 7 — Job diario

**Objetivo:** que la base se mantenga al día sola.

| # | Subpaso | Detalle |
|---|---|---|
| 7.1 | Pipeline incremental | Scrapear los últimos 7 días (con solapamiento, porque los fallos se publican con demora) → contrato → enriquecer → etiquetar lo nuevo → indexar. |
| 7.2 | Programación | Tarea programada en el VPS (cron) o en Windows (Programador de tareas). |
| 7.3 | Auditoría diaria | Snapshot + delta + alarmas: completitud < 99%, errores > umbral, deriva de etiquetas, cero fallos nuevos en un día hábil. |
| 7.4 | Aviso | Mensaje (mail o Telegram) solo cuando algo falla. |
| 7.5 | Runbook | Qué hacer ante cada alarma. |

**Criterio de salida:** **7 días seguidos** sin intervención manual.

**Imprevistos:**

| Si pasa esto | Hacemos esto |
|---|---|
| El sitio no responde un día | El job reintenta al día siguiente con una ventana más amplia (el solapamiento lo cubre) |
| Falla el etiquetador | Los fallos quedan pendientes de etiquetar y se procesan en la próxima corrida; no se publican sin etiquetas |
| Alarma de deriva | Revisar una muestra antes de publicar ese lote |

---

## 6. Cronograma estimado

Estimaciones, no compromisos. Dependen sobre todo del acceso a Jev y de la disponibilidad de los abogados.

| Fase | Duración estimada | Puede solaparse con |
|---|---|---|
| 1 · Probar Jev | 1 semana | 2 |
| 2 · Mapa CNAT | 1 semana | 1 |
| 3 · Set de verdad + etiquetador | 1–2 semanas | 4.1 a 4.3 |
| 4 · Volumen | 1 semana | 3 |
| 5 · Búsqueda | 1–2 semanas | — |
| 6 · Interfaz + piloto | 3 semanas | 7 |
| 7 · Job diario | 1 semana | 6 |
| **Total hasta el MVP** | **~8 a 10 semanas** | |

## 7. Costos estimados hasta el MVP

| Rubro | Estimado | Base |
|---|---|---|
| Captchas (scraping) | < $1 | $0,006 cada 721 fallos |
| VPS en paralelo | ~$5 | Corrida anterior: $0,50 por 48.000 fallos en 10 VPS |
| Etiquetado con Jev (60.000 fallos) | **~$71** | **Medido en la Fase 1:** ~28.000 tokens por fallo (preguntas del fallo ×3 por consenso + rol de cada párrafo) a $0,042 por millón |
| ~~Plan B con Haiku~~ | ~~$355 por pasada~~ | No hace falta: Jev pasó la Fase 1 |
| Consultas del piloto | < $5 | ~$0,04 por consulta |
| **Total** | **~$85** (sigue por debajo de $100) | Sin contar horas de trabajo |

## 8. Qué necesito de vos

| Qué | Para qué fase | Bloquea |
|---|---|---|
| API key de TypeSafe (`console.typesafe.ai/keys`) | 1 | Fase 1 (sin esto seguimos con la 2 y Haiku) |
| Revisar el mini set de verdad (30 fallos, ~1 hora) | 1 | Criterio de salida de la Fase 1 |
| Revisar el set de verdad completo (100 fallos, ~3 horas) | 3 | Fase 3 |
| Presupuesto para VPS (~$5) y la API key de Vultr rotada | 4 | Fase 4 |
| 2 o 3 laboralistas para el piloto | 6 | Fase 6 (conviene buscarlos desde ya) |

## 9. Próximo paso concreto

La Fase 1 está hecha. Sigue la **Fase 2**: familias de caso y conteo de agravios (2.1–2.3), y la revisión humana del set de verdad de la Fase 1.
