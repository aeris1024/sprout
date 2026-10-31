// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import ComparePanel from "./ComparePanel";
import { runSprout, type CommitGraph } from "../lib/sprout";
vi.mock("../lib/sprout", async (original) => ({ ...await original<typeof import("../lib/sprout")>(), runSprout: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const commits = [{ id: "a", message: "First" }, { id: "b", message: "Second" }] as CommitGraph["commits"];
const props = { projectDir: "project", program: "sprout", commits, source: "a", target: "b", busy: false, onChange: vi.fn(), onClose: vi.fn() };
it("shows direction, CLI changes and performs only a read command", async () => {
  vi.mocked(runSprout).mockResolvedValue([
    { state: "added", path: "new.bin", old_size: null, new_size: 2 },
    { state: "modified", path: "changed.bin", old_size: 2, new_size: 3 },
    { state: "deleted", path: "old.bin", old_size: 1, new_size: null },
  ]);
  render(<ComparePanel {...props} />);
  expect((screen.getByLabelText("比較元") as HTMLSelectElement).value).toBe("a");
  expect((screen.getByLabelText("比較先") as HTMLSelectElement).value).toBe("b");
  fireEvent.click(screen.getByText("比較する"));
  await screen.findByText("new.bin");
  for (const label of ["追加", "変更", "削除", "changed.bin", "old.bin"]) expect(screen.getByText(label)).toBeTruthy();
  expect(vi.mocked(runSprout).mock.calls).toEqual([["project", ["diff", "a", "b"], "sprout"]]);
});
it("clears old results when targets change and displays empty results", async () => {
  vi.mocked(runSprout).mockResolvedValue([]);
  const view = render(<ComparePanel {...props} />);
  fireEvent.click(screen.getByText("比較する"));
  await screen.findByText("差分はありません");
  fireEvent.change(screen.getByLabelText("比較元"), { target: { value: "b" } });
  expect(props.onChange).toHaveBeenCalledWith("b", "b");
  view.rerender(<ComparePanel {...props} source="b" />);
  expect(screen.queryByText("差分はありません")).toBeNull();
});
it("retains targets on errors and can retry", async () => {
  vi.mocked(runSprout).mockRejectedValueOnce({ code: "repository_locked", message: "Locked", details: {} }).mockResolvedValueOnce([]);
  render(<ComparePanel {...props} />);
  fireEvent.click(screen.getByText("比較する"));
  await screen.findByText("別のSproutの操作が実行中です。終わってから再試行してください");
  expect((screen.getByLabelText("比較先") as HTMLSelectElement).value).toBe("b");
  fireEvent.click(screen.getByText("比較する"));
  await screen.findByText("差分はありません");
  expect(screen.queryByRole("alert")).toBeNull();
});
it("ignores an obsolete reply after target changes", async () => {
  let resolve!: (value: unknown) => void;
  vi.mocked(runSprout).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
  const view = render(<ComparePanel {...props} />);
  fireEvent.click(screen.getByText("比較する"));
  view.rerender(<ComparePanel {...props} target="a" />);
  resolve([{ state: "added", path: "stale.bin", old_size: null, new_size: 1 }]);
  await waitFor(() => expect((screen.getByText("比較する") as HTMLButtonElement).disabled).toBe(false));
  expect(screen.queryByText("stale.bin")).toBeNull();
});
