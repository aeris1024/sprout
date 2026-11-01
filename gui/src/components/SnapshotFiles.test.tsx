// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import SnapshotFiles from "./SnapshotFiles";
afterEach(cleanup);
const files = [
  { path: "assets/a.bin", size: 10, object_hash: "a", mtime_ns: 0 },
  { path: "assets/nested/b.bin", size: 20, object_hash: "b", mtime_ns: 0 },
  { path: "other.bin", size: 30, object_hash: "c", mtime_ns: 0 },
];
it("selects nested directories, excludes unchecked files and resets on a new snapshot", () => {
  const onExport = vi.fn();
  const props = { files, busy: false, onExport, onRestore: vi.fn() };
  const view = render(<SnapshotFiles key="first" {...props} />);
  expect((screen.getByText("選択したファイルを取り出す") as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox", { name: "assets/ 配下を選択" }));
  fireEvent.click(screen.getByRole("button", { name: "assets/を展開" }));
  fireEvent.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
  fireEvent.click(screen.getByText("選択したファイルを取り出す"));
  expect(onExport).toHaveBeenLastCalledWith(["assets/nested/b.bin"]);
  fireEvent.click(screen.getByRole("checkbox", { name: "すべて選択" }));
  fireEvent.click(screen.getByText("選択したファイルを取り出す"));
  expect(onExport).toHaveBeenLastCalledWith(files.map((file) => file.path));
  view.rerender(<SnapshotFiles key="second" {...props} />);
  expect(screen.getByText("0件を選択中")).toBeTruthy();
});
it("filters nested paths, preserves hidden selections and exposes IDs only in details", () => {
  const onExport = vi.fn();
  render(<SnapshotFiles files={files.map((file) => ({ ...file, file_id: `id-${file.path}` }))} busy={false} onExport={onExport} onRestore={vi.fn()} />);
  fireEvent.click(screen.getByRole("checkbox", { name: /other.bin/ }));
  fireEvent.change(screen.getByRole("searchbox", { name: "保存済みファイルを検索" }), { target: { value: "ASSETS/NESTED" } });
  expect(screen.queryByRole("checkbox", { name: /assets\/a.bin/ })).toBeNull();
  expect(screen.getByRole("checkbox", { name: /assets\/nested\/b.bin/ })).toBeTruthy();
  fireEvent.click(screen.getByRole("checkbox", { name: "assets/ 配下を選択" }));
  expect(screen.getByRole("status").textContent).toContain("検索結果の外に1件");
  fireEvent.click(screen.getByRole("button", { name: "選択したファイルを取り出す" }));
  expect(onExport).toHaveBeenLastCalledWith(["assets/nested/b.bin", "other.bin"]);
  const details = screen.getByText("assets/nested/b.binの素材ID").closest("details")!;
  expect(details.open).toBe(false);
  fireEvent.click(details.querySelector("summary")!);
  expect(details.textContent).toContain("id-assets/nested/b.bin");
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "missing" } });
  expect(screen.getByText("一致するファイルはありません。")).toBeTruthy();
});
it("shows an empty snapshot without partial-operation controls", () => {
  render(<SnapshotFiles files={[]} busy={false} onExport={vi.fn()} onRestore={vi.fn()} />);
  expect(screen.getByText("保存済みファイルはありません。")).toBeTruthy();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
