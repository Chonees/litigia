"""Human-readable summary formatters for the analysis pipeline.

These pure functions convert parsed JSON dicts into readable text for
frontend display and transparency mode.
"""


def build_agent_summary(analysis: dict, caratula: str = "") -> str:
    """Build a human-readable summary from parsed analysis fields (no JSON)."""
    lines = []
    resultado = analysis.get("resultado", "N/D")
    resultado_map = {"favorable": "FAVORABLE", "desfavorable": "DESFAVORABLE", "parcial": "PARCIAL", "inadmisible": "INADMISIBLE"}
    lines.append(f"Resultado: {resultado_map.get(resultado, resultado)}")

    if caratula and caratula != "N/D":
        lines.append(f"Carátula: {caratula}")

    via = analysis.get("via_procesal", "")
    if via and via != "N/D":
        lines.append(f"Vía procesal: {via}")

    doctrina = analysis.get("doctrina_aplicada", "")
    if doctrina and doctrina != "N/D":
        lines.append(f"Doctrina: {doctrina}")

    hechos = analysis.get("hechos_determinantes", "")
    if hechos and hechos != "N/D":
        lines.append(f"\nHechos determinantes:\n{hechos}")

    argumento = analysis.get("argumento_clave", "")
    if argumento and argumento != "N/D":
        lines.append(f"\nArgumento clave:\n{argumento}")

    relevancia = analysis.get("relevancia_cliente", "")
    if relevancia and relevancia != "N/D":
        lines.append(f"\nRelevancia para el caso:\n{relevancia}")

    normas = analysis.get("normas_citadas", [])
    if normas:
        lines.append(f"\nNormas: {', '.join(normas[:8])}")

    quantum = analysis.get("quantum", "")
    if quantum and quantum != "N/D":
        lines.append(f"Quantum/Costas: {quantum}")

    return "\n".join(lines)


def build_synth_summary(synthesis: dict) -> str:
    """Build a human-readable summary from synthesizer output (no JSON)."""
    lines = []

    # Stats
    total = synthesis.get("total_analizados", 0)
    fav = synthesis.get("favorables", 0)
    desfav = synthesis.get("desfavorables", 0)
    parc = synthesis.get("parciales", 0)
    inadm = synthesis.get("inadmisibles", 0)
    pct = synthesis.get("porcentaje_favorable", 0)
    if total:
        lines.append(f"ESTADÍSTICAS: {total} fallos analizados")
        lines.append(f"  Favorables: {fav} | Desfavorables: {desfav} | Parciales: {parc} | Inadmisibles: {inadm}")
        lines.append(f"  Probabilidad favorable: {pct:.0f}%")

    # Recommendation (most important — goes early)
    recomendacion = synthesis.get("recomendacion_estrategica", "")
    if recomendacion:
        lines.append(f"\nRECOMENDACIÓN ESTRATÉGICA:\n{recomendacion}")

    # Winning strategies
    estrategias = synthesis.get("estrategias_exitosas", [])
    if estrategias:
        lines.append("\nESTRATEGIAS EXITOSAS:")
        for e in estrategias[:5]:
            nombre = e.get("estrategia", "")
            tasa = e.get("tasa_exito", 0)
            freq = e.get("frecuencia", 0)
            lines.append(f"  • {nombre} (éxito: {tasa:.0f}%, {freq} casos)")

    # Failed strategies
    fracasadas = synthesis.get("estrategias_fracasadas", [])
    if fracasadas:
        lines.append("\nESTRATEGIAS QUE FRACASARON:")
        for e in fracasadas[:3]:
            nombre = e.get("estrategia", "")
            tasa = e.get("tasa_exito", 0)
            lines.append(f"  • {nombre} (éxito: {tasa:.0f}%)")

    # Factual patterns
    patron_fav = synthesis.get("patron_factico_favorable", "")
    if patron_fav:
        lines.append(f"\nPATRÓN DE CASOS FAVORABLES:\n{patron_fav}")
    patron_desfav = synthesis.get("patron_factico_desfavorable", "")
    if patron_desfav:
        lines.append(f"\nPATRÓN DE CASOS DESFAVORABLES:\n{patron_desfav}")

    # Key norms
    normas = synthesis.get("normas_clave", [])
    if normas:
        lines.append(f"\nNORMAS CLAVE: {', '.join(normas[:10])}")

    # Precedents to cite
    precedentes = synthesis.get("precedentes_para_citar", [])
    if precedentes:
        lines.append("\nPRECEDENTES PARA CITAR:")
        for p in precedentes[:8]:
            lines.append(f"  • {p}")

    # Required evidence
    prueba = synthesis.get("prueba_necesaria", [])
    if prueba:
        lines.append("\nPRUEBA NECESARIA:")
        for p in prueba[:5]:
            lines.append(f"  • {p}")

    # Risks
    riesgos = synthesis.get("riesgos", [])
    if riesgos:
        lines.append("\nRIESGOS:")
        for r in riesgos[:5]:
            lines.append(f"  • {r}")

    # Contradictions
    contradicciones = synthesis.get("contradicciones", [])
    if contradicciones:
        lines.append("\nCONTRADICCIONES JURISPRUDENCIALES:")
        for c in contradicciones[:5]:
            lines.append(f"  • {c}")

    # Quantum & costs
    quantum = synthesis.get("rango_quantum", "")
    if quantum and quantum != "N/D":
        lines.append(f"\nESTIMACIÓN DE MONTOS: {quantum}")
    costas = synthesis.get("patron_costas", "")
    if costas and costas != "N/D":
        lines.append(f"PATRÓN DE COSTAS: {costas}")

    # Dissents
    disidencias = synthesis.get("disidencias_relevantes", [])
    if disidencias:
        lines.append("\nDISIDENCIAS RELEVANTES:")
        for d in disidencias[:3]:
            lines.append(f"  • {d}")

    return "\n".join(lines) if lines else "Síntesis completada."
