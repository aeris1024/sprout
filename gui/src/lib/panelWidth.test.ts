import { describe, expect, it } from "vitest";
import { PANEL_WIDTH, clampPanelWidth, savedPanelWidth } from "./panelWidth";

describe("panel width", () => {
  it("stays between its limits", () => {
    expect(clampPanelWidth(100)).toBe(PANEL_WIDTH.min);
    expect(clampPanelWidth(5000)).toBe(PANEL_WIDTH.max);
    expect(clampPanelWidth(400.4)).toBe(400);
  });

  it("leaves the map its working width in a small window", () => {
    expect(clampPanelWidth(700, 900)).toBe(900 - PANEL_WIDTH.splitter - PANEL_WIDTH.mapMin);
  });

  it("falls back to the default for unusable saved values", () => {
    expect(savedPanelWidth(undefined)).toBe(PANEL_WIDTH.default);
    expect(savedPanelWidth("wide")).toBe(PANEL_WIDTH.default);
    expect(savedPanelWidth(Number.NaN)).toBe(PANEL_WIDTH.default);
    expect(savedPanelWidth(480)).toBe(480);
  });
});
