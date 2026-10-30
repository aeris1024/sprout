// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import TrashPanel from "./TrashPanel";
import type { TrashItem } from "../lib/sprout";

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

it("describes the files kept with a bud", () => {
  panel([item("discard", "a.txt", [{ table: "bud_files", before: { path: "a.txt", size: 3 }, after: null }])]);
  expect(screen.getByText("つぼみのファイル")).toBeTruthy();
  expect(screen.getByText("パス: a.txt")).toBeTruthy();
});
