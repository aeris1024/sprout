import { describe, expect, it } from "vitest";
import { isUninitializedProject, normalizeCliError } from "./sprout";
import { nextRecentProjects } from "./settings";

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
});
