// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import SproutMap from "./SproutMap";
import userEvent from "@testing-library/user-event";
import type { Bud, CommitGraph } from "../lib/sprout";

afterEach(cleanup);

function renderLeaves(onSelect = vi.fn()) {
  const commit = { parent_id: null, branch_id: "b1", branch_name: "main", created_at: "2026-10-30T03:04:05.000000+00:00", attachments: [], note: null, note_updated_at: null, labels: [] as string[] };
  const graph: CommitGraph = {
    current_commit: "c3",
    at_branch_tip: true,
    commits: [
      { ...commit, id: "c1", message: "ラフ案を作成" },
      { ...commit, id: "c2", parent_id: "c1", message: "Client Review", note: "確認済み", labels: ["承認済み", "wip"] },
      { ...commit, id: "c3", parent_id: "c2", message: "とても長いメッセージなのでマップの葉では省略されてしまう説明" },
    ],
    branches: [{ id: "b1", name: "main", commit_id: "c3", comment: "", current: true }],
    tags: [{ name: "submitted", commit_id: "c1", comment: "", created_at: commit.created_at }],
    buds: [],
  };
  render(<SproutMap graph={graph} selection={null} unsavedCount={0} projectDir="C:/p" sproutProgram="" onSelect={onSelect} onSelectBud={vi.fn()} onSelectBranch={vi.fn()} onSelectUnsaved={vi.fn()} />);
  const leaf = (name: string | RegExp) => screen.getByRole("button", { name });
  return { leaf, search: screen.getByLabelText("葉を検索") };
}

function leafDimmed(element: HTMLElement) {
  return element.classList.contains("dimmed");
}

it("uses one map tab stop and moves, selects and exits with the keyboard", async () => {
  const user = userEvent.setup();
  const select = vi.fn();
  const { leaf } = renderLeaves(select);
  const current = leaf(/とても長いメッセージ/);
  expect(document.querySelectorAll('[data-map-node][tabindex="0"]').length).toBe(1);
  expect(current.getAttribute("tabindex")).toBe("0");
  current.focus();
  await user.keyboard("{ArrowLeft}");
  expect(document.activeElement).toBe(leaf("Client Review"));
  expect(select).toHaveBeenLastCalledWith("c2");
  expect(document.querySelectorAll('[data-map-node][tabindex="0"]').length).toBe(1);
  const panel = document.createElement("button"); panel.textContent = "右パネル"; document.body.append(panel);
  await user.tab();
  expect(document.activeElement).toBe(panel);
  panel.remove();
});

describe("leaf information", () => {
  it("shows the full message and time on hover and keyboard focus", () => {
    const { leaf } = renderLeaves();
    const long = leaf(/とても長いメッセージ/);
    expect(long.querySelector("title")?.textContent).toContain("説明");
    expect(document.querySelector(".map-hint")).toBeNull();

    fireEvent.mouseEnter(long);
    expect(document.querySelector(".map-hint")?.textContent).toContain("省略されてしまう説明");
    expect(document.querySelector(".map-hint")?.textContent).toContain("2026/10/30");
    fireEvent.mouseLeave(long);
    expect(document.querySelector(".map-hint")).toBeNull();

    fireEvent.focus(long);
    expect(document.querySelector(".map-hint")?.textContent).toContain("省略されてしまう説明");
    fireEvent.blur(long);
    expect(document.querySelector(".map-hint")).toBeNull();
  });

  it("marks leaves that have a note or labels", () => {
    const { leaf } = renderLeaves();
    expect(leaf("Client Review").textContent).toContain("メモ・ラベル2");
    expect(leaf("ラフ案を作成").textContent).not.toContain("メモ");
  });
});

describe("leaf search", () => {
  it.each([
    ["message", "CLIENT", "Client Review"],
    ["tag", "submit", "ラフ案を作成"],
    ["label", "承認", "Client Review"],
  ])("finds a leaf by %s", (_kind, text, expected) => {
    const { leaf, search } = renderLeaves();
    fireEvent.change(search, { target: { value: text } });
    expect(screen.getByRole("status").textContent).toBe("1件");
    expect(leafDimmed(leaf(expected))).toBe(false);
    expect(leafDimmed(leaf(/とても長いメッセージ/))).toBe(true);
  });

  it("says when nothing matches and restores the map when cleared", () => {
    const { leaf, search } = renderLeaves();
    fireEvent.change(search, { target: { value: "存在しない" } });
    expect(screen.getByRole("status").textContent).toBe("該当なし");
    expect(leafDimmed(leaf("Client Review"))).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "検索を解除" }));
    expect(leafDimmed(leaf("Client Review"))).toBe(false);
    expect((search as HTMLInputElement).value).toBe("");
    fireEvent.change(search, { target: { value: "x" } });
    fireEvent.keyDown(search, { key: "Escape" });
    expect((search as HTMLInputElement).value).toBe("");
  });

  it("moves through matches, selecting each leaf and wrapping around", () => {
    const onSelect = vi.fn();
    const { search } = renderLeaves(onSelect);
    // Matches c1 through its tag and c2 through its message and label.
    fireEvent.change(search, { target: { value: "i" } });
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getByRole("status").textContent).toBe("2件");

    fireEvent.keyDown(search, { key: "Enter" });
    expect(onSelect).toHaveBeenLastCalledWith("c1");
    expect(screen.getByRole("status").textContent).toBe("1 / 2件");
    fireEvent.click(screen.getByRole("button", { name: "次の一致" }));
    expect(onSelect).toHaveBeenLastCalledWith("c2");
    fireEvent.keyDown(search, { key: "Enter" });
    expect(onSelect).toHaveBeenLastCalledWith("c1");
    fireEvent.click(screen.getByRole("button", { name: "前の一致" }));
    expect(onSelect).toHaveBeenLastCalledWith("c2");
    fireEvent.keyDown(search, { key: "Enter", shiftKey: true });
    expect(onSelect).toHaveBeenLastCalledWith("c1");
  });
});

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

describe("opening a leaf's previews", () => {
  function renderWithPreviews() {
    const preview = { commit_id: "c1", object_hash: "h", role: "preview", media_type: "image/png", size: 1, display_name: "", description: "" };
    const commit = { parent_id: null, branch_id: "b1", branch_name: "main", created_at: "2026-10-30T03:04:05.000000+00:00", note: null, note_updated_at: null, labels: [] as string[] };
    const graph: CommitGraph = {
      current_commit: "c2",
      at_branch_tip: true,
      commits: [
        { ...commit, id: "c1", message: "三面図", attachments: [
          { ...preview, id: "p1", position: 0, original_name: "front.png" },
          { ...preview, id: "p2", position: 1, original_name: "side.png" },
          { ...preview, id: "t1", role: "thumbnail", position: 0, original_name: "thumb.png" },
        ] as never },
        { ...commit, id: "c2", parent_id: "c1", message: "仕上げ", attachments: [] },
      ],
      branches: [{ id: "b1", name: "main", commit_id: "c2", comment: "", current: true }],
      tags: [],
      buds: [],
    };
    const onSelect = vi.fn();
    const onOpenPreviews = vi.fn();
    render(<SproutMap graph={graph} selection={null} unsavedCount={0} projectDir="C:/p" sproutProgram="" onSelect={onSelect} onSelectBud={vi.fn()} onSelectBranch={vi.fn()} onSelectUnsaved={vi.fn()} onOpenPreviews={onOpenPreviews} />);
    return { onSelect, onOpenPreviews, leaf: (name: string) => screen.getByRole("button", { name }) };
  }

  it("counts previews but not the thumbnail among a leaf's marks", () => {
    const { leaf } = renderWithPreviews();
    expect(leaf("三面図").textContent).toContain("プレビュー2");
    expect(leaf("仕上げ").textContent).not.toContain("プレビュー");
  });

  it("opens previews with a double-click or Space, while a click and Enter still select", async () => {
    const user = userEvent.setup();
    const { leaf, onSelect, onOpenPreviews } = renderWithPreviews();
    await user.dblClick(leaf("三面図"));
    expect(onSelect).toHaveBeenCalledWith("c1");
    expect(onOpenPreviews).toHaveBeenCalledTimes(1);
    expect(onOpenPreviews).toHaveBeenLastCalledWith("c1");
    onSelect.mockClear();
    leaf("仕上げ").focus();
    await user.keyboard(" ");
    expect(onOpenPreviews).toHaveBeenLastCalledWith("c2");
    expect(onSelect).not.toHaveBeenCalled();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("c2");
    expect(onOpenPreviews).toHaveBeenCalledTimes(2);
  });
});
