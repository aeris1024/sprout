import { describe, expect, it } from "vitest";
import { canDiscardChanges, isUninitializedProject, normalizeCliError } from "./sprout";
import { nextRecentProjects, removeRecentProject } from "./settings";

describe("normalizeCliError", () => {
  it("preserves structured CLI errors", () => {
    expect(
      normalizeCliError({
        code: "repository_locked",
        message: "実行中",
        details: { retryable: true },
      }),
    ).toEqual({
      code: "repository_locked",
      message: "実行中",
      details: { retryable: true },
    });
  });

  it("accepts serialized Tauri errors", () => {
    const error = normalizeCliError(
      JSON.stringify({ code: "sprout_error", message: "失敗", details: {} }),
    );
    expect(error.message).toBe("失敗");
  });
});

describe("project helpers", () => {
  it("recognizes uninitialized project errors", () => {
    expect(
      isUninitializedProject({
        code: "sprout_error",
        message: "not inside a Sprout project (run 'sprout init')",
        details: {},
      }),
    ).toBe(true);
  });

  it("deduplicates and limits recent projects", () => {
    const recent = Array.from({ length: 8 }, (_, index) => `C:/work/${index}`);
    expect(nextRecentProjects(recent, "C:/work/3")[0]).toBe("C:/work/3");
    expect(nextRecentProjects(recent, "C:/work/new")).toHaveLength(8);
  });

  it("removes only the selected recent project", () => {
    expect(removeRecentProject(["C:/work/one", "C:/work/two"], "C:/work/one")).toEqual(["C:/work/two"]);
  });

  it("only permits discard for the structured uncommitted changes error", () => {
    expect(
      canDiscardChanges({
        code: "uncommitted_changes",
        message: "dirty",
        details: { can_discard: true },
      }),
    ).toBe(true);
    expect(
      canDiscardChanges({
        code: "sprout_error",
        message: "failed",
        details: { can_discard: true },
      }),
    ).toBe(false);
  });
});
