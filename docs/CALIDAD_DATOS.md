# Calidad real de los datos — 5 fueros nacionales de CABA, 12 meses

Fecha: 2026-09-30, actualizado el 2026-10-01 · Alcance: sentencias definitivas del 27/09/2025 al 27/09/2026 de las cámaras nacionales del Trabajo, de la Seguridad Social, en lo Contencioso Administrativo Federal, en lo Civil y en lo Comercial, con sus juzgados de primera instancia. Fuente: el sitio público de fallos del PJN.

La auditoría común mide **cobertura** (si un campo existe). Este test mide además **completitud** contra el sitio y **exactitud** (si el valor es correcto), en cuatro capas. La cuarta compara con lo que escribieron **personas**.

## Resumen

| Fuero | Informa el sitio | Guardados | Aptos para búsqueda | Chequeos cruzados | Texto contra PDF | Resultado a ciegas |
|---|---|---|---|---|---|---|
| Laboral | 22.653 | 22.551 (**99,5%**) | 22.431 | ≥ 99% | 50/50 idénticos | 100% (30 fallos) |
| Seguridad social | 35.635 | 35.582 (**99,9%**) | 35.438 | ≥ 97% | 50/50 | 88% (16)¹ |
| Contencioso adm. federal | 13.088 | 13.088 (**100%**) | 12.086 | ≥ 98%² | 50/50 | 88% (16)¹ |
| Civil | 6.788 | 6.764 (**99,6%**) | 6.644 | ≥ 99% | 50/50 | 94% (16)¹ |
| Comercial | 948 | 948 (**100%**) | 945 | ≥ 99% | 50/50 | 75% (16)¹ |
| **Total** | **79.112** | **78.933 (99,8%)** | **77.546** | | **250/250** | |

¹ Casi todos los desacuerdos son **zonas grises** que el propio lector ciego marcó como dudosas (ver Capa 3).
² Salvo dos chequeos informativos por el estilo del fuero: muchos fallos no nombran a la Cámara ni repiten las partes (93% y 95%).

**Instancia, Sala (cuando el texto la nombra), primer voto y número de sentencia dieron 100% a ciegas en los cinco fueros.**

**Contra 311 notas escritas por personas** (Capa 4):
- Sala 99%, instancia 100%, jueces 99%.
- Normas 90% (antes 76%) y mayoría 96% (antes 87%), después de las correcciones que salieron de esa comparación.

## Completitud: cada fallo del sitio, contabilizado

`python -m scripts.reconcile --camara C_x --desde 2025-09-27 --hasta 2026-09-27`

El scraper registra qué listó cada búsqueda (`listings`) y qué PDFs fallaron y por qué (`failures`). La conciliación compara, por mes y por año, lo que informa el sitio con lo que se guardó.

| Fuero | Lo que falta | Por qué |
|---|---|---|
| Laboral | 102 (0,5%) | Días cuyo reintento quedó cortado porque la PC se suspendió. Se retoma con `spikes.retry_incomplete --camara C_7` |
| Seguridad social | 53 (0,1%) | **El sitio los cuenta pero nunca los muestra**, en 4 días de más de 360 fallos, aun buscando oficina por oficina y por año del expediente |
| Civil | 24 (0,4%) | **PDFs que el sitio sirve vacíos**, siempre los mismos (16 del 8 al 10/08/2026) |
| Contencioso y comercial | 0 | — |

Ningún día quedó sin cubrir y ningún fallo quedó guardado con una fecha fuera de su búsqueda.

## Capa 1 — Chequeos cruzados contra el texto

`python -m spikes.quality_check --camara C_x --desde 2025-09-27 --hasta 2026-09-27`

| Chequeo | Laboral | Seg. social | Contencioso | Civil | Comercial |
|---|---|---|---|---|---|
| El texto no contradice el expediente | 99,0% | 99,8% | 99,0% | 99,3% | 99,7% |
| Parte de la carátula aparece en el texto | 99,5% | 100% | 95,2%² | 99,2% | 99,0% |
| Fecha en día hábil | 99,7% | 100% | 100% | 100% | 99,8% |
| El texto termina en la parte resolutiva o la firma | 99,7% | 99,9% | 99,2% | 99,3% | 99,9% |
| Texto legible | 100% | 100% | 100% | 100% | 100% |
| El texto no contradice la Sala | 99,7% | 97,0% | 98,2% | 99,7% | 99,6% |
| Cada juez que vota también firma | 99,5% | 99,9% | 100% | 99,7% | 100% |

Lo que queda es mayormente **del PJN** (números de expediente o fechas que difieren entre el sistema y el fallo) o **del estilo del fuero**. Tres correcciones de esta auditoría fueron **del chequeo y no de los datos**: las Salas en números arábigos (la Seguridad Social escribe "Sala 2"), los apellidos compuestos en las firmas ("Fantini Albarenque"), y en contencioso las Salas **del Tribunal Fiscal** y los **expedientes administrativos** que aparecen en la carátula ("DNM – EXPTE 3074/15").

## Capa 2 — Fidelidad del texto

`python -m spikes.text_fidelity --n 50 --camara C_x`

**250 de 250 PDFs bajados de nuevo (50 por fuero) dieron exactamente el texto guardado.** No hay corrupción ni al bajar, ni al limpiar, ni al juntar las 20 VPS.

## Capa 3 — Exactitud del enriquecimiento (extracción a ciegas)

Seis agentes independientes leyeron **64 fallos nuevos** (16 por fuero nuevo, 8 de Cámara y 8 de primera instancia, al azar con semilla fija) **sin ver nuestros datos**: `spikes/show_text.py` muestra solo el texto. Muestra: `backend/labels/gold/enrich/fueros_sample.json`; respuestas: `fuero_C_*.jsonl`.

| Campo | Seg. social | Contencioso | Civil | Comercial | Laboral (30) |
|---|---|---|---|---|---|
| Instancia | 100% | 100% | 100% | 100% | 100% |
| Resultado | 88% | 88% | 94% | 75% | 100% |
| Primer voto | 100% | 100% | 100% | 100% | 100% |
| Número de sentencia | 100% | 100% | 100% | 100% | 100% |
| Sala (cuando el texto la nombra) | 100% | 100% | 100% | 100% | 100% |

**Las diferencias de resultado son casi todas zonas grises que el lector marcó como dudosas:**
- El primer punto del resolutivo **rechaza algo secundario** (la demanda contra un codemandado, un pedido de inconstitucionalidad) y el siguiente **hace lugar a lo principal**. ¿El resultado es "rechaza" o "hace lugar"?
- Seguridad social: el primer punto **difiere los topes a la etapa de ejecución**. ¿Confirma o revoca?
- Comercial: el resolutivo tiene **un punto por cada apelación** (rechaza la del actor, admite en parte la del demandado).

El campo "resultado" registra **lo que cambió en la sentencia**. Desde el 01/10, cuando un recurso se rechaza y otro se admite para revocar o modificar, cuenta la revocación o la modificación, no el "rechaza" del primer punto.

El gold se armó con la convención anterior, la del primer punto. Por eso en comercial un caso que el lector marcó como dudoso ("el resultado global es modificación parcial") figura como "rechaza" en el gold y como "modifica" en la base. El gold no se cambió.

**Quién ganó cada punto lo responde el etiquetado con Jev** (agravios por parte), no esta regla.

Sobre los votos: en civil y comercial, los lectores contaron también a los jueces que **adhieren** sin voto propio ("la Dra. Iturbide vota en el mismo sentido"). El campo `votos` registra a quienes escriben su voto; los demás están en `firmantes` (100%). Por eso en esos fueros se mide el **primer voto**, que es el que fija el criterio.

### Correcciones que salieron de esta auditoría (todas con test, 165 en total)

| Fuero | Qué no se leía bien |
|---|---|
| Seguridad social | Primera persona ("**hago lugar**", "rechazo"); rechazar una **defensa** no es rechazar la demanda; "confirmarla"; el PDF que imprime "1) Revocar…" antes de "el Tribunal RESUELVE:"; dos jueces pegados en un solo voto ("Dorado. EL Doctor Walter F. Carnota") |
| Contencioso | "**ASÍ SE RESUELVE**" como cierre y no como apertura; decisiones escritas en el último considerando; "**atribuir la competencia**"; "denegar el recurso extraordinario"; "**mandando llevar adelante la ejecución**" (las ejecuciones fiscales: primera instancia pasó de 22% a 93%); los juzgados de Ejecuciones Fiscales son de este fuero |
| Civil | "el Tribunal **decide:**"; "**Elevar / Reducir** la suma reconocida" es modificar; la fórmula sin "FALLO" que deja el PDF ("Por todo lo expuesto, :"); "el Juez de Cámara Doctor X dijo:"; artículos del CCyC y del CPCCN como normas citadas |
| Comercial | "los señores Jueces de Cámara **acuerdan:**"; "Juez de Cámara**,** doctor X dijo:"; "sentencio este juicio de trance y remate" |
| Todos | El expediente que se lee del encabezado prefiere el número del PJN (CAF, CNT, CIV…) al de un expediente administrativo |

## Capa 4 — Contra notas escritas por personas

`python -m spikes.compare_with_notes` · Detalle en [BENCHMARK.md](BENCHMARK.md#uso-secundario-validar-nuestros-datos-contra-lo-que-escribieron-personas)

311 fallos del año tienen una nota publicada por un tercero: Microjuris, Diario Judicial, boletines de la CNACAF, SADL y otros. Un agente leyó **solo la nota** y anotó qué dice sobre:
- el resultado;
- las normas aplicadas;
- los jueces;
- si hubo disidencia.

La comparación con nuestros datos mostró errores que las capas anteriores no veían:
- **Normas:** se perdían las citas en lista ("arts. 1463 y 1467 del CCyCN", "arts. 330 inc. 2 y 377 del C.P.C.C.N.") y el código procesal con otros nombres ("Cód. Procesal", "código ritual", "ordenamiento adjetivo"). Arreglarlo sumó unas 104 mil normas y sacó unas 2 mil. En las muestras revisadas a mano, las que se fueron eran atribuciones falsas, como "ley 27.423 (art. 30)" leído como artículo del CPCCN.
- **Mayoría:** no se leía la disidencia parcial en las firmas ("(en disidencia parcial)"), ni el tercer juez que define ("en lo que es / resulta materia de disidencia", "zanjar tal disidencia"), ni "el voto de la mayoría". Ahora 7.806 fallos del año figuran por mayoría.
- **Resultado:**
  - "Decretar la deserción" es desierto;
  - "admitir el recurso y revocar" es revoca;
  - "aumentar la suma" es modifica;
  - se arreglaron los verbos que el PDF parte ("r evocar").

Las correcciones se hicieron con la tanda 1 (112 notas) y se probaron con la tanda 2 (199 notas que no se miraron al corregir):
- **Normas generalizó:** 90% en las dos tandas.
- **Mayoría no generalizó del todo:** 86% en la tanda 2, que trajo formas nuevas. Se corrigieron con tests y quedó en 94%.

**Un hueco que la conciliación no veía:**
- **Cómo apareció:** al buscar en el sitio los fallos que citó la prensa y no teníamos, salió una definitiva publicada que faltaba (González Haydee Alicia c/ ANSES, Sala 3).
- **La causa:** el scraper viejo había guardado su PDF sin tribunal ni carátula, y esa copia estaba desactivada. La fusión de los catálogos de las VPS **salteaba los fallos con el mismo texto**, así que nunca la completó ni la reactivó.
- **El alcance:** **22 fallos** (12 de seguridad social, 6 civiles y 4 de contencioso). La conciliación los contaba como "guardados".
- **La corrección:**
  - La fusión ya no saltea copias desactivadas o incompletas.
  - La conciliación tiene una columna **"desactivados"**, que hoy da 0 en los cinco fueros.
  - Los 22 se completaron.
  - Ahora los fallos activos del año son 78.933, exactamente los guardados.

Antes de cada recálculo de la base se verificó en solo lectura sobre los 78.911 fallos:
- los estados no cambian;
- ningún set del gold ciego empeora;
- se revisó a mano una muestra de los cambios.

## Fallos que no son "de fondo"

Rechazados con su motivo (nunca borrados):
- **671 fallos de contencioso que solo deciden honorarios** (`solo_honorarios`).
- Resoluciones de trámite y textos cortos, en todos los fueros.

**Pendiente conocido:** en contencioso quedan **~1.300 fallos aptos que también son de honorarios o de trámite**, con un formato que las reglas no distinguen sin rechazar fallos de fondo (una regla por densidad de palabras atrapaba amparos y sentencias laborales). **Separar fondo, honorarios y trámite va a ser la primera pregunta del mapa de Jev** (Fase 5 del plan).

## Pendientes

1. Retomar el reintento del laboral cuando la PC pueda quedar despierta (102 fallos).
2. Que una persona revise una muestra de la extracción ciega: los agentes son Claude, igual que quien escribió las reglas.
3. La carga diaria (Fase 8) tiene que correr en un servidor: esta PC entra en suspensión (Modern Standby) y congela los procesos.

---

## Anexo — Primera auditoría del laboral (28/09)

### Capa 1 — Chequeos cruzados contra el texto

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

### Capa 2 — Fidelidad del texto

`python -m spikes.text_fidelity --n 50`

- **50 de 50 PDFs bajados de nuevo dieron exactamente el mismo texto guardado.** No hay corrupción al guardar ni al juntar las VPS.
- Palabra por palabra contra el PDF crudo, la limpieza quita sellos de página, firmas y encabezados repetidos, que es lo buscado. Del **cuerpo** del fallo se perdía un 0,39%, concentrado en **tablas numéricas**. Caso real: la tabla del ingreso base mensual, con el total **$11.888.158,60**, en un recurso Ley 27.348 contra Galeno ART.
- **Corregido:** solo se descartan fragmentos numéricos del tamaño de un número de página (≤ 8 caracteres). Test con las filas reales.
- **Reprocesado (28/09):** se volvieron a bajar los 23.416 PDFs activos (`spikes/reprocess_pdfs.py`, ~10 min, 0 fallos; esa velocidad provocó el bloqueo de la IP, ver Pendientes). **En 2.242 (9,6%) el texto cambió**: recuperaron tablas de montos, fechas y liquidaciones. Los metadatos no se tocaron.
- Después del reprocesado, la capa 1 dio los mismos porcentajes: no hubo regresiones.
- La auditoría ya no cuenta como ruido las líneas numéricas largas (son filas de tabla); solo los números de página sueltos, que quedaron en **0**. Queda ruido residual de firmas en 19 fallos y sellos de página en 4 (0,1%).

### Capa 3 — Exactitud del enriquecimiento

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

### Casos donde "correcto" es discutible

Los extractores marcaron zonas grises reales, que ninguna regla resuelve sola:
- "**Confirmar** … con la salvedad de los intereses": ¿confirma o modifica?
- En primera instancia, Ley 27.348: "**Revocar** lo resuelto por la Comisión Médica y condenar a la ART": ¿revoca o hace lugar?
- "Declarar la inconstitucionalidad…" como primer punto.

Hoy se etiqueta por el primer verbo del resolutivo. Para el abogado, lo que importa es **a favor de quién**, y eso lo decide el etiquetado de la Fase 1 (agravios por parte), no esta regex.

### Expediente tal como lo escribe el fallo

Nuevo campo `expediente_texto`, leído del encabezado del fallo (normalizado: "46676/2016"). Está en **20.353 de 23.416 fallos (87%)**; en el resto el encabezado no lo repite. Cuando difiere del número del sistema del PJN (número o año), el fallo lleva la advertencia `expediente_no_coincide`: **180 fallos (0,9%)**. El buscador puede mostrar los dos.

### Auditoría final (28/09)

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

### Pendientes de esa auditoría (resueltos el 29 y 30/09)

1. **Reintentar los 166 fallos faltantes** (17 días; 74 del 31/08/2026 y 48 del 31/03/2026). El reintento del 28/09 no pudo correr: **csjn.gov.ar bloqueó nuestra IP** desde las ~11:48. Desde otra IP argentina (un celular con datos móviles) el sitio anda. La causa fue nuestra: el reprocesado bajó 23.416 PDFs a ~40 por segundo, con 6 descargas simultáneas y sin pausa. Ahora `reprocess_pdfs` tiene un límite global (2 por segundo por defecto); los scrapers ya iban a ~1 pedido por segundo. Cuando se levante el bloqueo, correr `python -m spikes.retry_incomplete --desde 2025-09-27 --hasta 2026-09-27` (son pocas búsquedas y ya van con pausa). No insistir mientras dure el bloqueo.
2. Que una persona revise una muestra de la extracción ciega: los agentes son Claude, igual que el que escribió las regex.
