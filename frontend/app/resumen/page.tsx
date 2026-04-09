"use client";

import { resumirFallo } from "@/lib/api";
import { ResumenForm } from "@/components/forms";
import { ResumenResult } from "@/components/results";
import { ToolPage } from "@/components/tool-page";

export default function ResumenPage() {
  return (
    <ToolPage
      label="Case Summarizer"
      title="Resumir Fallo"
      buttonText="Resumir Fallo"
      onSubmit={async (data) => resumirFallo(data.texto_fallo)}
      renderResult={(result) => <ResumenResult data={result} />}
    >
      <ResumenForm />
    </ToolPage>
  );
}
