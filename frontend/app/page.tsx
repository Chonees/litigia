"use client";

import { useState } from "react";
import {
  searchJurisprudencia,
  generateEscrito,
  resumirFallo,
  generateOficio,
  analisisPredictivo,
  downloadDocx,
} from "@/lib/api";

type Tool =
  | "jurisprudencia"
  | "escrito"
  | "resumen"
  | "oficio"
  | "analisis";

const TOOLS: { id: Tool; label: string; desc: string }[] = [
  {
    id: "jurisprudencia",
    label: "Buscar Jurisprudencia",
    desc: "Encontrar fallos relevantes para tu caso",
  },
  {
    id: "escrito",
    label: "Generar Escrito",
    desc: "Contestaciones, demandas, recursos",
  },
  {
    id: "resumen",
    label: "Resumir Fallo",
    desc: "Resumen estructurado de un fallo",
  },
  {
    id: "oficio",
    label: "Generar Oficio",
    desc: "Oficios a AFIP, bancos, registros",
  },
  {
    id: "analisis",
    label: "Analisis Predictivo",
    desc: "Evaluar chances en base a jurisprudencia",
  },
];

export default function Home() {
  const [activeTool, setActiveTool] = useState<Tool>("jurisprudencia");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData(e.currentTarget);
    const data = Object.fromEntries(formData.entries()) as Record<string, string>;

    try {
      let res;
      switch (activeTool) {
        case "jurisprudencia":
          res = await searchJurisprudencia({
            descripcion_caso: data.descripcion,
            jurisdiccion: data.jurisdiccion || undefined,
            fuero: data.fuero || undefined,
            top_k: 5,
          });
          break;
        case "escrito":
          res = await generateEscrito({
            tipo: data.tipo,
            fuero: data.fuero,
            tema: data.tema,
            posicion: data.posicion,
            jurisdiccion: data.jurisdiccion,
            datos_caso: data.datos_caso,
          });
          break;
        case "resumen":
          res = await resumirFallo(data.texto_fallo);
          break;
        case "oficio":
          res = await generateOficio({
            destinatario: data.destinatario,
            motivo: data.motivo,
            datos_expediente: data.datos_expediente,
            datos_requeridos: data.datos_requeridos,
          });
          break;
        case "analisis":
          res = await analisisPredictivo({
            descripcion_caso: data.descripcion,
            fuero: data.fuero || undefined,
          });
          break;
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Tool selector */}
      <div className="flex flex-wrap gap-3">
        {TOOLS.map((tool) => (
          <button
            key={tool.id}
            onClick={() => {
              setActiveTool(tool.id);
              setResult(null);
              setError(null);
            }}
            className={`px-4 py-3 rounded-lg border-2 transition-all text-left ${
              activeTool === tool.id
                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-white"
                : "border-gray-200 bg-white hover:border-[var(--color-primary-light)]"
            }`}
          >
            <div className="font-semibold text-sm">{tool.label}</div>
            <div
              className={`text-xs mt-1 ${
                activeTool === tool.id
                  ? "text-gray-200"
                  : "text-[var(--color-text-muted)]"
              }`}
            >
              {tool.desc}
            </div>
          </button>
        ))}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-md p-6 space-y-4">
        <h2 className="text-xl font-bold text-[var(--color-primary)]">
          {TOOLS.find((t) => t.id === activeTool)?.label}
        </h2>

        {activeTool === "jurisprudencia" && <JurisprudenciaForm />}
        {activeTool === "escrito" && <EscritoForm />}
        {activeTool === "resumen" && <ResumenForm />}
        {activeTool === "oficio" && <OficioForm />}
        {activeTool === "analisis" && <AnalisisForm />}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-[var(--color-primary)] text-white rounded-lg font-semibold hover:bg-[var(--color-primary-light)] disabled:opacity-50 transition-colors"
        >
          {loading ? "Procesando..." : "Enviar"}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="text-lg font-bold text-[var(--color-primary)] mb-4">
            Resultado
          </h3>
          {activeTool === "jurisprudencia" && (
            <JurisprudenciaResult data={result} />
          )}
          {activeTool === "escrito" && <EscritoResult data={result} />}
          {activeTool === "resumen" && <ResumenResult data={result} />}
          {activeTool === "oficio" && (
            <pre className="whitespace-pre-wrap font-serif text-sm">
              {(result as { contenido?: string }).contenido}
            </pre>
          )}
          {activeTool === "analisis" && <AnalisisResult data={result} />}
        </div>
      )}
    </div>
  );
}

// --- Form Components ---

function JurisprudenciaForm() {
  return (
    <>
      <textarea
        name="descripcion"
        placeholder="Describí el caso en lenguaje natural... Ej: Mi cliente sufrió un accidente laboral en una obra. La ART le rechazó el siniestro."
        className="w-full h-32 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none"
        required
      />
      <div className="grid grid-cols-2 gap-4">
        <select name="jurisdiccion" className="p-2 border rounded-lg">
          <option value="">Jurisdiccion (todas)</option>
          <option value="CABA">CABA</option>
          <option value="PBA">Provincia de Buenos Aires</option>
          <option value="Nacional">Nacional</option>
          <option value="Federal">Federal</option>
        </select>
        <select name="fuero" className="p-2 border rounded-lg">
          <option value="">Fuero (todos)</option>
          <option value="civil">Civil</option>
          <option value="laboral">Laboral</option>
          <option value="penal">Penal</option>
          <option value="comercial">Comercial</option>
          <option value="contencioso_administrativo">Cont. Administrativo</option>
          <option value="familia">Familia</option>
        </select>
      </div>
    </>
  );
}

function EscritoForm() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4">
        <select name="tipo" className="p-2 border rounded-lg" required>
          <option value="">Tipo de escrito</option>
          <option value="contestacion_demanda">Contestacion de demanda</option>
          <option value="demanda">Demanda</option>
          <option value="recurso_apelacion">Recurso de apelacion</option>
          <option value="recurso_extraordinario">Recurso extraordinario</option>
          <option value="amparo">Amparo</option>
          <option value="medida_cautelar">Medida cautelar</option>
          <option value="alegato">Alegato</option>
        </select>
        <select name="fuero" className="p-2 border rounded-lg" required>
          <option value="">Fuero</option>
          <option value="civil">Civil</option>
          <option value="laboral">Laboral</option>
          <option value="penal">Penal</option>
          <option value="comercial">Comercial</option>
          <option value="familia">Familia</option>
        </select>
        <select name="posicion" className="p-2 border rounded-lg" required>
          <option value="">Posicion procesal</option>
          <option value="actor">Actor</option>
          <option value="demandado">Demandado</option>
          <option value="tercero">Tercero</option>
        </select>
        <select name="jurisdiccion" className="p-2 border rounded-lg" required>
          <option value="">Jurisdiccion</option>
          <option value="CABA">CABA</option>
          <option value="PBA">Provincia de Buenos Aires</option>
          <option value="Nacional">Nacional</option>
        </select>
      </div>
      <input
        name="tema"
        placeholder="Tema: ej. Danos y perjuicios por accidente de transito"
        className="w-full p-2 border rounded-lg"
        required
      />
      <textarea
        name="datos_caso"
        placeholder="Describí los datos del caso: hechos, partes, pretension..."
        className="w-full h-32 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none"
        required
      />
    </>
  );
}

function ResumenForm() {
  return (
    <textarea
      name="texto_fallo"
      placeholder="Pegá el texto completo del fallo aca..."
      className="w-full h-48 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none font-mono text-sm"
      required
    />
  );
}

function OficioForm() {
  return (
    <>
      <input
        name="destinatario"
        placeholder="Destinatario: ej. AFIP, Banco Nacion, Registro de la Propiedad"
        className="w-full p-2 border rounded-lg"
        required
      />
      <input
        name="motivo"
        placeholder="Motivo: ej. Solicitar informacion fiscal del demandado"
        className="w-full p-2 border rounded-lg"
        required
      />
      <input
        name="datos_expediente"
        placeholder="Expediente: ej. Expte 12345/2024, Juzgado Civil 43, Sec. 85"
        className="w-full p-2 border rounded-lg"
        required
      />
      <textarea
        name="datos_requeridos"
        placeholder="Datos requeridos: ej. Informacion fiscal del CUIT 20-12345678-9, ultimas 5 DDJJ"
        className="w-full h-24 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none"
        required
      />
    </>
  );
}

function AnalisisForm() {
  return (
    <>
      <textarea
        name="descripcion"
        placeholder="Describí el caso para analizar chances: ej. Despido sin causa, empleado con 8 anos de antiguedad, sueldo $500k..."
        className="w-full h-32 p-3 border rounded-lg resize-none focus:ring-2 focus:ring-[var(--color-primary)] focus:outline-none"
        required
      />
      <select name="fuero" className="p-2 border rounded-lg">
        <option value="">Fuero (opcional)</option>
        <option value="civil">Civil</option>
        <option value="laboral">Laboral</option>
        <option value="penal">Penal</option>
        <option value="comercial">Comercial</option>
      </select>
    </>
  );
}

// --- Result Components ---

function JurisprudenciaResult({ data }: { data: Record<string, unknown> }) {
  const fallos = (data.fallos ?? []) as Array<{
    tribunal: string;
    fecha: string;
    caratula: string;
    resumen: string;
    argumento_clave: string;
    cita_textual: string;
    score: number;
  }>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-text-muted)]">
        {(data.total_encontrados as number) ?? 0} fallos encontrados |
        Terminos: {((data.query_expandida as string[]) ?? []).join(", ")}
      </p>
      {fallos.map((fallo, i) => (
        <div key={i} className="border-l-4 border-[var(--color-accent)] pl-4 py-2">
          <div className="font-semibold">{fallo.caratula}</div>
          <div className="text-sm text-[var(--color-text-muted)]">
            {fallo.tribunal} | {fallo.fecha} | Relevancia:{" "}
            {(fallo.score * 100).toFixed(0)}%
          </div>
          <p className="mt-2 text-sm">{fallo.resumen}</p>
          <p className="mt-1 text-sm font-semibold">
            Argumento clave: {fallo.argumento_clave}
          </p>
          <blockquote className="mt-1 text-sm italic border-l-2 border-gray-300 pl-2 text-gray-600">
            &ldquo;{fallo.cita_textual}&rdquo;
          </blockquote>
        </div>
      ))}
      {fallos.length === 0 && (
        <p className="text-gray-500">No se encontraron fallos relevantes.</p>
      )}
    </div>
  );
}

function EscritoResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-4">
      <pre className="whitespace-pre-wrap font-serif text-sm bg-gray-50 p-4 rounded-lg max-h-[600px] overflow-y-auto">
        {data.contenido_texto as string}
      </pre>
      {data.archivo_docx_base64 && (
        <button
          onClick={() =>
            downloadDocx(data.archivo_docx_base64 as string, "escrito_litigia.docx")
          }
          className="px-6 py-2 bg-[var(--color-accent)] text-white rounded-lg font-semibold hover:opacity-90"
        >
          Descargar .docx
        </button>
      )}
    </div>
  );
}

function ResumenResult({ data }: { data: Record<string, unknown> }) {
  const sections = [
    { key: "hechos", label: "Hechos" },
    { key: "cuestion_juridica", label: "Cuestion Juridica" },
    { key: "argumentos_actor", label: "Argumentos del Actor" },
    { key: "argumentos_demandado", label: "Argumentos del Demandado" },
    { key: "resolucion", label: "Resolucion" },
    { key: "doctrina_aplicada", label: "Doctrina Aplicada" },
  ];

  return (
    <div className="space-y-3">
      {sections.map(({ key, label }) => (
        <div key={key}>
          <h4 className="font-bold text-[var(--color-primary)]">{label}</h4>
          <p className="text-sm">{data[key] as string}</p>
        </div>
      ))}
      {(data.articulos_citados as string[])?.length > 0 && (
        <div>
          <h4 className="font-bold text-[var(--color-primary)]">
            Articulos Citados
          </h4>
          <ul className="list-disc list-inside text-sm">
            {(data.articulos_citados as string[]).map((art, i) => (
              <li key={i}>{art}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AnalisisResult({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 p-4 rounded-lg text-center">
          <div className="text-3xl font-bold text-[var(--color-primary)]">
            {data.fallos_analizados as number}
          </div>
          <div className="text-sm text-gray-600">Fallos analizados</div>
        </div>
        <div className="bg-green-50 p-4 rounded-lg text-center">
          <div className="text-3xl font-bold text-green-700">
            {((data.porcentaje_favorable as number) ?? 0).toFixed(0)}%
          </div>
          <div className="text-sm text-gray-600">Favorable</div>
        </div>
      </div>
      <div>
        <h4 className="font-bold">Argumento mas fuerte</h4>
        <p className="text-sm">{data.argumento_mas_fuerte as string}</p>
      </div>
      {((data.riesgos as string[]) ?? []).length > 0 && (
        <div>
          <h4 className="font-bold text-red-600">Riesgos</h4>
          <ul className="list-disc list-inside text-sm">
            {(data.riesgos as string[]).map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
