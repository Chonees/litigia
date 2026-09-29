# Calidad real de los datos — CNAT, 12 meses

Fecha: 2026-09-28 · Alcance: 22.464 fallos de la Cámara Nacional del Trabajo (17.037 de Cámara y 5.427 de primera instancia), del 27/09/2025 al 27/09/2026, sentencias definitivas.

La auditoría común mide **cobertura** (si un campo existe). Este test mide **exactitud** (si el valor es correcto) en tres capas.

## Resumen

| Capa | Qué mide | Resultado |
|---|---|---|
| 1. Chequeos cruzados (22.464 fallos) | Que cada metadato sea consistente con el texto del propio fallo | **≥ 99% en todos los campos.** Lo que queda es mayormente del propio PJN |
| 2. Fidelidad del texto (50 PDFs bajados de nuevo) | Que el texto guardado sea el del PDF | **50/50 idénticos.** La limpieza quitaba tablas numéricas (0,4% de las palabras); **corregido y reprocesado: 2.242 fallos recuperaron sus tablas** |
| 3. Exactitud del enriquecimiento (extracción ciega) | Que los campos extraídos sean correctos | **Muestra nueva: 100% en instancia, resultado, votos y número.** Sala: ver nota |

## Capa 1 — Chequeos cruzados contra el texto

`python -m spikes.quality_check --desde 2025-09-27 --hasta 2026-09-27`

| Chequeo | OK | Qué son los que fallan |
|---|---|---|
| El expediente no está contradicho por el encabezado | 99,0% | **Del PJN:** el número del sistema y el que escribió el juzgado difieren (año o un dígito). Ej.: 46676/**2019** contra 46676/**2016** |
| Parte de la carátula aparece en el texto | 99,5% | Nombres cortados o con errores de tipeo en la fuente |
| Fecha dentro del rango | 100% | — |
| Fecha en día hábil | 99,7% | **Del PJN:** registra un sábado (28/02) cuando el fallo dice 27/02 |
| Texto completo (termina en resolutivo o firma) | 99,7% | Falsos positivos: terminan en "Conste." o en honorarios |
| Texto legible | 100% | — |
| Primera instancia es realmente de primera instancia | 100% | — |
| La Sala no está contradicha por el texto | 99,9% | Sala de Feria que resuelve una causa de otra Sala (correcto) |
| Cada juez que vota también firma | 99,3% | Jueces que votan y no firman, o errores de tipeo en el fallo ("Mauata" contra "Manauta") |
| Duplicados por expediente y fecha | 1 caso | — |

El expediente aparece literalmente en el texto en el 89,7% de los casos, y la Sala en el 91,1%. En el resto el fallo no los repite; el dato viene del sistema del PJN y el texto no lo contradice.

## Capa 2 — Fidelidad del texto

`python -m spikes.text_fidelity --n 50`

- **50 de 50 PDFs bajados de nuevo dieron exactamente el mismo texto guardado.** No hay corrupción al guardar ni al juntar las VPS.
- Palabra por palabra contra el PDF crudo, la limpieza quita sellos de página, firmas y encabezados repetidos, que es lo buscado. Del **cuerpo** del fallo se perdía un 0,39%, concentrado en **tablas numéricas**. Caso real: la tabla del ingreso base mensual, con el total **$11.888.158,60**, en un recurso Ley 27.348 contra Galeno ART.
- **Corregido:** solo se descartan fragmentos numéricos del tamaño de un número de página (≤ 8 caracteres). Test con las filas reales.
- **Reprocesado (28/09):** se volvieron a bajar los 23.416 PDFs activos (`spikes/reprocess_pdfs.py`, ~10 min, 0 fallos; esa velocidad provocó el bloqueo de la IP, ver Pendientes). **En 2.242 (9,6%) el texto cambió**: recuperaron tablas de montos, fechas y liquidaciones. Los metadatos no se tocaron.
- Después del reprocesado, la capa 1 dio los mismos porcentajes: no hubo regresiones.
- La auditoría ya no cuenta como ruido las líneas numéricas largas (son filas de tabla); solo los números de página sueltos, que quedaron en **0**. Queda ruido residual de firmas en 19 fallos y sellos de página en 4 (0,1%).

## Capa 3 — Exactitud del enriquecimiento

Agentes independientes leyeron cada fallo completo y extrajeron los campos **a ciegas**: sin ver nuestros valores ni los metadatos del sitio (`spikes/show_text.py` muestra solo el texto).

| Campo | 60 fallos iniciales (antes) | Los mismos 60, después de corregir | **30 fallos nuevos (muestra nunca vista)** |
|---|---|---|---|
| Instancia | 100% | 100% | **100%** |
| Resultado | 91,7% | 98,3% | **100%** |
| Votos | 90,0% | 100% | 85% → **100%**¹ |
| Número de sentencia | 70,0% | 96,7% | **100%** |
| Sala | 92,5%² | 92,5%² | 90,0%² |

¹ En la muestra nueva aparecieron dos formatos de encabezado de voto que no conocíamos ("HOCKL, dijo:" y "Pesino dijo Por…"). Se corrigieron con test, así que el 100% final de votos también está medido sobre fallos que ya vimos.
² Los "errores" de Sala no son nuestros: el texto no nombra la Sala y el extractor ciego no la puede saber. Nuestro dato viene del sistema del PJN; los agentes mismos dicen "por los jueces sería la III".

Correcciones aplicadas, todas con test (106 tests en total):
- Número de sentencia de primera instancia ("SENTENCIA NÚMERO: 18867"), sin confundirlo con el expediente ("31748/2021") ni con códigos de Sala ("SENT.DEF. 2-3").
- Votos encabezados con "manifestó:", con coma antes de "dijo" o sin los dos puntos. Una cita dentro del razonamiento ("el Dr. Pérez dijo que…") no cuenta como voto.
- Resultado: "Haciendo lugar", "condeno", "Declarar mal concedido" y "Dejar sin efecto".
- Sala de Feria.

## Casos donde "correcto" es discutible

Los extractores marcaron zonas grises reales, que ninguna regla resuelve sola:
- "**Confirmar** … con la salvedad de los intereses": ¿confirma o modifica?
- En primera instancia, Ley 27.348: "**Revocar** lo resuelto por la Comisión Médica y condenar a la ART": ¿revoca o hace lugar?
- "Declarar la inconstitucionalidad…" como primer punto.

Hoy se etiqueta por el primer verbo del resolutivo. Para el abogado, lo que importa es **a favor de quién**, y eso lo decide el etiquetado de la Fase 1 (agravios por parte), no esta regex.

## Expediente tal como lo escribe el fallo

Nuevo campo `expediente_texto`, leído del encabezado del fallo (normalizado: "46676/2016"). Está en **20.353 de 23.416 fallos (87%)**; en el resto el encabezado no lo repite. Cuando difiere del número del sistema del PJN (número o año), el fallo lleva la advertencia `expediente_no_coincide`: **180 fallos (0,9%)**. El buscador puede mostrar los dos.

## Auditoría final (28/09)

`python -m spikes.audit_batch --desde 2025-09-27 --hasta 2026-09-27`

| | Cámara | Primera instancia |
|---|---|---|
| Fallos | 17.041 | 5.429 |
| Aptos para búsqueda | 99,2% | 99,3% |
| Fecha, tribunal, carátula, expediente, firmantes | 100% | 100% |
| Sala | 100% | no aplica |
| Resultado | 97,8% | 92,0% |
| Normas citadas | 99,4% | 99,7% |
| Votos | 98,7% | no aplica |
| Número de sentencia | 25,6%¹ | 87,3% |

¹ La mayoría de los fallos de Cámara no escriben su número de sentencia en el texto. Cuando lo escriben, la extracción es correcta (capa 3: 100%).

Completitud: el sitio informó 22.294 fallos y el catálogo tiene 22.134 (**99,3%**).

## Pendientes

1. **Reintentar los 166 fallos faltantes** (17 días; 74 del 31/08/2026 y 48 del 31/03/2026). El reintento del 28/09 no pudo correr: **csjn.gov.ar bloqueó nuestra IP** desde las ~11:48. Desde otra IP argentina (un celular con datos móviles) el sitio anda. La causa fue nuestra: el reprocesado bajó 23.416 PDFs a ~40 por segundo, con 6 descargas simultáneas y sin pausa. Ahora `reprocess_pdfs` tiene un límite global (2 por segundo por defecto); los scrapers ya iban a ~1 pedido por segundo. Cuando se levante el bloqueo, correr `python -m spikes.retry_incomplete --desde 2025-09-27 --hasta 2026-09-27` (son pocas búsquedas y ya van con pausa). No insistir mientras dure el bloqueo.
2. Que una persona revise una muestra de la extracción ciega: los agentes son Claude, igual que el que escribió las regex.
