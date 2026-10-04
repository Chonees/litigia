# LITIGIA — Plan hasta el MVP: el conector

Plan de ejecución en pasos chicos y en orden. Cada paso dice qué se hace, cuándo está terminado y qué hacemos si algo sale mal. El diseño general está en el [README](../README.md).

**Decisión (2026-09-29): el MVP es un conector MCP y nada más.** El abogado usa LITIGIA desde su propio asistente de IA (Claude, ChatGPT, Grok o Gemini). La app web, la app de celular y cualquier interfaz propia quedan para después del MVP.

Estado de partida (2026-09-29):
- **Datos:** 22.470 sentencias definitivas de la Cámara Nacional del Trabajo (un año, 99,3% de lo que informa el sitio). Los otros cuatro fueros nacionales de CABA se están bajando: seguridad social, contencioso administrativo federal, civil y comercial (~56.500 fallos).
- **Scraper con contabilidad:** sabemos qué informó el sitio, qué se guardó y qué falló, fallo por fallo.
- **Jev probado** en castellano jurídico (Fase 1, [reporte](FASE1_JEV_REPORT.md)).
- 139 tests.

Estado al 2026-10-04:
- **Datos cerrados (Fases 0 a 2):** 78.933 sentencias de los 5 fueros, 77.546 aptas, auditadas en 4 capas. La última capa compara con 311 notas escritas por personas.
- **El examen del buscador está listo (3.6):** 311 fallos conocidos y 100 consultas de doctrina ([BENCHMARK.md](BENCHMARK.md)).
- 200 tests.
- **Sigue:** construir el buscador (3.1 a 3.5).

---

## 1. Qué es el MVP

**En una frase:** un abogado litigante agrega LITIGIA como conector en su asistente de IA, le cuenta su caso con sus palabras, y recibe los fallos que resolvieron su misma cuestión: separados en a favor y en contra, con cómo resuelve su Sala ese punto y el párrafo literal para citar.

> **"Tu asistente redacta; LITIGIA pone las balas."**

| Entra en el MVP | Queda afuera (después del MVP) |
|---|---|
| **Conector MCP remoto** para Claude (primero), ChatGPT, Grok y Gemini | App web, app de celular (Capacitor), cualquier pantalla propia |
| Justicia nacional de CABA, 5 fueros: laboral, seguridad social, contencioso administrativo federal, civil y comercial | Provincias, Corte Suprema, interlocutorias, legislación |
| Sentencias definitivas del último año, más la carga diaria de lo nuevo | Años anteriores |
| Búsqueda por párrafo y filtros; después etiquetas y tendencia por Sala | Redactar escritos: lo hace el asistente del abogado |
| Acceso por usuario con límites de uso | Cobro automático y planes (se abre después del piloto) |
| Prueba de punta a punta con las consultas del benchmark | **Piloto con abogados reales** y lanzamiento público |

**Qué pone cada uno:**

| El asistente del abogado (su infraestructura, su suscripción) | LITIGIA (nuestra API) |
|---|---|
| Conversación, voz y app de celular | ~79.000 fallos completos y contabilizados |
| Leer la sentencia o la demanda que el abogado adjunta al chat | Búsqueda por párrafo, etiquetas y tendencia por Sala |
| Redactar, resumir, corregir y comparar escritos, citando lo que devuelve LITIGIA | El párrafo literal que decidió la mayoría, con el link al PDF oficial |

Así, funciones que otras herramientas construyeron a mano (redactar, voz, celular, subir documentos) le llegan al abogado hechas, y el foco del MVP queda en lo que nadie más tiene. Después de la v1, el conector puede sumar **plantillas de pedidos** del estándar MCP (por ejemplo, "Armar agravios con jurisprudencia de mi Sala"). Lo esencial tiene que funcionar solo con herramientas, porque cada asistente soporta el estándar de forma distinta.

**Por qué el conector primero:**
- **No hay que construir interfaz.** La pone el asistente, que además entiende el relato del abogado y redacta el escrito con nuestras citas.
- **Llegamos adonde el abogado ya trabaja.** Muchos ya usan ChatGPT o Claude todos los días.
- **No pagamos la IA de conversación:** la paga la suscripción del abogado. Nosotros ponemos lo único que su asistente no tiene: los fallos completos, etiquetados y contabilizados.
- **Es el camino más corto** a tener abogados usándolo y midiendo si las balas sirven.

---

## 2. Cómo lo usa el abogado

1. **Agrega el conector una sola vez.** En Claude: Personalizar → Conectores → "+", pega la URL de LITIGIA e inicia sesión. Funciona también en la app de celular de Claude, pero el conector se agrega desde la web.
2. **Cuenta su caso en el chat:**
   > *"Represento a una jubilada. Ganó el reajuste, ANSES apeló los topes del art. 9 de la ley 24.463 y las costas. Nos tocó la Sala 1. Buscame fallos a favor y en contra, y cómo resuelve la Sala."*
3. **Su asistente llama a las herramientas de LITIGIA** con los datos del caso.
4. **LITIGIA devuelve fichas:** fallo, Sala, fecha, qué resolvió en ese punto, el párrafo literal y el link al PDF oficial. Con la v2, además, cómo resuelve ese punto cada Sala y con cuántos fallos.
5. **Si el abogado lo pide, su asistente redacta** el agravio o el escrito usando esas citas.

---

## 3. Las herramientas del conector

| Herramienta | Qué recibe | Qué devuelve | Versión |
|---|---|---|---|
| `buscar_fallos` | Fuero, cuestión en texto, hechos clave, a quién representa; opcionales: Sala, fechas | Hasta 10 fichas, con Sala, fecha, carátula, expediente, resultado, párrafo literal y link al PDF. Desde v1, separadas en a favor y en contra | v0 |
| `ver_fallo` | Id del fallo | El fallo completo para que el asistente del abogado lo lea y responda repreguntas: metadatos, votos, normas citadas y el texto limpio en párrafos numerados (verificado contra el PDF), más el enlace al PDF oficial como recurso MCP | v0 |
| `citar` | Id del fallo y párrafo | La cita lista para pegar en un escrito, con el formato del fuero | v0 |
| `buscar_en_fallo` | Id del fallo y una pregunta en texto ("¿qué tasa aplicó?") | Los 3 o 4 párrafos de ese fallo que la responden, numerados y con su rol. Para las repreguntas del abogado sobre un resultado, sin mandarle el fallo entero a su asistente | v0 |
| `preguntas_del_caso` | Fuero y tipo de caso | Los datos que hacen falta para afinar la búsqueda, con una línea de por qué importa cada uno. Sale del mapa de preguntas | v1 |
| `tendencia_sala` | Fuero, punto en discusión y Sala (opcional) | Cómo resuelve cada Sala ese punto, con cantidad de fallos y un ejemplo citable de cada criterio | v2 |

**Reglas de las respuestas:**
- **JSON estructurado:** cada herramienta declara su `outputSchema` y responde con `structuredContent` (estándar MCP 2025-06-18), repitiendo el mismo JSON como texto para los asistentes que no leen el campo estructurado. Cada ficha trae el rol del párrafo, la certeza, la cita lista y el link al PDF oficial. La v1 agrega campos a la v0 sin cambiar los existentes.
- **LITIGIA nunca genera texto jurídico.** Devuelve datos del fallo y párrafos literales, siempre con el link al PDF oficial.
- **Cada herramienta avisa en su descripción** que las citas se reproducen tal cual y que el abogado debe verificarlas en la fuente. El asistente externo redacta; nosotros no controlamos ese texto, y el abogado tiene que saberlo.
- **Si no hay fallos con certeza suficiente, se dice.** No se rellena con resultados dudosos.
- **Cada búsqueda dice cuánto respaldo tiene:** `precedentes_disponibles` para ese tipo de caso. Hay tipos con muy pocos fallos definitivos publicados (familia: ~115 por año; concursos: ~35; sociedades: ~1), y el abogado tiene que saberlo.
- **Lo que no sabemos, también se dice:** cada ficha trae `"vigencia": "no verificada"` mientras no tengamos los fallos de la Corte ni la cadena de recursos, para que el asistente no afirme que un fallo quedó firme.
- **Preguntas sobre muchos fallos** ("¿en cuántos casos…?", "¿cuánto se otorga por…?") solo se responden con herramientas que cuentan sobre la base etiquetada (`tendencia_sala`, y más adelante montos otorgados como etiqueta del mapa). El asistente no puede leer miles de fallos por su cuenta.
- **Solo lo que decidió la mayoría.** Nunca se devuelve como decisión un párrafo que es una queja de parte, una cita del juez anterior o un voto en minoría (desde v1).

---

## 4. Principios

1. **Un paso a la vez**, y no se arranca el siguiente sin cumplir el criterio del actual.
2. **Todo se mide contra datos:** contabilidad del scraper, auditorías y consultas reales.
3. **Reversible:** nada se borra (se deshabilita), las etiquetas tienen versión y se pueden rehacer sin volver a scrapear.
4. **TDD** en todo el código, con fallos reales como fixtures.
5. **Costos visibles:** cada corrida registra tokens y dólares.
6. **Respeto por el sitio del PJN:** como máximo 1 o 2 pedidos por segundo por IP. El bloqueo del 28/09 fue por ir a 40.

---

## 5. Fases

### Fase 0 — Datos confiables ✅
Scraper del PJN con partición por fecha, por tipo de oficina, por oficina y por año del expediente; contrato de calidad; catálogo; enriquecimiento por reglas; contabilidad fallo por fallo (`scripts/reconcile.py`); deploy en VPS paralelas con collect automático.

### Fase 1 — Jev en castellano jurídico ✅
Cumple el criterio en las 6 preguntas del fallo y en el rol de cada párrafo, con consenso de 3 corridas y la estructura de votos calculada en código. ~US$71 cada 60.000 fallos laborales.

**Falta validarlo contra personas.** El set de 30 lo etiquetó Claude. Las 311 notas del benchmark dicen qué decidió el tribunal y quién ganó, así que sirven de ancla humana para el resultado principal de Jev, sin costo extra y en los 5 fueros:
- **Primera prueba:** los 96 fallos laborales con nota (≈ US$0,15).
- **Lo que las notas no cubren**, el rol de cada párrafo, lo revisa una persona sobre una muestra chica (≈ 1 hora).

### Fase 2 — Cerrar el año de los 5 fueros ✅ HECHA (2026-09-30)

**Resultado:** 78.933 de 79.112 sentencias que informa el sitio (99,8%), 77.546 aptas para búsqueda. La prueba de cobertura con la prensa encontró 22 fallos guardados pero escondidos: una copia vieja desactivada que la fusión de las VPS no completaba. Se corrigió y la conciliación ahora los cuenta aparte. Test de calidad en 4 capas en los 5 fueros, la última contra 311 notas escritas por personas: chequeos cruzados ≥ 97%, 250/250 PDFs idénticos al texto guardado, y extracción a ciegas con instancia, Sala, primer voto y número al 100%. Detalle: [CALIDAD_DATOS.md](CALIDAD_DATOS.md). Quedan como pendientes 102 fallos del laboral (reintento cortado), 53 que el sitio nunca lista y 24 PDFs vacíos.

Plan original de la fase (referencia):
| # | Subpaso |
|---|---|
| 2.1 | Terminar las 20 VPS, traer todo y **apagarlas** |
| 2.2 | Reaplicar las reglas nuevas a todo el catálogo: resultado, votos, normas del CCyC y el CPCCN, rechazos formales corregidos |
| 2.3 | Conciliación de cada fuero; reintentar los días incompletos y los PDFs fallidos, despacio |
| 2.4 | Test de calidad en 3 capas por fuero, como el del laboral ([CALIDAD_DATOS.md](CALIDAD_DATOS.md)) |
| 2.5 | Arreglar la extracción de votos que junta dos jueces en un nombre |
| 2.6 | **Copia de seguridad del catálogo** fuera del disco D |
| 2.7 | Commit y push |

**Criterio de salida:** cada fuero con ≥ 98% de lo que informa el sitio guardado (o la diferencia explicada fallo por fallo), sin días sin cubrir, y con su test de calidad publicado.

### Fase 3 — Motor de búsqueda y API
| # | Subpaso |
|---|---|
| 3.1 | Índice por párrafo de los fallos activos: BM25 (SQLite FTS5) más vectores. Decidir entre **bge-m3 local (con GPU) o una API de embeddings**, midiendo costo y tiempo sobre ~3 millones de párrafos |
| 3.2 | Filtros con lo que ya existe: fuero, instancia, Sala, fechas, resultado, normas, tipo de caso (objeto) |
| 3.3 | Recuperación híbrida (RRF) y reranker local; devolver el mejor párrafo de cada fallo |
| 3.4 | Agrupar párrafos repetidos: "criterio reiterado en N fallos" |
| 3.5 | API interna con `buscar_fallos`, `ver_fallo` y `citar` |
| 3.6 ✅ | **Benchmark de búsqueda desde fuentes públicas, sin depender de abogados** ([BENCHMARK.md](BENCHMARK.md)). **Hecho:** 311 fallos conocidos y 100 consultas de doctrina, dev 30% y test 70% congelados. Las partes: (a) **fallos conocidos**: notas, boletines y comentarios publicados por terceros que describen un caso y citan el fallo que lo resolvió; la consulta sale de esa descripción y la respuesta correcta la puso el autor, no nosotros; (b) **consultas de doctrina**: las cuestiones que discuten los manuales y la doctrina por tipo de caso, con una regla de relevancia escrita antes de ver resultados. P@5 y recall se miden **por tipo de caso** |
| 3.6b ✅ | **Reglas para que no se pueda "arreglar":** quien escribe la consulta no ve nuestra base; la consulta queda congelada antes de buscar el fallo; los resultados se juzgan a ciegas, mezclando los nuestros con los de una búsqueda simple por palabras; set de desarrollo y set de prueba congelado; siempre contra esa base de comparación; se informa el tamaño de cada muestra y cada error. El benchmark viejo del README (8 consultas nuestras, criterio flojo) es solo una señal. Las pruebas con abogados (casos propios y fallos que citaron) van después del MVP |
| 3.7 | **¿Hace falta un juez por consulta?** Medir sobre el set: A = búsqueda + reordenador local; B = A + Jev sobre los 10 primeros. Si B no mejora P@5 de forma clara, el juez queda apagado: en MCP, el asistente del abogado ya lee y elige entre los resultados. Lo que más importa es que el fallo correcto entre en los 10 primeros |

**Requisito de costo: la consulta no llama a un LLM por defecto.** Lo caro se hace una vez por fallo, al etiquetar. En la consulta: filtros, búsqueda y reordenamiento en nuestro servidor; lo ambiguo lo decide el asistente del abogado, que lee los resultados. Jev en la consulta queda como opción para preguntas que no encajan con el mapa o para resultados dudosos, siempre con pocos candidatos (≤ 10), una sola pasada y caché. Así el costo por consulta es casi solo servidor, y el margen se sostiene aun con usuarios muy intensivos.

**Criterio de salida:** P@5 ≥ 0,6 en v0 (sin etiquetas) sobre el set de consultas, y menos de 3 segundos por búsqueda.

### Fase 4 — Conector MCP v0
| # | Subpaso |
|---|---|
| 4.1 | Servidor MCP remoto (HTTPS) sobre la API de la Fase 3, en una VPS chica con dominio propio |
| 4.2 | Acceso por usuario: una credencial por persona (el login completo con OAuth va en la Fase 9) |
| 4.3 | Límites: consultas por minuto y por día por usuario, máximo 10 resultados por consulta, alertas de uso anormal |
| 4.4 | Registro anonimizado de las consultas: qué preguntan y qué fichas abren. Alimenta el mapa de preguntas y el set de evaluación |
| 4.5 | Probarlo en Claude web y celular, ChatGPT (modo desarrollador) y Grok |
| 4.6 | Guía de instalación en 2 pasos para abogados no técnicos |
| 4.7 | Prueba de punta a punta en Claude con las consultas del benchmark, como las haría un abogado |

**Criterio de salida:** el conector responde las consultas del benchmark en Claude, ChatGPT y Grok con el mismo P@5 que la API, y el asistente cita los párrafos sin alterarlos. **El piloto con abogados reales va después del MVP.**

### Fase 5 — Mapa de preguntas por fuero
Se alimenta de lo que preguntan los usuarios del conector (registro anonimizado, 4.4), de la investigación por fuero y de las 100 consultas de doctrina del benchmark.

| # | Subpaso |
|---|---|
| 5.1 | Familias de caso por fuero, a partir del objeto de juicio (el 94% del laboral está en 4 tipos) |
| 5.2 | Extraer y contar los agravios por familia |
| 5.3 | Sumar lo que preguntan los usuarios del conector y lo que salió de la investigación por fuero y del benchmark |
| 5.4 | Redactar las preguntas cerradas (Claude + código): condición literal, opciones con definición y "no aplica" |
| 5.5 | Congelar con versión y tests: `labels/<fuero>_v1.yaml` |

Orden de fueros: **laboral y seguridad social primero** (los de más volumen), después contencioso, civil y comercial.

**Criterio de salida:** preguntas para las familias que cubren ≥ 95% de los fallos de cada fuero.

### Fase 6 — Etiquetado medido y conector v1
| # | Subpaso |
|---|---|
| 6.1 | Set de verdad por fuero (~100 fallos), anclado en las notas de terceros (qué decidió y quién ganó) y revisado por una persona |
| 6.2 | Etiquetar con Jev: consenso de 3 corridas, votos por código, umbral por pregunta |
| 6.3 | Medir precisión y consistencia pregunta por pregunta; las que no pasan no se publican |
| 6.4 | Etiquetar todos los fallos, de forma idempotente y registrando el costo |
| 6.5 | **Conector v1:** a favor y en contra, quién ganó cada punto, el hecho clave, solo el párrafo de la mayoría, y la herramienta `preguntas_del_caso` |

**Criterio de salida:** cada pregunta publicada con ≥ 90% de acierto por encima de su umbral y ≥ 98% de consistencia. P@5 ≥ 0,8 en el set de consultas.

### Fase 7 — Tendencia por Sala y conector v2
Contar, por Sala, cómo se resolvió cada pregunta del mapa, con un mínimo de fallos para mostrar una tendencia y un ejemplo citable de cada criterio. Herramienta `tendencia_sala`.

**Criterio de salida:** tendencias verificadas a mano en 10 puntos contra los fallos que las respaldan.

### Fase 8 — Carga diaria
Scrapear los últimos 7 días (se publican con demora), aplicar el contrato, enriquecer, etiquetar solo lo nuevo, indexar y conciliar. Alertas solo cuando algo falla. A 1 o 2 pedidos por segundo.

**Criterio de salida:** 7 días seguidos sin intervención manual.

### Fase 9 — Cuentas y cobro
Login OAuth en el conector, planes, pago en nuestra web (sin comisión de las plataformas) y una sola suscripción que después sirva también para la app. Controles contra cuentas compartidas y contra copia masiva de la base.

---

## 6. Metas y cómo se miden

| Meta | Cómo se mide |
|---|---|
| Datos completos | Conciliación contra el sitio: ≥ 98% guardado por fuero |
| Búsqueda precisa | Sobre el benchmark: fallos conocidos en los 10 primeros y P@5 de doctrina ≥ 0,6 en v0 y ≥ 0,8 en v1, siempre contra la búsqueda por palabras |
| Etiquetas confiables | ≥ 90% de acierto y ≥ 98% de consistencia por pregunta |
| Rápido | < 3 s por búsqueda en v0; < 10 s con el juez de Jev en v1 |
| Barato | < US$0,001 por consulta en LLM (sin juez por defecto); el resto es servidor |
| Útil | En el piloto con abogados, después del MVP: ≥ 50% de consultas útiles en v0 y ≥ 70% en v1 |

---

## 7. Costos estimados

| Rubro | Estimado |
|---|---|
| Scraping del año de los 5 fueros | < US$3 (VPS y captchas) |
| Servidor del conector | US$5 a 10 por mes |
| Etiquetado con Jev de ~79.000 fallos | ~US$95 a 150 (los fallos civiles son 2,5 veces más largos que los laborales) |
| Vectores para la búsqueda | $0 con GPU local, o a medir con API |
| Consultas del piloto | < US$5 |

---

## 8. Qué necesito de vos

| Qué | Para qué fase |
|---|---|
| **Dominio** para el conector (por ejemplo, un subdominio `mcp.` del dominio de LITIGIA) | 4 |
| Revisar a mano una muestra de los juicios de agentes (gold ciego, roles de párrafo) | 1 y 6 |
| **2 o 3 abogados** para el piloto, idealmente laboral y previsional | Después del MVP |
| Pagar el saldo de Vultr y rotar la key | Ya |

---

## 9. Después del MVP

- **App web y app de celular con Capacitor**, con la misma API y la misma suscripción.
- **Subir la sentencia de primera instancia o la demanda:** el sistema la lee con el mapa de preguntas y busca fallos para cada agravio.
- **Más cobertura:** Corte Suprema, provincias (empezando por Buenos Aires), interlocutorias, años anteriores.
- **Avisar si un fallo quedó superado** (revocado, plenario o ley nueva).

---

## 10. Próximo paso concreto

**Fase 3.1:** el índice por párrafo de los fallos activos:
- BM25 con SQLite FTS5, más vectores.
- Primero se mide sobre una muestra cuánto cuesta y cuánto tarda vectorizar ~3 millones de párrafos, con bge-m3 en la GPU local o con una API de embeddings.
- Con el índice armado, se corre el benchmark en dev contra la búsqueda por palabras.
