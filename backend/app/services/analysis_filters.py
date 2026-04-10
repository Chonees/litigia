"""Quality pre-filter for search results (no LLM calls).

Classifies fallos as substantive or auto-inadmisible based on text patterns
BEFORE sending them to reader agents. Saves ~$0.03 per filtered fallo.
"""


def filter_low_quality(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Classify search results as substantive or auto-inadmisible.

    Returns (substantive_results, auto_classified_inadmisibles).

    SKIP conditions (any one triggers skip):
    - texto length < 500 chars: too short to contain substantive content
    - "art. 280" or "articulo 280" AND length < 2000 chars: certiorari dismissal
    - "desestimase" or "desestimase" (accent variant) AND length < 1500 chars
    - "desistimiento" or "dase por desistido" AND length < 1500 chars
    - "caducidad de instancia" AND length < 1500 chars

    All skip conditions use lowercase matching on the texto field.
    """
    substantive: list[dict] = []
    noise: list[dict] = []

    for r in results:
        texto = r.get("texto", "") or ""
        texto_lower = texto.lower()
        length = len(texto)
        reason = None

        if length < 500:
            reason = f"texto muy corto ({length} chars)"

        elif (
            ("art. 280" in texto_lower or "articulo 280" in texto_lower or "artículo 280" in texto_lower)
            and length < 2000
        ):
            reason = f"art. 280 CPCCN ({length} chars) - certiorari sin fundamentacion"

        elif (
            ("desestimase" in texto_lower or "desestímase" in texto_lower)
            and length < 1500
        ):
            reason = f"desestimacion breve ({length} chars)"

        elif (
            ("desistimiento" in texto_lower or "dase por desistido" in texto_lower)
            and length < 1500
        ):
            reason = f"desistimiento ({length} chars)"

        elif "caducidad de instancia" in texto_lower and length < 1500:
            reason = f"caducidad de instancia ({length} chars)"

        if reason:
            caratula = r.get("caratula", "N/D")[:60]
            print(
                f"  [QFilter] SKIP: {caratula} -- {reason}",
                flush=True,
            )
            noise.append(r)
        else:
            substantive.append(r)

    total = len(results)
    n_pass = len(substantive)
    n_skip = len(noise)
    print(
        f"  [QFilter] {n_pass}/{total} passed quality check "
        f"({n_skip} auto-classified as inadmisible, saved ~${n_skip * 0.03:.2f})",
        flush=True,
    )
    return substantive, noise


def make_auto_inadmisible(fallo: dict, index: int) -> dict:
    """Build a minimal FalloAnalizado-compatible dict for a pre-filtered fallo."""
    texto = fallo.get("texto", "") or ""
    length = len(texto)
    return {
        "caratula": fallo.get("caratula", "N/D"),
        "tribunal": fallo.get("tribunal", "N/D"),
        "fecha": fallo.get("fecha", "N/D"),
        "resultado": "inadmisible",
        "normas_citadas": [],
        "precedentes_citados": [],
        "via_procesal": "pre-filtrado automatico",
        "doctrina_aplicada": "",
        "hechos_determinantes": "",
        "prueba_decisiva": "",
        "quantum": "",
        "votos": "",
        "estrategia": "",
        "argumento_clave": "",
        "razon_resultado": (
            f"Pre-filtrado automatico: texto de {length} caracteres. "
            "Sin contenido sustantivo (ruido procesal: art. 280, desestimacion, "
            "desistimiento o caducidad). No se envio a agente lector."
        ),
        "relevancia_cliente": "Ninguna - fallo sin contenido de fondo.",
        "score": fallo.get("score", 0.0),
        "source_id": fallo.get("source_id", fallo.get("id", "")),
        "agent_thinking": "",
        "reasoning": "",
        "_raw_claude_response": "",
        "_original_texto": texto,
        "_auto_filtered": True,
    }
