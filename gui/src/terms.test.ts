import { describe, expect, it } from "vitest";

const sources = Object.entries(import.meta.glob("./**/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>)
  .filter(([path]) => !path.includes(".test."));

/** Words gui/README.md defines away; see its 用語 section. */
describe("GUI wording", () => {
  it.each(sources)("%s uses the defined terms", (_path, source) => {
    expect(source.match(/コミット|スナップショット|枝/g)).toBeNull();
    expect(source.match(/className="eyebrow">[A-Z]/g)).toBeNull();
    expect(source.match(/"(SNAPSHOT|BUD|BRANCH)"/g)).toBeNull();
  });

  it("checks the components", () => {
    expect(sources.length).toBeGreaterThan(10);
  });
});
