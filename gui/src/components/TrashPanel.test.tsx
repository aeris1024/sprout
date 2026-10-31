// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import TrashPanel from "./TrashPanel";
import { formatLocalTime, type TrashItem } from "../lib/sprout";

afterEach(cleanup);

function item(kind: TrashItem["kind"], title: string, changes?: TrashItem["changes"]): TrashItem {
  return { id: `${kind}-id`, kind, target_id: "target", title, created_at: "2026-10-30T00:00:00.000000+00:00", protected_bytes: 1, reclaimable_bytes: 1, objects: [], changes };
}

function panel(items: TrashItem[]) {
  render(<TrashPanel items={items} busy={false} onInspect={vi.fn()} onRestore={vi.fn()} onPurge={vi.fn()} onClose={vi.fn()} />);
}

it("names dropped buds and discarded work and explains how they come back", () => {
  panel([item("bud_delete", "別案"), item("discard", "a.txt +1")]);
  expect(screen.getByText("捨てたつぼみ")).toBeTruthy();
  expect(screen.getByText("破棄した未保存の変更")).toBeTruthy();
  expect(screen.getByText(/つぼみとして戻ります/)).toBeTruthy();
});

it("names deleted notes, tags and branches", () => {
  panel([item("note_delete", "メモ"), item("tag_delete", "v1"), item("branch_delete", "side")]);
  expect(screen.getByText("メモの削除")).toBeTruthy();
  expect(screen.getByText("タグの削除")).toBeTruthy();
  expect(screen.getByText("ブランチの削除")).toBeTruthy();
});

it("shows local times and keeps internal IDs folded away", () => {
  panel([item("commit", "葉", [{ table: "commits", before: { updated_at: "2026-10-30T01:00:00+00:00", parent_id: "p".repeat(32) }, after: null }])]);
  const article = screen.getByRole("article");
  expect(screen.getByText(`ゴミ箱へ移動: ${formatLocalTime("2026-10-30T00:00:00.000000+00:00")}`)).toBeTruthy();
  expect(screen.getByText(`更新日時: ${formatLocalTime("2026-10-30T01:00:00+00:00")}`)).toBeTruthy();
  expect(screen.getByText(`親の葉: ${"p".repeat(12)}`)).toBeTruthy();
  expect(article.textContent).not.toContain("+00:00");

  const ids = screen.getByText(/復旧ID: commit-id/).closest("details") as HTMLDetailsElement;
  expect(ids.open).toBe(false);
  expect(ids.textContent).toContain("対象: target");
});

it("sets the irreversible purge apart from the other actions", () => {
  panel([item("commit", "葉")]);
  expect(screen.getByRole("button", { name: "葉を完全削除" }).className).toContain("destructive");
  expect(screen.getByRole("button", { name: "葉を復旧" }).className).not.toContain("destructive");
});

it("describes the files kept with a bud", () => {
  panel([item("discard", "a.txt", [{ table: "bud_files", before: { path: "a.txt", size: 3 }, after: null }])]);
  expect(screen.getByText("つぼみのファイル")).toBeTruthy();
  expect(screen.getByText("パス: a.txt")).toBeTruthy();
});
