# Benchmark de búsqueda

Fecha: 2026-10-01 · Archivos: `backend/labels/bench/` · Se arma con `python -m spikes.build_bench <ronda1.json> <ronda2.json>`

Mide si LITIGIA encuentra **el fallo que sirve** para la consulta de un abogado. Está hecho para que **no se pueda arreglar**: la respuesta correcta no la ponemos nosotros, y nadie que escribió una consulta vio nuestra base.

## Qué tiene

| Fuero | Fallos conocidos (dev / test) | Con la cita de la fuente textual en el fallo | Consultas de doctrina (dev / test) |
|---|---|---|---|
| Laboral | 96 (30 / 66) | 61 | 20 (5 / 15) |
| Seguridad social | 20 (10 / 10) | 15 | 20 (6 / 14) |
| Contencioso adm. federal | 70 (21 / 49) | 31 | 20 (6 / 14) |
| Civil | 68 (21 / 47) | 43 | 20 (7 / 13) |
| Comercial | 57 (20 / 37) | 41 | 20 (4 / 16) |
| **Total** | **311 (102 / 209)** | **191** | **100 (28 / 72)** |

Se armó en **dos rondas** de búsqueda. La segunda no repitió fallos de la primera y recorrió Microjuris de forma sistemática (por la API del sitio, tema por tema).

### 1. Fallos conocidos (`known_items.jsonl`)

Un **tercero** describió un caso real y citó el fallo que lo resolvió. Los terceros son:
- Microjuris Al Día (117)
- los boletines de jurisprudencia de la CNACAF (53)
- SADL (24)
- Diario Judicial (18)
- revistas y blogs profesionales: notariado, contadores, estudios
- elDial, Palabras del Derecho y abogados.com.ar

**La consulta** se escribió a partir de los hechos y la cuestión que cuenta la fuente, como la escribiría un abogado que tiene un caso parecido. No lleva partes, carátula, expediente, Sala, fecha ni frases copiadas.

**La respuesta correcta** es el fallo que cita la fuente, ubicado después en nuestra base.

**La verificación:**
- Un agente distinto ubicó cada fallo y comprobó partes, fecha, Sala y que el resolutivo dijera lo mismo que la fuente.
- Después el código revisó cada ubicación: fuero, fecha y partes. Las carátulas con iniciales se cotejaron a mano contra las iniciales de las partes.
- En **191 de 311**, el pasaje que cita la fuente aparece **palabra por palabra** en el texto del fallo.
- En los desacuerdos se leyó el fallo. Las diferencias de fecha y de Sala son de la **nota**: pone la fecha de publicación, o mezcla la Sala de un fallo revocado por la Corte con la del fallo nuevo.

En **12** la fuente cuenta mal el resultado: por ejemplo, dice "revocó" y el fallo confirmó. Igual son la respuesta correcta para encontrar el caso, pero quedan marcados con `decision_verificada: false` y no se usan para medir si un fallo favorece o no al abogado.

### 2. Consultas de doctrina (`queries.jsonl`)

Son las cuestiones que se litigan en cada tipo de caso, tomadas de manuales, artículos de doctrina, guías de práctica, colegios de abogados y comentarios a fallos, con **399 URLs** de respaldo. Cada consulta trae, **escrita antes de buscar**:
- `relevante_si`: qué tiene que haber **decidido** el tribunal para que el fallo sirva. No alcanza con que mencione el tema.
- `no_relevante_si`: los casos que parecen servir y no sirven, como un voto en minoría, un recurso abstracto u otro régimen legal.
- `lado_cliente`: a quién representa el abogado, para medir a favor o en contra.

Cubren todos los tipos de caso, incluidos los que la prensa casi no cubre: concursos, juicios ejecutivos, sociedades, escrituración, desalojo, costas previsionales, ejecuciones fiscales y amparo por mora.

## Por qué no se puede "ganar"

| Riesgo | Cómo se evita |
|---|---|
| Escribir consultas que ya sabemos que dan bien | Nadie que escribió una consulta vio nuestra base. Las de fallos conocidos salen de lo que contó un tercero. |
| Que la consulta delate el fallo | Un crítico por fuero revisó todo en las dos rondas: corrigió 67 y descartó 39. Después el **código** volvió a revisar tres cosas:<br>• nombres de las partes que son raros en la base (aparecen en menos de 20 carátulas)<br>• números de expediente que no son de una norma<br>• 8 palabras seguidas copiadas de la fuente<br>Con eso descartó 7 más. |
| Ajustar el buscador hasta que pase | Hay un **set de desarrollo** (30%) y un **set de prueba** (70%). La separación sale de un hash del contenido y no se elige a mano. Las reglas se ajustan **solo** mirando dev. El test se corre en cada hito y sus errores no se usan para escribir reglas. |
| Juzgar a favor de lo nuestro | Las consultas de doctrina se juzgan **a ciegas**. Se juntan los 10 primeros resultados de cada sistema (el nuestro y una búsqueda simple por palabras), se mezclan y el juez no sabe de dónde salió cada uno. Aplica la regla escrita antes y lee solo el texto (`spikes/show_text.py`). |
| Medir sin comparación | Siempre contra una **búsqueda simple por palabras** (BM25) sobre el texto completo. Si esa búsqueda ya acierta casi todo, el set es demasiado fácil y se dice. |

## Cómo se mide (Fase 3)

**Fallos conocidos:**
- Si el fallo correcto aparece entre los **10 primeros** (recall@10) y en qué puesto (MRR).
- Para el conector MCP lo que más importa es que entre en los 10 primeros, porque el asistente del abogado lee y elige entre ellos.

**Doctrina:**
- P@5 y P@10 con el juicio a ciegas.
- Si el fallo favorece o no al `lado_cliente`.
- Los juicios se guardan en `judgments.jsonl`, así una corrida nueva solo juzga los fallos nuevos.

**Cómo se informa:** siempre por **fuero y tipo de caso**, con el tamaño de cada muestra y la lista de errores. Un promedio general esconde que familia o concursos anden mal.

## Uso secundario: validar nuestros datos contra lo que escribieron personas

Cada nota dice también qué decidió el tribunal, con qué normas, quiénes votaron y si hubo disidencia. Un agente leyó **solo la nota** de cada fallo y anotó esos datos (`validacion_notas.jsonl`). `spikes/compare_with_notes.py` los compara con los nuestros (`desacuerdos.jsonl`).

**Tanda 1 (112 fallos).** Sirvió para encontrar errores nuestros y corregirlos, con tests:
- se perdían las normas citadas en lista ("arts. 1463 y 1467 del CCyCN") y el código procesal con otros nombres ("Cód. Procesal", "código ritual");
- no se leía la disidencia parcial.

**Tanda 2 (199 fallos que no se miraron al corregir).** Mide si esas correcciones **generalizan**:

| Dato | Tanda 1, al principio | Tanda 1, corregida | **Tanda 2, nunca vista** |
|---|---|---|---|
| Sala | 100% | 100% | 98% (los 4 desacuerdos son errores de la nota) |
| Instancia | 99% | 99% | 100% |
| Fecha | 96% | 96% | 97% (diferencias = fecha de publicación de la nota) |
| Jueces que nombra la nota y firman | 99% | 99% | 98% |
| Normas que la nota dice que se aplicaron | 76% | 90% | **90%** |
| Por mayoría | 87% | 98% | **86%** |
| Resultado exacto | 60% | 67% | 65% |

- **Normas generaliza.**
- **Mayoría no generalizaba tanto:** en la tanda 2 aparecieron formas que la 1 no tenía, como "en lo que **resulta** materia de disidencia", "**zanjar** tal disidencia" o "el voto de **la mayoría**".
- **Resultado:** la mayoría de los desacuerdos son zonas grises o errores de la nota. La nota cuenta lo que pasó en primera instancia ("hizo lugar a la demanda") cuando la Cámara confirmó, o dice "rechazó" donde el fallo "rechaza el recurso y confirma".

Los errores reales de la tanda 2 se corrigieron con tests. Por eso, **desde acá, la tanda 2 deja de ser una medición independiente**: la cifra honesta de generalización es la de la tabla.

**Después de las correcciones**, con la base recalculada:

| Dato | Tanda 1 | Tanda 2 |
|---|---|---|
| Por mayoría | 98% | 94% |
| Resultado exacto | 68% | 68% |
| Normas | 90% | 90% |

**Antes de recalcular se hizo una verificación en solo lectura sobre los 78.911 fallos del año:**
- Los estados no cambian: siguen 77.525 aptos, que pasaron a 77.546 al completar los 22 fallos de la sección Cobertura.
- 7.806 fallos quedan por mayoría.
- Contra el gold ciego de `labels/gold/enrich`, ningún set baja. En esa verificación apareció una regla nueva que empeoraba un fallo del gold ("mal concedido" con "confirmar las costas"), y se corrigió antes de tocar la base.
- La regla nueva de mayoría ("el voto de la mayoría") la usa solo la Sala A de la Cámara Civil, y en 97 de 100 de sus fallos hay una disidencia real de un juez.

El "resultado" registra **lo que cambió en la sentencia**. Cuando un recurso se rechaza y el otro se admite y la sentencia se modifica, cuenta como "modifica", no "rechaza". Los desacuerdos que quedan son casi todos de este tipo:
- **La nota cuenta otra instancia:** dice que se "hizo lugar a la demanda" cuando la Cámara confirmó.
- **Zonas grises:** un resolutivo que confirma lo principal y modifica los intereses.

## Cobertura: ¿tenemos lo que publican los terceros?

Las fuentes citaron **373 fallos distintos** de nuestra ventana. **325 estaban en la base (87%).** Los 48 restantes se buscaron en el sitio del PJN por una palabra de la carátula, en ±30 días alrededor de la fecha citada (`spikes/site_lookup.py`), primero entre las definitivas y después entre las interlocutorias:

| Qué son | Cuántos |
|---|---|
| **Interlocutorias** en el sitio. Solo bajamos sentencias definitivas | 20 |
| **No aparecen en el sitio**, ni como definitiva ni como interlocutoria. Muchos son de primera instancia o amparos | 17 |
| Sin determinar: la carátula solo tiene iniciales o nombres genéricos ("Superintendencia de Seguros c/…") | 9 |
| Plenario (otro tipo de fallo) | 1 |
| **Definitiva publicada que nos faltaba** | **1** |

Detalle en `labels/bench/cobertura_sitio.jsonl`.

**La definitiva que faltaba destapó un error nuestro, que ya está corregido:**
- **El caso:** González Haydee Alicia c/ ANSES, Sala 3 de la Seguridad Social, 10/04/2026.
- **Qué pasaba:** el scraper viejo había bajado su PDF sin los datos del listado (tribunal, carátula), y esa copia quedó desactivada. Cuando las VPS lo bajaron de nuevo, la fusión de catálogos **salteaba los fallos con el mismo texto** y nunca le pasó los datos ni lo reactivó.
- **El alcance:** había **22 fallos así** (12 de seguridad social, 6 civiles y 4 de contencioso). La conciliación los contaba como "guardados" porque el documento existía.
- **La corrección, con tests:**
  - La fusión ya no saltea una copia desactivada o incompleta.
  - La conciliación separa la columna **"desactivados"**, que hoy da 0 en los cinco fueros.
  - Los 22 se completaron desde los catálogos de las VPS.

**Lo que esto dice:**
- Con esa corrección, la base tiene **todas las sentencias definitivas publicadas** que citaron los terceros en nuestra ventana. Es una prueba de completitud con una fuente independiente del sitio, y además encontró un error que la conciliación no podía ver.
- El hueco real son las **interlocutorias**: 20 de 373 fallos citados (5%). Algunas deciden cuestiones que un abogado busca: despidos en la CNAT, reajustes previsionales, ejecutivos y consumo en comercial. Están en el plan para después del MVP, y esto sirve como evidencia para priorizarlas.
- Hay fallos **que el sitio no publica**, sobre todo de juzgados de primera instancia y amparos contra el Estado. Ese hueco es del PJN y ningún scraper lo cierra.

**Qué volumen implican las interlocutorias:** el sitio publica más interlocutorias que definitivas.

| Fuero | Definitivas | Interlocutorias |
|---|---|---|
| Laboral | 22.653 | 27.020 |
| Seguridad social | 35.635 | 24.471 |
| Contencioso adm. federal | 13.088 | 6.738 |
| Civil | 6.788 | 26.038 |
| Comercial | 948 | 10.861 |
| **Total** | **79.112** | **95.128** |

Mucho de eso es trámite: honorarios, competencia, caducidad. Sumarlas duplicaría la base y obligaría a separar lo que decide una cuestión de lo que no, que es la primera pregunta del mapa de Jev. Por eso quedan para después del MVP.

Fuente: `spikes.site_totals` del 27/09/2025 al 27/09/2026, consultado el 01/10/2026.

## Límites (lo que este benchmark NO garantiza)

- **El juez es un modelo de la misma familia que el sistema** (Claude). Los fallos conocidos son el ancla confiable, porque ahí la respuesta la fijó un tercero. Una persona tiene que revisar una muestra de los juicios de doctrina.
- **La prensa elige fallos "noticiables"**: casos novedosos más que la sentencia de todos los días.
  - En comercial, 32 de 57 fallos conocidos son de consumo, y hay 1 de concursos y 1 de sociedades.
  - Seguridad social tiene solo 20, aunque es el fuero más grande: la prensa lo cubre poco.
  - Lo compensan las consultas de doctrina, que cubren lo rutinario.
- **Algunas fuentes reescriben poco el fallo.** 53 de 311 salen de los boletines de la propia CNACAF, cuyos sumarios usan el vocabulario del fallo. Eso le facilita el trabajo a la búsqueda por palabras; por eso se compara siempre contra ella y se informa por fuente.
- **Las muestras por tipo de caso siguen siendo chicas** en los tipos menos comentados (familia 7, sucesiones 6, concursos 1). Sirven para detectar un tipo de caso que no anda, no para dar un número fino.
- **Abogados reales:** las pruebas con sus casos y los fallos que citaron van **después del MVP**.

## Cómo se armó

Dos rondas de workflows con agentes, sin errores al final:

1. **Fallos conocidos:**
   - Ronda 1: 8 agentes buscaron en la web, por fuero y por tipo de fuente.
   - Ronda 2: 10 agentes, uno por fuero en Microjuris y otro por fuero en las demás fuentes, con la lista de lo ya citado para no repetir.
   - Ninguno tuvo acceso a nuestra base ni al sitio del PJN.
2. **Ubicación:** un agente por lote ubicó cada fallo citado con `spikes/find_ruling.py` y lo verificó leyendo el texto. No podía cambiar la consulta.
3. **Validación contra la nota:** un agente leyó solo la nota de cada fallo ubicado y anotó lo que dice la persona.
4. **Doctrina:** 5 agentes, uno por fuero, sin acceso a la base.
5. **Revisión:** un crítico por fuero en cada ronda, a la caza de filtraciones, consultas poco realistas y errores jurídicos.
6. **Código** (`spikes/build_bench.py`, con tests):
   - junta las rondas y aplica las correcciones del crítico;
   - vuelve a chequear las filtraciones;
   - saca duplicados (22 fallos los citó más de una fuente);
   - separa dev y test;
   - escribe `cobertura.jsonl` y `validacion_notas.jsonl`.

La salida completa de cada ronda, con las notas de cada agente, queda en `labels/bench/fuentes_workflow.json` para auditar.
