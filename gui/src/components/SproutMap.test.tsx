// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import SproutMap from "./SproutMap";
import type { Bud, CommitGraph } from "../lib/sprout";

afterEach(cleanup);

function renderMap(buds: Partial<Bud>[], onSelect = vi.fn()) {
  const graph: CommitGraph = {
    current_commit: "c1",
    at_branch_tip: true,
    commits: [{ id: "c1", parent_id: null, branch_id: "b1", branch_name: "main", created_at: "2026-10-30T00:00:00.000000+00:00", message: "Base", attachments: [], note: null, note_updated_at: null, labels: [] }],
    branches: [{ id: "b1", name: "main", commit_id: "c1", comment: "", current: true }],
    tags: [],
    buds: buds.map((bud, index) => ({ id: `bud${index}`, base_commit_id: "c1", branch_id: "b1", branch_name: "main", created_at: "2026-10-30T00:00:00.000000+00:00", changes: [{ state: "modified", path: "a.txt" }], files: [], ...bud })),
  };
  render(<SproutMap graph={graph} selection={null} unsavedCount={0} projectDir="C:/p" sproutProgram="" onSelect={onSelect} onSelectBud={vi.fn()} onSelectBranch={vi.fn()} onSelectUnsaved={vi.fn()} />);
}

function scrollArea(sizes: { clientWidth: number; clientHeight: number; scrollWidth: number; scrollHeight: number }) {
  const element = document.querySelector<HTMLElement>(".map-scroll")!;
  for (const [key, value] of Object.entries(sizes)) Object.defineProperty(element, key, { configurable: true, value });
  element.setPointerCapture = vi.fn();
  return element;
}

const wide = { clientWidth: 800, clientHeight: 600, scrollWidth: 4000, scrollHeight: 600 };

function pointer(target: Element, type: string, clientX: number, clientY: number, button = 0) {
  act(() => { target.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, clientX, clientY, button })); });
}

it("turns the wheel into sideways movement only when the map cannot scroll vertically", () => {
  renderMap([]);
  const element = scrollArea(wide);
  fireEvent.wheel(element, { deltaY: 120 });
  expect(element.scrollLeft).toBe(120);
  fireEvent.wheel(element, { deltaY: 120, shiftKey: true });
  expect(element.scrollLeft).toBe(120);

  Object.defineProperty(element, "scrollHeight", { configurable: true, value: 1200 });
  fireEvent.wheel(element, { deltaY: 120 });
  expect(element.scrollLeft).toBe(120);
});

it("pans from the background without taking clicks from leaves", () => {
  const onSelect = vi.fn();
  renderMap([], onSelect);
  const element = scrollArea(wide);
  element.scrollLeft = 300;
  element.scrollTop = 40;
  const canvas = document.querySelector(".map-canvas")!;

  pointer(canvas, "pointerdown", 400, 300);
  expect(element.classList.contains("panning")).toBe(true);
  pointer(canvas, "pointermove", 350, 290);
  expect([element.scrollLeft, element.scrollTop]).toEqual([350, 50]);
  pointer(canvas, "pointerup", 350, 290);
  expect(element.classList.contains("panning")).toBe(false);
  pointer(canvas, "pointermove", 100, 100);
  expect(element.scrollLeft).toBe(350);

  const leaf = screen.getByRole("button", { name: "Base" });
  pointer(leaf, "pointerdown", 400, 300);
  expect(element.classList.contains("panning")).toBe(false);
  fireEvent.click(leaf);
  expect(onSelect).toHaveBeenCalledWith("c1");
});

it("leaves the scrollbar and other mouse buttons alone", () => {
  renderMap([]);
  const element = scrollArea(wide);
  pointer(document.querySelector(".map-canvas")!, "pointerdown", 100, 100, 2);
  expect(element.classList.contains("panning")).toBe(false);
  pointer(element, "pointerdown", 805, 100);
  expect(element.classList.contains("panning")).toBe(false);
});

it("keeps the viewed place when zooming", () => {
  renderMap([]);
  const element = scrollArea(wide);
  element.scrollLeft = 1000;
  fireEvent.click(screen.getByRole("button", { name: "拡大" }));
  // The middle of the view was at 1400 at 100%, so it is at 1750 at 125%.
  expect(element.scrollLeft).toBe(1750 - 400);
});

it("returns to the current position on request", () => {
  renderMap([]);
  const element = scrollArea(wide);
  const scrollTo = vi.fn();
  element.scrollTo = scrollTo;
  fireEvent.click(screen.getByRole("button", { name: "いまここへ戻る" }));
  expect(scrollTo).toHaveBeenCalledOnce();
});

it("shows a bud's name on the map and keeps long names readable through the label", () => {
  renderMap([{ name: "配色" }, { name: "とても長いつぼみの名前です" }, { name: "" }]);
  expect(screen.getByText("配色")).toBeTruthy();
  expect(screen.getByRole("button", { name: "つぼみ「配色」（1件の変更）" })).toBeTruthy();
  expect(screen.getByText("とても長いつ…")).toBeTruthy();
  expect(screen.getByRole("button", { name: "つぼみ「とても長いつぼみの名前です」（1件の変更）" })).toBeTruthy();
  expect(screen.getByText("つぼみ 1")).toBeTruthy();
});
