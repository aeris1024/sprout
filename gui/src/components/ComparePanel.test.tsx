// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import ComparePanel from "./ComparePanel";
import userEvent from "@testing-library/user-event";
import { runSprout, type CommitGraph } from "../lib/sprout";
vi.mock("../lib/sprout", async (original) => ({ ...await original<typeof import("../lib/sprout")>(), runSprout: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const commits = [{ id: "a", message: "First" }, { id: "b", message: "Second" }] as CommitGraph["commits"];
const props = { projectDir: "project", program: "sprout", commits, source: "a", target: "b", busy: false, onChange: vi.fn(), onClose: vi.fn() };
it("opens full old and new paths and exposes them on hover", async () => {
  const user = userEvent.setup();
  const oldPath = `${"before/".repeat(30)}old.png`; const path = `${"after/".repeat(30)}new.png`;
  vi.mocked(runSprout).mockResolvedValue([{ state: "renamed", previous_path: oldPath, path, old_size: 10, new_size: 10 }]);
  render(<ComparePanel {...props} />);
  await user.click(screen.getByRole("button", { name: "比較する" }));
  const title = await screen.findByTitle(`${oldPath} → ${path}`);
  const details = title.closest("details")!;
  expect(details.open).toBe(false);
  details.querySelector("summary")!.focus();
  await user.click(details.querySelector("summary")!);
  expect(details.open).toBe(true);
  expect(screen.getByText(`変更前: ${oldPath}`)).toBeTruthy();
  expect(screen.getByText(`変更後: ${path}`)).toBeTruthy();
  expect(screen.getByText("10 B → 10 B")).toBeTruthy();
});
it("switches the map picking side, swaps endpoints and formats sizes", async () => {
  const onPick = vi.fn();
  vi.mocked(runSprout).mockResolvedValue([{ state: "modified", path: "large.bin", old_size: 2048, new_size: 1048576 }]);
  render(<ComparePanel {...props} picking="target" onPick={onPick} />);
  fireEvent.click(screen.getByRole("radio", { name: "比較元をマップで選ぶ" }));
  expect(onPick).toHaveBeenCalledWith("source");
  fireEvent.click(screen.getByRole("button", { name: "比較元と比較先を入れ替える" }));
  expect(props.onChange).toHaveBeenCalledWith("b", "a");
  fireEvent.click(screen.getByRole("button", { name: "比較する" }));
  expect(await screen.findByText("2.0 KiB → 1.0 MiB")).toBeTruthy();
});
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
  expect(vi.mocked(runSprout).mock.calls).toEqual([["project", ["file", "diff", "a", "b"], "sprout"]]);
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
