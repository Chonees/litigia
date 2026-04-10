"use client";

import { searchJurisprudencia } from "@/lib/api";
import { JurisprudenciaForm } from "@/components/forms";
import { JurisprudenciaResult } from "@/components/results";
import { ToolPage } from "@/components/tool-page";

export default function JurisprudenciaPage() {
  return (
    <ToolPage
      label="Archive Search"
      title="Jurisprudencia"
      buttonText="Buscar Precedentes"
      saveType="jurisprudencia"
      getSaveTitle={(data) => data.descripcion?.slice(0, 80) || "Búsqueda"}
      onSubmit={async (data) =>
        searchJurisprudencia({
          descripcion_caso: data.descripcion,
          jurisdiccion: data.jurisdiccion || undefined,
          fuero: data.fuero || undefined,
          top_k: parseInt(data.top_k || "5"),
        })
      }
      renderResult={(result) => <JurisprudenciaResult data={result} />}
    >
      <JurisprudenciaForm />
    </ToolPage>
  );
}
