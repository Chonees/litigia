"use client";

import { generateOficio } from "@/lib/api";
import { OficioForm } from "@/components/forms";
import { OficioResult } from "@/components/results";
import { ToolPage } from "@/components/tool-page";

export default function OficioPage() {
  return (
    <ToolPage
      label="Official Communication"
      title="Oficio Judicial"
      buttonText="Generar Oficio"
      onSubmit={async (data) =>
        generateOficio({
          destinatario: data.destinatario,
          motivo: data.motivo,
          datos_expediente: data.datos_expediente,
          datos_requeridos: data.datos_requeridos,
        })
      }
      renderResult={(result) => <OficioResult data={result} />}
    >
      <OficioForm />
    </ToolPage>
  );
}
