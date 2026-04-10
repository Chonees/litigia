# Ruido Procesal Argentino — Tipos y Tratamiento en RAG

## Contexto

En un pipeline RAG sobre jurisprudencia argentina, entre el 70% y el 86% de los fallos
recuperados por búsqueda vectorial son "ruido procesal": documentos que coinciden
semánticamente con la query (mencionan las mismas normas, fueros y hechos) pero no
contienen doctrina sustantiva. Mandarlos a un agente lector desperdicia tokens sin
agregar valor al análisis.

**Distribución observada en el benchmark (Standard 100 + transparencia):**

| Categoría | Cantidad | % del total |
|-----------|----------|-------------|
| Inadmisibles procesales | 62 | 70% |
| Con contenido sustantivo | 27 | 30% |

En escala Economy 100, la proporción sube al 75%. A mayor escala, mayor saturación de ruido.

---

## Diferencia clave con EE.UU.

En la Corte Suprema de EE.UU., los *cert denials* **no se publican como fallos** — son
entradas administrativas que no forman parte de la base jurisprudencial.

En Argentina, **cada rechazo art. 280 CPCCN es un "fallo" completo en SAIJ y CSJN.org**,
con número de expediente, carátula, tribunal, fecha, y texto. Las bases de datos no
distinguen entre "fallo con doctrina" y "fallo de una línea". El vector de embeddings los
trata como documentos iguales porque comparten el vocabulario jurídico del área.

---

## Tipos de ruido procesal argentino

### 1. Art. 280 CPCCN — "Certiorari criollo"

**Norma:** Artículo 280 del Código Procesal Civil y Comercial de la Nación.

**Qué hace:** Permite a la CSJN rechazar recursos extraordinarios federales sin expresar
fundamentos, invocando únicamente la "falta de agravio federal suficiente", "insuficiencia
de fundamentación" o "cuestiones de hecho, prueba y derecho procesal". No hay reasoning.
El fallo completo es: *"Buenos Aires, [fecha]. Vistos los autos: [...] Considerando: Que el
recurso extraordinario, cuya denegación origina esta queja, es inadmisible (art. 280 del
Código Procesal Civil y Comercial de la Nación). Por ello, se desestima la queja."*

**Magnitud:** La CSJN rechaza entre el 80% y el 90% de los REX por art. 280. Son miles de
fallos por año, todos registrados en SAIJ con metadatos completos.

**Problema para RAG:** El texto menciona explícitamente el artículo en disputa (ej: "art.
173 CP", "art. 245 LCT") en la carátula y el encabezado. El vector embedding los ubica
cerca de los fallos sustantivos del mismo fuero. Pero no hay doctrina, no hay hechos
analizados, no hay razonamiento. El agente lector gasta ~$0.03 para escribir tres párrafos
explicando por qué el fallo "no aporta doctrina".

**Señal de detección:**
- Texto contiene "art. 280" o "artículo 280"
- Longitud < 2000 caracteres
- Palabras clave: "desestimase", "desestimase la queja", "inadmisible (art. 280)"

---

### 2. Incidentes de competencia (art. 117 CN)

**Norma:** Artículo 117 de la Constitución Nacional + arts. 7-24 CPCCN.

**Qué hace:** Deciden qué tribunal es competente para conocer el fondo. El fallo SOLO
resuelve si el caso va a la justicia federal, ordinaria, o a la CSJN en instancia
originaria. No entra al mérito.

**Problema para RAG:** En casos con componente penal, tributario y societario simultáneo
(exactamente el tipo de caso complejo que usa LITIGIA), hay docenas de fallos de
competencia que mencionan todas las normas del caso (art. 173 CP, ley 24.769, ley 19.550)
sin pronunciarse sobre ninguna de ellas. El vector los confunde con fallos sustantivos.

**Señal de detección:** Texto < 1500 chars + "competencia" en título + ausencia de
"condenó", "rechazó la demanda", "hizo lugar".

---

### 3. Recursos de queja por REX denegado (art. 285 CPCCN)

**Norma:** Artículo 285 CPCCN.

**Qué hace:** Cuando la Cámara deniega el recurso extraordinario federal, la parte puede
presentar queja directamente ante la CSJN. La CSJN rechaza la queja (usualmente por art.
280) o la admite. Los rechazos son brevísimos.

**Relación con art. 280:** El fallo de queja IS el art. 280 en muchos casos. Son la misma
basura pero a veces tienen texto ligeramente distinto: "Que el recurso extraordinario, cuya
denegación origina esta queja..." vs el REX directo.

**Señal de detección:** Texto contiene "queja" + "denegación origina" + < 1500 chars.

---

### 4. Desistimientos y caducidades (art. 310 CPCCN)

**Norma:** Art. 304 (desistimiento del proceso), art. 305 (desistimiento del derecho),
art. 310 (caducidad de instancia).

**Qué hace:** El actor abandona el caso (desistimiento) o no mueve el expediente durante
el plazo legal y el proceso caduca. El fallo solo homologa la situación procesal. No hay
análisis de fondo.

**Problema para RAG:** El fallo menciona el nombre de las partes, la norma invocada (ej:
"administración fraudulenta art. 173 CP"), y el tribunal. Todo lo que hace el embedding
necesario para una alta similitud coseno con la query.

**Señal de detección:**
- Texto contiene "desistimiento" o "dase por desistido"
- Texto contiene "caducidad de instancia"
- Longitud < 1500 chars (el fallo de caducidad es literalmente: "tengo por operada la
  caducidad de instancia y por perdido el derecho")

---

### 5. Acordadas y resoluciones administrativas

**Normas principales:**
- Acordada 4/2007 CSJN: formato, extensión y carátula del REX
- Acordada 13/2022 CSJN: firma digital, presentación electrónica
- Acordada 47/91 CSJN: depósito previo para recursos de queja

**Qué hace:** El tribunal rechaza el recurso no por su mérito sino porque el escrito no
cumple los requisitos formales: excede páginas permitidas, no tiene carátula, falta la
firma digital, no se abonó el depósito de queja.

**Problema para RAG:** Son rechazos formales, no sustantivos. Pero el vocabulario es
idéntico al de fallos con fondo: mismas partes, mismas normas. A veces la Acordada 4/2007
se menciona en fallos sustantivos de REX también, lo que hace más difícil filtrarlos solo
por keywords.

**Señal de detección:** Texto < 1000 chars + mención de "Acordada 4/2007", "Acordada
47/91", "insuficiencia de depósito", "no se ha dado cumplimiento a la Acordada".

---

### 6. Fallos con texto incompleto (SAIJ/CSJN)

**Qué hace:** SAIJ y CSJN.org a veces publican solo el sumario o encabezado del fallo,
no el texto completo. El sistema de scraping capturó el documento pero no tiene contenido
sustantivo.

**Tipos:**
- Solo "Sumario: [2-3 líneas de resumen]" sin el texto
- Solo la carátula y la parte resolutiva, sin los considerandos
- Fallo truncado por error en el PDF (el scraper no pudo extraer texto del PDF)

**Problema para RAG:** Estos documentos tienen score alto en vector search porque el
sumario fue redactado para capturar los conceptos clave. Pero no hay texto del que extraer
doctrina, hechos o razonamiento. El agente lector recibe 200 caracteres y produce un
análisis vacío.

**Señal de detección:** Longitud < 500 caracteres (cualquier fallo real tiene al menos los
vistos, considerandos y resolutiva, que suman más de 500 chars).

---

## Impacto económico del ruido

En el benchmark Standard 100 ($3.33 total):

- ~$2.33 gastados en leer 62 fallos sin contenido sustantivo
- ~$1.00 en los 27 fallos con doctrina real
- **El 70% del costo total se va en ruido**

El agente lector ante un art. 280 invariablemente escribe:
> "El fallo es muy breve (2-3 páginas). Solo decide sobre la procedencia del recurso de
> queja. No aporta doctrina sobre prescripción penal ni administración fraudulenta.
> Relevancia LIMITADA Y NEGATIVA."

Eso cuesta lo mismo que analizar un Fallos: 340:1771 de 30 páginas.

---

## Solución implementada: pre-filtro de calidad

Ver `backend/app/services/analysis.py`, función `_filter_low_quality`.

El filtro se ejecuta ENTRE el resultado de búsqueda y los agentes lectores. Clasifica
automáticamente como "inadmisible" sin gastar tokens de reader los fallos que cumplen
cualquiera de los criterios de ruido. Solo los fallos sustantivos llegan a los agentes.

Ahorro estimado: 50-70% en costo de readers, con igual o mejor calidad de sintesis
(el sintetizador recibe menos inadmisibles y mas fallos con fondo real).

---

## Se pierde valor con el filtro?

**No.** Y los datos del benchmark lo confirman:

### Evidencia cuantitativa

De los 62 inadmisibles que Opus analizo en Standard 100 + transparencia, la recomendacion
estrategica final se baso en los 14 favorables, 8 desfavorables y 5 parciales. Los 62
inadmisibles aportaron exactamente UNA cosa util: "la CSJN rechaza REX por art. 280,
cuida los requisitos formales". Eso se aprende con 1 fallo inadmisible, no con 62.

### Evidencia cualitativa (chain of thought)

Con transparencia activada, los agentes lectores confirman el problema en su propio
razonamiento. Frases textuales de los agentes ante fallos filtrados:

- "El fallo es muy breve (2-3 paginas) y es fundamentalmente un rechazo formal"
- "Es claramente un fragmento extractado, no el fallo completo"
- "La CSJN no entra en ningun analisis de fondo"
- "Relevancia LIMITADA Y NEGATIVA para el caso del cliente"
- "No aporta doctrina sobre prescripcion penal ni administracion fraudulenta"

Cada agente gasto ~$0.03 en tokens para llegar a la misma conclusion: "este fallo no
sirve". El filtro llega a la misma conclusion con 0 tokens en 0.001 segundos.

### Riesgo real del filtro

El filtro es por largo de texto + keywords. Podria filtrar incorrectamente:

1. **Fallo corto pero sustantivo** — un pronunciamiento de CSJN que en 1500 caracteres
   sienta doctrina nueva. Raro pero posible en cuestiones de competencia con analisis
   de fondo breve.

2. **Fallo que DISCUTE el art. 280** — un fallo sustantivo que analiza la
   constitucionalidad del art. 280 como tema de fondo (ej: Vidal, Fallos: 344:3156).
   Poco probable porque esos fallos son largos (> 5000 chars).

**Riesgo real evaluado**: Revisando los 62 inadmisibles del benchmark Standard 100,
NINGUNO tenia doctrina sustantiva. Todos eran "desestimase" + deposito. El filtro los
hubiera descartado correctamente a todos.

### Red de seguridad

Los fallos filtrados NO se pierden:

1. Se cuentan como "inadmisible - pre-filtrado automatico" en el resultado final
2. Aparecen en la lista de fallos analizados con la nota de por que fueron filtrados
3. El abogado VE que fueron filtrados y puede decidir re-analizarlos manualmente
4. El sintetizador sabe cuantos fueron filtrados y lo incluye en sus estadisticas

No se pierde visibilidad. Solo se evita gastar tokens en lo que ya se sabe que no sirve.

### Ahorro por escala con el filtro

| Escala | Filtrados (est.) | Ahorro readers | Ahorro total (incl. synth) |
|--------|-----------------|----------------|---------------------------|
| 10 fallos | ~3 (30%) | ~25% | ~15% |
| 30 fallos | ~12 (40%) | ~35% | ~25% |
| 50 fallos | ~25 (50%) | ~45% | ~30% |
| 100 fallos | ~60 (60%) | ~55% | ~40% |

A mayor escala, mayor ahorro — porque el pipeline de busqueda se satura en ~25-30
fallos sustantivos y rellena con ruido procesal. El filtro captura ese relleno.

### Optimizacion adicional: max_tokens dinamico

Ademas del pre-filtro, los fallos que SI pasan al reader pero son cortos reciben un
limite de output menor:

| Texto del fallo | Sin transparencia | Con transparencia |
|-----------------|-------------------|-------------------|
| < 2000 chars | 1000 tokens | 2000 tokens |
| 2000-5000 chars | 1500 tokens | 3500 tokens |
| > 5000 chars | 2000 tokens | 3500 tokens |

Un fallo corto que paso el filtro no necesita 2000 tokens de respuesta. Con 1000 alcanza.
Esto ahorra ~20% adicional en tokens de output para fallos medianos.
