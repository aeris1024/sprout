import { describe, expect, it } from "vitest";
import { cliErrorTranslations, translateCliError } from "./cliErrors";
import { isUninitializedProject, normalizeCliError } from "./sprout";

const cliSources = Object.values(import.meta.glob("../../../src/sprout/*.py", { query: "?raw", import: "default", eager: true }) as Record<string, string>).join("\n");

describe("translateCliError", () => {
  it.each([
    ["unknown_commit", "unknown commit: abc", { commit_id: "abc" }, "葉「abc」が見つかりません"],
    ["nothing_to_commit", "nothing to commit", {}, "保存する変更がありません"],
    ["empty_message", "commit message cannot be empty", {}, "メッセージを入力してください"],
    ["unknown_branch", "unknown branch: main", { name: "main" }, "ブランチ「main」が見つかりません"],
    ["unknown_bud", "unknown bud: b1", {}, "つぼみが見つかりません"],
    ["tagged_commit", "commit is tagged", { tags: ["v1", "v2"] }, "タグが付いた葉は削除できません。先にタグを削除してください（v1、v2）"],
    ["label_too_long", "label exceeds 64 character limit", { limit: 64 }, "ラベルが長すぎます（64文字まで）"],
    ["invalid_reference_name", "tag name must be non-empty", { kind: "tag" }, "タグの名前には空白を含めず、1文字以上入力してください"],
    ["invalid_preview_metadata", "description must be", { field: "description" }, "プレビューの説明は20,000文字までです"],
  ])("shows %s in the GUI's words", (code, message, details, expected) => {
    expect(translateCliError(code, message, details)).toBe(expected);
  });

  it("keeps the CLI's message for codes without a translation", () => {
    expect(translateCliError("sprout_error", "corrupt object abc", {})).toBe("corrupt object abc");
    expect(translateCliError("constructor", "from a newer CLI", {})).toBe("from a newer CLI");
  });

  it("translates only the repository format reason it can explain", () => {
    expect(translateCliError("unsupported_repository_format", "unsupported repository schema version: 99 (expected 1)", { reason: "schema_version", found_schema_version: 99, supported_schema_version: 1 })).toBe("このプロジェクトの形式（99）は、今のSprout CLI（1）では開けません");
    expect(translateCliError("unsupported_repository_format", "repository schema is incomplete; missing tables: commits", { reason: "missing_tables" })).toBe("repository schema is incomplete; missing tables: commits");
  });

  it("explains known trash conflicts and keeps unknown ones as sent", () => {
    expect(translateCliError("trash_restore_conflict", "cannot restore", { reason_code: "newer_note" })).toBe("復旧できません。葉に新しいメモがあります。何も変更していません");
    expect(translateCliError("trash_restore_conflict", "cannot restore", { reason_code: "new_reason" })).toBe("cannot restore");
    expect(translateCliError("trash_restore_conflict", "cannot restore", {})).toBe("cannot restore");
  });

  it("only translates codes the CLI can send", () => {
    const missing = Object.keys(cliErrorTranslations).filter((code) => !cliSources.match(new RegExp(`code\\s*=\\s*["']${code}["']|code: str = "${code}"`)));
    expect(missing).toEqual([]);
    for (const reason of ["commit_missing", "newer_note", "name_in_use", "preview_list_changed", "preview_materials_changed", "bud_base_missing", "changed_since", "missing_reference", "record_conflict"]) {
      expect(cliSources).toContain(`'${reason}'`);
    }
  });

  it("uses the defined terms", () => {
    const samples = Object.keys(cliErrorTranslations).map((code) => translateCliError(code, "", { name: "x", commit_id: "x", kind: "tag", limit: 1, tags: ["x"], reason: code === "unsupported_repository_format" ? "schema_version" : "x", reason_code: "newer_note" }));
    for (const sample of samples) {
      expect(sample).not.toBe("");
      expect(sample).not.toMatch(/コミット|スナップショット|枝|commit|snapshot|branch|\bbud\b/i);
    }
  });
});

describe("CLI errors reaching the GUI", () => {
  it("translates through normalizeCliError and keeps the code and details", () => {
    expect(normalizeCliError({ code: "unknown_commit", message: "unknown commit: abc", details: { commit_id: "abc" } })).toEqual({
      code: "unknown_commit",
      message: "葉「abc」が見つかりません",
      details: { commit_id: "abc" },
      translated: true,
    });
  });

  it("keeps text added to an error that is normalized again", () => {
    const once = normalizeCliError({ code: "nothing_to_save", message: "no unsaved changes to keep in a bud", details: {} });
    expect(normalizeCliError({ ...once, message: `${once.message}（注記）` }).message).toBe("つぼみへ移す未保存の変更がありません（注記）");
  });

  it("still recognizes an uninitialized project after translating", () => {
    expect(isUninitializedProject(normalizeCliError({ code: "not_initialized", message: "not inside a Sprout project (run 'sprout init')", details: {} }))).toBe(true);
    expect(isUninitializedProject(normalizeCliError({ code: "sprout_error", message: "not inside a Sprout project (run 'sprout init')", details: {} }))).toBe(true);
  });
});
