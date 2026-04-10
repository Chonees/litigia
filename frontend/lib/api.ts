const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002/api/v1";

export async function searchJurisprudencia(params: {
  descripcion_caso: string;
  jurisdiccion?: string;
  fuero?: string;
  top_k?: number;
}) {
  const res = await fetch(`${API_BASE}/jurisprudencia`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function generateEscrito(params: {
  tipo: string;
  fuero: string;
  tema: string;
  posicion: string;
  jurisdiccion: string;
  datos_caso: string;
}) {
  const res = await fetch(`${API_BASE}/escrito`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function resumirFallo(texto_fallo: string) {
  const res = await fetch(`${API_BASE}/resumen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto_fallo }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function generateOficio(params: {
  destinatario: string;
  motivo: string;
  datos_expediente: string;
  datos_requeridos: string;
}) {
  const res = await fetch(`${API_BASE}/oficio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function analisisPredictivo(params: {
  descripcion_caso: string;
  fuero?: string;
}) {
  const res = await fetch(`${API_BASE}/analisis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export function downloadDocx(base64: string, filename: string) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  const blob = new Blob([byteArray], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
