/** Widths in CSS pixels; App.css repeats `min` and `mapMin` to keep the panel inside a shrinking window. */
export const PANEL_WIDTH = { default: 360, min: 280, max: 720, step: 24, splitter: 6, mapMin: 360 };

/** Keep the panel readable and leave the map its working width; `available` is the workspace width. */
export function clampPanelWidth(width: number, available = Infinity): number {
  const limit = Math.min(PANEL_WIDTH.max, available - PANEL_WIDTH.splitter - PANEL_WIDTH.mapMin);
  return Math.round(Math.max(PANEL_WIDTH.min, Math.min(width, limit)));
}

/** A saved width, or the default when the settings hold nothing usable. */
export function savedPanelWidth(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? clampPanelWidth(value) : PANEL_WIDTH.default;
}
