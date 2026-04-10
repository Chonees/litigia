"""Benchmark precision across 50 practice areas for litigation firm."""
import sys, asyncio, time
sys.stdout.reconfigure(encoding="utf-8")

from app.services.analysis import _search_cases

QUERIES = [
    {"q": "Despido sin causa empleada embarazada art. 178 LCT indemnizacion agravada", "kw": ["embaraz","178","maternidad"], "f": "laboral"},
    {"q": "Despido delegado gremial sin exclusion tutela sindical art. 52 ley 23.551", "kw": ["delegado","tutela","sindical","23.551"], "f": "laboral"},
    {"q": "Tercerizacion fraudulenta solidaridad grupo economico art. 31 LCT", "kw": ["tercerizacion","solidari","grupo econ","art. 31"], "f": "laboral"},
    {"q": "Accidente laboral ART rechaza siniestro ley 24.557", "kw": ["accidente","ART","siniestro","24.557"], "f": "laboral"},
    {"q": "Inconstitucionalidad art. 39 ley 24.557 reparacion integral trabajador", "kw": ["inconstitucionalidad","24.557","reparacion integral","art. 39"], "f": "laboral"},
    {"q": "Despido durante licencia enfermedad inculpable art. 213 LCT reserva puesto", "kw": ["enfermedad","inculpable","art. 213","reserva"], "f": "laboral"},
    {"q": "Diferencias salariales incorrecta categorizacion convenio colectivo", "kw": ["diferencias salariales","categorizacion","convenio"], "f": "laboral"},
    {"q": "Mobbing acoso laboral dano moral resarcimiento trabajador", "kw": ["acoso","mobbing","dano moral","hostigamiento"], "f": "laboral"},
    {"q": "Horas extras no pagadas jornada laboral art. 201 LCT trabajo nocturno", "kw": ["horas extra","jornada","art. 201","nocturno"], "f": "laboral"},
    {"q": "Despido por matrimonio art. 182 LCT presuncion indemnizacion especial", "kw": ["matrimonio","art. 182","presuncion"], "f": "laboral"},
    {"q": "Trabajo no registrado empleo en negro multas ley 24.013 arts 8 9 15", "kw": ["no registrado","negro","24.013"], "f": "laboral"},
    {"q": "Accidente in itinere desvio trayecto habitual trabajador", "kw": ["in itinere","desvio","trayecto"], "f": "laboral"},
    {"q": "Despido discriminatorio por enfermedad HIV SIDA ley 23.798", "kw": ["discriminat","HIV","SIDA","23.798"], "f": "laboral"},
    {"q": "Contrato eventual fraude laboral art. 99 LCT relacion permanente", "kw": ["eventual","fraude","art. 99","permanente"], "f": "laboral"},
    {"q": "Viajante de comercio comisiones impagas estatuto especial ley 14.546", "kw": ["viajante","comision","14.546"], "f": "laboral"},
    {"q": "Mala praxis medica consentimiento informado dano moral responsabilidad sanatorio", "kw": ["mala praxis","consentimiento","sanatorio","medic"], "f": "civil"},
    {"q": "Danos y perjuicios accidente transito responsabilidad objetiva art. 1757 CCyCN", "kw": ["accidente","transito","responsabilidad","1757"], "f": "civil"},
    {"q": "Ejecucion hipotecaria nulidad subasta precio vil deudor", "kw": ["hipotecaria","ejecucion","subasta","precio vil"], "f": "civil"},
    {"q": "Dano ambiental colectivo remediacion art. 41 CN ley 25.675", "kw": ["ambiental","remediacion","art. 41","25.675"], "f": "civil"},
    {"q": "Responsabilidad del Estado por falta de servicio danos ruta nacional", "kw": ["estado","falta de servicio","ruta","responsabilidad"], "f": "civil"},
    {"q": "Prescripcion adquisitiva usucapion inmueble posesion veinteanal", "kw": ["prescripcion adquisitiva","usucapion","posesion"], "f": "civil"},
    {"q": "Alimentos provisorios cuota alimentaria menores interes superior del nino", "kw": ["alimentos","cuota","menores","interes superior"], "f": None},
    {"q": "Divorcio distribucion bienes gananciales sociedad conyugal", "kw": ["divorcio","gananciales","sociedad conyugal","bienes"], "f": None},
    {"q": "Danos punitivos art. 52 bis ley 24.240 defensa consumidor", "kw": ["danos punitivos","24.240","consumidor","52 bis"], "f": "civil"},
    {"q": "Ruidos molestos dano moral vecinos inmisiones art. 1973 CCyCN", "kw": ["ruidos","inmisiones","vecin","1973"], "f": "civil"},
    {"q": "Responsabilidad directores sociedad anonima art. 274 ley 19.550", "kw": ["director","responsabilidad","19.550","sociedad anonima"], "f": "comercial"},
    {"q": "Medida cautelar innovativa contra resolucion asamblea accionistas", "kw": ["cautelar","asamblea","accionista","intervencion"], "f": "comercial"},
    {"q": "Concurso preventivo cramdown salvataje empresa verificacion creditos", "kw": ["concurso","cramdown","verificacion","salvataje"], "f": "comercial"},
    {"q": "Quiebra extension responsabilidad socios administradores art. 161 ley 24.522", "kw": ["quiebra","extension","responsabilidad","24.522"], "f": "comercial"},
    {"q": "Contrato de franquicia resolucion abusiva indemnizacion franquiciado", "kw": ["franquicia","resolucion","indemnizacion","franquiciad"], "f": "comercial"},
    {"q": "Recurso extraordinario federal CSJN arbitrariedad sentencia gravedad institucional ley 48", "kw": ["recurso extraordinario","arbitrariedad","gravedad institucional","ley 48"], "f": None},
    {"q": "Accion de amparo art. 43 CN contra acto autoridad publica", "kw": ["amparo","art. 43","autoridad publica","legitimacion"], "f": None},
    {"q": "Competencia originaria Corte Suprema art. 117 CN conflicto provincias", "kw": ["competencia originaria","art. 117","corte suprema","provincia"], "f": None},
    {"q": "Habeas corpus privacion ilegitima libertad art. 43 CN", "kw": ["habeas corpus","privacion","libertad","art. 43"], "f": None},
    {"q": "Accion declarativa inconstitucionalidad ley impositiva provincial", "kw": ["declarativa","inconstitucionalidad","impositiva","provincial"], "f": None},
    {"q": "Empleo publico cesantia estabilidad propia reincorporacion", "kw": ["empleo publico","cesantia","estabilidad","reincorporacion"], "f": None},
    {"q": "Expropiacion irregular indemnizacion justa previa art. 17 CN", "kw": ["expropiacion","indemnizacion","justa","art. 17"], "f": None},
    {"q": "Evasion fiscal ley 24.769 penal tributario condiciones objetivas punibilidad", "kw": ["evasion","24.769","penal tributario","punibilidad"], "f": "penal"},
    {"q": "Lavado de activos ley 25.246 encubrimiento UIF reporte operacion sospechosa", "kw": ["lavado","25.246","encubrimiento","UIF","sospechosa"], "f": "penal"},
    {"q": "Estafa procesal falsedad documental art. 172 codigo penal", "kw": ["estafa","falsedad","documental","art. 172"], "f": "penal"},
    {"q": "Seguro de vida rechazo siniestro reticencia art. 5 ley 17.418", "kw": ["seguro","siniestro","reticencia","17.418"], "f": "civil"},
    {"q": "Seguro automotor franquicia oponibilidad tercero victima accidente", "kw": ["seguro","franquicia","oponibilidad","tercero","victima"], "f": "civil"},
    {"q": "Marca registrada confusion marcaria competencia desleal ley 22.362", "kw": ["marca","confusion","competencia desleal","22.362"], "f": "civil"},
    {"q": "Derecho de autor plagio obra literaria ley 11.723 indemnizacion", "kw": ["autor","plagio","11.723","obra"], "f": "civil"},
    {"q": "Resolucion contrato incumplimiento obligacion reciproca art. 1083 CCyCN pacto comisorio", "kw": ["resolucion","incumplimiento","1083","pacto comisorio"], "f": "civil"},
    {"q": "Contrato distribucion comercial rescision intempestiva preaviso razonable lucro cesante", "kw": ["distribucion","rescision","preaviso","lucro cesante"], "f": "comercial"},
    {"q": "Locacion inmueble urbano desalojo falta de pago ley 27.551", "kw": ["locacion","desalojo","falta de pago","27.551"], "f": "civil"},
    {"q": "Fideicomiso inmobiliario incumplimiento constructor obligacion escriturar", "kw": ["fideicomiso","constructor","escritur","incumplimiento"], "f": "civil"},
    {"q": "Determinacion de oficio AFIP impuesto ganancias recurso tribunal fiscal", "kw": ["AFIP","ganancias","tribunal fiscal","determinacion"], "f": None},
    {"q": "Repeticion pago indebido tributo inconstitucional prescripcion", "kw": ["repeticion","pago indebido","tributo","inconstitucional"], "f": None},
]

async def run():
    total = len(QUERIES)
    start = time.time()
    results = []

    for i, q in enumerate(QUERIES):
        try:
            docs = await _search_cases(q["q"], q["f"], top_k=10)
        except Exception as e:
            print(f"  [{i+1}/{total}] ERROR: {str(e)[:50]}", flush=True)
            results.append({"q": q["q"][:60], "precision": 0, "n": 0})
            continue

        relevant = 0
        for d in docs:
            texto = (d.get("texto","") + " " + d.get("caratula","") + " " + d.get("sumario","")).lower()
            found = [kw for kw in q["kw"] if kw.lower() in texto]
            if len(found) / len(q["kw"]) >= 0.3:
                relevant += 1

        prec = (relevant / len(docs) * 100) if docs else 0
        results.append({"q": q["q"][:60], "precision": prec, "n": len(docs)})

        status = "EXCELENTE" if prec >= 80 else "BUENA" if prec >= 60 else "ACEPTABLE" if prec >= 40 else "MALA"
        print(f"  [{i+1}/{total}] {prec:>3.0f}% [{status:>9}] {q['q'][:70]}", flush=True)

    elapsed = time.time() - start

    print(f"\n{'='*100}")
    print(f"BENCHMARK: {total} queries | {elapsed:.0f}s total | {elapsed/total:.1f}s/query")
    print(f"{'='*100}")

    excelente = sum(1 for r in results if r["precision"] >= 80)
    buena = sum(1 for r in results if 60 <= r["precision"] < 80)
    aceptable = sum(1 for r in results if 40 <= r["precision"] < 60)
    mala = sum(1 for r in results if r["precision"] < 40)
    avg = sum(r["precision"] for r in results) / len(results)

    print(f"\n  EXCELENTE (80%+):   {excelente}/{total} ({excelente/total*100:.0f}%)")
    print(f"  BUENA (60-79%):     {buena}/{total} ({buena/total*100:.0f}%)")
    print(f"  ACEPTABLE (40-59%): {aceptable}/{total} ({aceptable/total*100:.0f}%)")
    print(f"  MALA (<40%):        {mala}/{total} ({mala/total*100:.0f}%)")
    print(f"\n  PROMEDIO GENERAL: {avg:.1f}%")

    print(f"\n  TOP 5 mejores:")
    by_prec = sorted(results, key=lambda r: r["precision"], reverse=True)
    for r in by_prec[:5]:
        print(f"    {r['precision']:>3.0f}% | {r['q']}")

    print(f"\n  BOTTOM 5 peores:")
    for r in by_prec[-5:]:
        print(f"    {r['precision']:>3.0f}% | {r['q']}")

if __name__ == "__main__":
    asyncio.run(run())
