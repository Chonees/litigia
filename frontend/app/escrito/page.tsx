"use client";

import { generateEscrito } from "@/lib/api";
import { EscritoForm } from "@/components/forms";
import { EscritoResult } from "@/components/results";
import { ToolPage } from "@/components/tool-page";

export default function EscritoPage() {
  return (
    <ToolPage
      label="Drafting Engine"
      title="Escrito Judicial"
      buttonText="Generar Escrito"
      onSubmit={async (data) =>
        generateEscrito({
          tipo: data.tipo,
          fuero: data.fuero,
          tema: data.tema,
          posicion: data.posicion,
          jurisdiccion: data.jurisdiccion,
          datos_caso: data.datos_caso,
        })
      }
      renderResult={(result) => <EscritoResult data={result} />}
    >
      <EscritoForm />
    </ToolPage>
  );
}
