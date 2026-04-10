import { supabase } from "@/lib/supabase";

export type SavedItemType = "jurisprudencia" | "escrito" | "resumen" | "oficio" | "analisis";

export interface SavedItem {
  id: string;
  user_id: string;
  type: SavedItemType;
  title: string;
  data: {
    input: Record<string, unknown>;
    output: Record<string, unknown>;
  };
  created_at: string;
}

/** Strip heavy fields (raw Claude responses) to keep payload under Supabase limits */
function stripHeavyFields(output: Record<string, unknown>): Record<string, unknown> {
  const stripped = { ...output };

  // Remove synthesizer raw thinking (~32KB)
  delete stripped.synth_thinking;

  // Strip heavy fields — narrative is rebuilt from parsed fields client-side
  const detalle = stripped.fallos_analizados_detalle;
  if (Array.isArray(detalle)) {
    stripped.fallos_analizados_detalle = detalle.map(
      (f: Record<string, unknown>) => {
        const { agent_thinking, _raw_claude_response, _original_texto, ...rest } = f;
        return rest;
      },
    );
  }

  return stripped;
}

/** Auto-save — fire and forget, never blocks UI */
export function autoSave(
  type: SavedItemType,
  title: string,
  output: Record<string, unknown>,
  input: Record<string, unknown>,
) {
  (async () => {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) return;

    const safeOutput = type === "analisis" ? stripHeavyFields(output) : output;

    const { error } = await supabase.from("saved_items").insert({
      user_id: user.id,
      type,
      title,
      data: { input, output: safeOutput },
    });

    if (error) {
      console.error("[autoSave] Supabase error:", error.message, { type, title });
    }
  })().catch((err) => {
    console.error("[autoSave] Unexpected error:", err);
  });
}

export async function getSavedItems(type?: SavedItemType): Promise<SavedItem[]> {
  let query = supabase
    .from("saved_items")
    .select("*")
    .order("created_at", { ascending: false });

  if (type) query = query.eq("type", type);

  const { data, error } = await query;
  if (error) throw new Error(error.message);
  return (data ?? []) as SavedItem[];
}

export async function deleteSavedItem(id: string) {
  const { error } = await supabase.from("saved_items").delete().eq("id", id);
  if (error) throw new Error(error.message);
}
