/**
 * Litigia Sovereign — Design Tokens
 *
 * Single source of truth for the entire UI.
 * Light minimal theme with institutional gold accents.
 */

export const colors = {
  // Surfaces
  bg: "#FAFAF8",
  surface: "#FFFFFF",
  containerLow: "#F0EDE6",
  containerHigh: "#FFFFFF",

  // Primary — institutional gold
  primary: "#9A7B2D",
  primaryContainer: "#B08A30",
  onPrimary: "#FFFFFF",

  // Text
  onSurface: "#1A1A1A",
  onSurfaceVariant: "#4A4640",
  muted: "#8C8579",

  // Borders
  outline: "#D4CFC6",
  outlineVariant: "#E2DED6",

  // Semantic
  danger: "#C62828",

  // Accent aliases
  accent: "#B08A30",
  accentLight: "#C9A84C",
} as const;

export const fonts = {
  heading: "'Newsreader', Georgia, 'Times New Roman', serif",
  body: "'Inter', system-ui, -apple-system, sans-serif",
} as const;
