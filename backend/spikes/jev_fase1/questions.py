"""Universal questions v0 for the Fase 1 spike, in Spanish and English.

Written for jev-1.13 guidance: literal conditions, every option defined with its
boundary cases, an exit option, no numbers or dates to compute. The state is always
the Spanish ruling; only the question wording changes between languages.
"""

ES = {
    "tipo_caso": {
        "type": "choice",
        "instructions": "¿Qué tipo de reclamo laboral resuelve esta sentencia de la Cámara del Trabajo?",
        "criteria": {
            "despido": "Reclamo por la extinción del contrato de trabajo: despido directo o indirecto, "
                       "indemnizaciones por despido, multas por falta de registración o por no entregar certificados.",
            "riesgos_trabajo": "Reclamo contra una ART por prestaciones de la Ley de Riesgos del Trabajo (24.557) por "
                               "accidente o enfermedad laboral, incluidos los recursos contra dictámenes de comisiones "
                               "médicas (Ley 27.348).",
            "accidente_civil": "Reclamo de reparación integral de un accidente o enfermedad laboral con fundamento en el "
                               "Código Civil (acción civil), no en la tarifa de la ley especial.",
            "salarios": "Reclamo de salarios adeudados, diferencias salariales, horas extras o encuadre convencional, "
                        "cuando el despido no es la cuestión principal.",
            "otro": "Cualquier otro tipo de reclamo: amparo, tutela sindical, consignación, ejecución, cuestiones de "
                    "competencia o trámite, entre otros.",
        },
    },
    "quien_apelo": {
        "type": "choice",
        "instructions": "Según la sentencia, ¿qué partes apelaron la decisión de primera instancia? El trabajador es la "
                        "parte actora; la demandada es el empleador, la ART, la aseguradora o quien haya sido demandado.",
        "criteria": {
            "solo_trabajador": "Solo apeló el trabajador (parte actora), aunque también apelen peritos o letrados por sus honorarios.",
            "solo_demandada": "Solo apeló la parte demandada (o varias codemandadas), aunque también apelen peritos o letrados por sus honorarios.",
            "ambas_partes": "Apelaron tanto el trabajador como la parte demandada.",
            "solo_honorarios": "Solo apelaron peritos o letrados por sus propios honorarios; ninguna de las partes apeló el fondo.",
            "no_se_indica": "La sentencia no permite saber quién apeló.",
        },
    },
    "resultado_apelacion": {
        "type": "choice",
        "instructions": "¿A favor de qué parte resolvió la Cámara las apelaciones sobre el fondo del reclamo?",
        "criteria": {
            "favorece_trabajador": "La Cámara admite total o principalmente los agravios del trabajador, o rechaza los "
                                   "agravios de la demandada y mantiene la condena.",
            "favorece_demandada": "La Cámara admite total o principalmente los agravios de la demandada, o rechaza los "
                                  "agravios del trabajador y mantiene el rechazo de su reclamo.",
            "parcial": "La Cámara admite agravios de las dos partes, o admite solo una parte menor de lo que pedía quien apeló.",
            "sin_cambios": "Apelaron las dos partes y la Cámara rechazó todos los agravios de ambas, confirmando la sentencia.",
            "solo_accesorios": "La Cámara solo decide sobre honorarios, costas, intereses menores o cuestiones de trámite, "
                               "sin resolver el fondo del reclamo.",
        },
    },
    "costas_alzada": {
        "type": "choice",
        "instructions": "¿A cargo de quién impuso la Cámara las costas de la segunda instancia (alzada)?",
        "criteria": {
            "demandada": "Las costas de alzada quedan a cargo de la parte demandada.",
            "trabajador": "Las costas de alzada quedan a cargo del trabajador (parte actora).",
            "por_su_orden": "Las costas de alzada se imponen por su orden o en el orden causado.",
            "distribuidas": "Las costas de alzada se distribuyen entre las partes en proporciones o porcentajes.",
            "no_se_indica": "La sentencia no dice cómo se imponen las costas de alzada.",
        },
    },
}

EN = {
    "tipo_caso": {
        "type": "choice",
        "instructions": "What type of labor claim does this Argentine labor appeals court ruling (written in Spanish) decide?",
        "criteria": {
            "despido": "A claim about the termination of employment: dismissal (direct or constructive), severance pay, "
                       "penalties for unregistered work or for not delivering work certificates.",
            "riesgos_trabajo": "A claim against an ART (occupational risk insurer) for benefits under the Occupational Risks "
                               "Law 24.557 for a work accident or illness, including appeals against medical commission "
                               "decisions (Law 27.348).",
            "accidente_civil": "A claim for full compensation of a work accident or illness based on the Civil Code "
                               "(civil action), not on the special-law tariff.",
            "salarios": "A claim for unpaid wages, wage differences, overtime or collective agreement classification, "
                        "when dismissal is not the main issue.",
            "otro": "Any other claim: injunctions (amparo), union protection, deposit in payment, enforcement, "
                    "jurisdiction or procedural matters, among others.",
        },
    },
    "quien_apelo": {
        "type": "choice",
        "instructions": "According to the ruling, which parties appealed the first-instance decision? The worker is the "
                        "plaintiff (parte actora); the defendant (demandada) is the employer, the ART, the insurer or "
                        "whoever was sued.",
        "criteria": {
            "solo_trabajador": "Only the worker (plaintiff) appealed, even if experts or lawyers also appealed their fees.",
            "solo_demandada": "Only the defendant side appealed (one or several co-defendants), even if experts or lawyers also appealed their fees.",
            "ambas_partes": "Both the worker and the defendant appealed.",
            "solo_honorarios": "Only experts or lawyers appealed their own fees; neither party appealed the merits.",
            "no_se_indica": "The ruling does not say who appealed.",
        },
    },
    "resultado_apelacion": {
        "type": "choice",
        "instructions": "In favor of which party did the court decide the appeals on the merits of the claim?",
        "criteria": {
            "favorece_trabajador": "The court upholds all or most of the worker's grievances, or rejects the defendant's "
                                   "grievances and keeps the award against the defendant.",
            "favorece_demandada": "The court upholds all or most of the defendant's grievances, or rejects the worker's "
                                  "grievances and keeps the dismissal of the worker's claim.",
            "parcial": "The court upholds grievances from both parties, or upholds only a minor part of what the appellant asked.",
            "sin_cambios": "Both parties appealed and the court rejected all grievances from both, confirming the ruling.",
            "solo_accesorios": "The court only decides fees, costs, minor interest issues or procedural matters, without "
                               "deciding the merits of the claim.",
        },
    },
    "costas_alzada": {
        "type": "choice",
        "instructions": "Who did the court order to pay the costs of the appeal (costas de alzada)?",
        "criteria": {
            "demandada": "The defendant pays the appeal costs.",
            "trabajador": "The worker (plaintiff) pays the appeal costs.",
            "por_su_orden": "Each party bears its own appeal costs (por su orden / en el orden causado).",
            "distribuidas": "The appeal costs are split between the parties in proportions or percentages.",
            "no_se_indica": "The ruling does not say how the appeal costs are allocated.",
        },
    },
}

HOLDING = {
    "es": ("¿Qué párrafo de `parrafos` contiene el fundamento principal con el que la Cámara decide la cuestión de fondo "
           "más importante del caso? Elegí el párrafo donde el tribunal razona su decisión; no el relato de los agravios "
           "de las partes, ni la parte resolutiva final, ni el voto que solo adhiere."),
    "en": ("Which paragraph in `parrafos` contains the court's main reasoning for deciding the most important "
           "merits issue of the case? Pick the paragraph where the court explains its decision; not the summary of the "
           "parties' grievances, not the final operative part, and not a vote that merely concurs."),
}
NONE_OPTION = {"es": "Ninguno: la sentencia no decide una cuestión de fondo.",
               "en": "None: the ruling does not decide a merits issue."}


def questions_for(state: dict, lang: str = "es") -> dict:
    """The universal questions plus the holding question, whose options are this fallo's paragraph ids."""
    base = ES if lang == "es" else EN
    options = {pid: None for pid in state["parrafos"]}
    options["ninguno"] = NONE_OPTION[lang]
    return {**base, "holding": {"type": "choice", "instructions": HOLDING[lang], "criteria": options}}


QUESTION_IDS = ["tipo_caso", "quien_apelo", "resultado_apelacion", "costas_alzada", "holding"]


# -- v1: rewritten after the v0 run and the gold labelers' feedback ------------------
# * quien_apelo: answering or replying to the other side's appeal is not appealing.
# * resultado_apelacion split into one outcome per party (literal, no indirection).
# * holding replaced by the role of each paragraph (majority vs. dissent vs. grievance).

_OUTCOME = {
    "no_apelo": "Esta parte no apeló, o solo apelaron sus letrados o peritos por sus propios honorarios.",
    "admitidos": "La Cámara hace lugar a todos los agravios de esta parte o a los principales.",
    "admitidos_en_parte": "La Cámara hace lugar solo a algunos agravios secundarios de esta parte y rechaza los principales.",
    "rechazados": "La Cámara trata y rechaza todos los agravios de esta parte.",
    "no_tratados": "La apelación de esta parte no se trata en el fondo: se declara desierta, mal concedida, "
                   "extemporánea o inapelable.",
}

ES_V1 = {
    "tipo_caso": ES["tipo_caso"],
    "costas_alzada": ES["costas_alzada"],
    "quien_apelo": {
        **ES["quien_apelo"],
        "instructions": ES["quien_apelo"]["instructions"] + " Contestar o replicar el recurso de la otra parte NO es "
                        "apelar. Una apelación declarada desierta o mal concedida sí cuenta como apelación.",
    },
    "agravios_trabajador": {
        "type": "choice",
        "instructions": "¿Qué resolvió la Cámara sobre la apelación del trabajador (parte actora)?",
        "criteria": _OUTCOME,
    },
    "agravios_demandada": {
        "type": "choice",
        "instructions": "¿Qué resolvió la Cámara sobre la apelación de la parte demandada (empleador, ART, aseguradora "
                        "o quien haya sido demandado)?",
        "criteria": _OUTCOME,
    },
    "materia_apelada": {
        "type": "choice",
        "instructions": "¿Sobre qué versan las apelaciones de las partes, tomadas en conjunto?",
        "criteria": {
            "fondo": "Al menos una parte apela el fondo: la condena o el rechazo, la responsabilidad, la incapacidad, "
                     "los rubros o el monto del capital.",
            "solo_accesorios": "Todas las apelaciones se limitan a honorarios, costas, tasa de interés, capitalización "
                               "o actualización del crédito.",
        },
    },
}

ROLE_CRITERIA = {
    "encabezado": "Carátula, número de expediente, fecha, lugar o fórmula de apertura del acuerdo.",
    "antecedentes": "Relato de lo que decidió la sentencia de primera instancia o de los hechos del caso.",
    "agravio": "Relato de lo que sostiene o reclama una de las partes en su apelación (sus agravios o críticas).",
    "razonamiento_mayoria": "Argumentación del tribunal que fundamenta la decisión que finalmente adopta la mayoría.",
    "voto_minoria": "Argumentación de un juez cuya propuesta NO es la que adopta la mayoría (disidencia).",
    "adhesion": "Un juez solo adhiere al voto de otro, sin argumentos propios.",
    "costas_honorarios": "Fundamento o decisión sobre costas u honorarios.",
    "resolutivo": "Parte dispositiva final (RESUELVE / SE RESUELVE) o fórmulas de notificación y firma.",
}


def role_questions(state: dict) -> dict:
    """One Choice per paragraph, all over the same state (one request)."""
    return {
        f"rol_{pid}": {
            "type": "choice",
            "instructions": f"¿Qué función cumple el párrafo `parrafos.{pid}` dentro de esta sentencia?",
            "criteria": ROLE_CRITERIA,
        }
        for pid in state["parrafos"]
    }


V1_IDS = ["tipo_caso", "quien_apelo", "agravios_trabajador", "agravios_demandada", "materia_apelada", "costas_alzada"]


# -- v1.1: what code can decide, code decides -----------------------------------------
# * Majority vs. dissent comes from scripts.labeling.votes (vote structure in code), so the
#   role question only asks the function of the paragraph ("razonamiento" is not split).
# * Party outcomes: "admitidos" covers total or partial; explicit rule for "no_tratados".

_OUTCOME_V11 = {
    "no_apelo": "Esta parte no apeló, o solo apelaron sus letrados o peritos por sus propios honorarios.",
    "admitidos": "La Cámara hace lugar, total o parcialmente, a al menos uno de los agravios de esta parte.",
    "rechazados": "La Cámara examina y rechaza todos los agravios de esta parte.",
    "no_tratados": "La Cámara no examina ningún agravio de esta parte: su apelación se declara desierta, mal concedida, "
                   "extemporánea o inapelable. Si examina al menos un agravio, elegí admitidos o rechazados.",
}

ES_V11 = {
    **{k: v for k, v in ES_V1.items() if not k.startswith("agravios_")},
    "agravios_trabajador": {**ES_V1["agravios_trabajador"], "criteria": _OUTCOME_V11},
    "agravios_demandada": {**ES_V1["agravios_demandada"], "criteria": _OUTCOME_V11},
}

ROLE_CRITERIA_V11 = {
    "encabezado": "Carátula, número de expediente, fecha, lugar, fórmula de apertura del acuerdo o la línea que "
                  "anuncia el voto de un juez.",
    "antecedentes": "Relato de lo que decidió la sentencia de primera instancia o de los hechos del caso.",
    "agravio": "Relato de lo que sostiene o reclama una de las partes en su apelación (sus agravios o críticas).",
    "razonamiento": "Argumentación de un juez sobre las cuestiones del caso: analiza la prueba, el derecho o los "
                    "agravios y propone una solución.",
    "adhesion": "Un juez solo adhiere al voto de otro, sin argumentos propios.",
    "costas_honorarios": "Fundamento o decisión sobre costas u honorarios.",
    "resolutivo": "Parte dispositiva final (RESUELVE / SE RESUELVE) o fórmulas de notificación y firma.",
}


def role_questions_v11(state: dict) -> dict:
    return {
        f"rol_{pid}": {
            "type": "choice",
            "instructions": f"¿Qué función cumple el párrafo `parrafos.{pid}` dentro de esta sentencia?",
            "criteria": ROLE_CRITERIA_V11,
        }
        for pid in state["parrafos"]
    }


def final_role(jev_role: str, pid: str, votes: dict) -> str:
    """Code turns "razonamiento" into majority or dissent by the vote the paragraph belongs to."""
    if jev_role != "razonamiento":
        return jev_role
    minority = {p for v in votes["votos"] if v["juez"] in votes["votos_minoria"] for p in v["parrafos"]}
    return "voto_minoria" if pid in minority else "razonamiento_mayoria"
