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
  fireEvent.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
  fireEvent.click(screen.getByText("選択したファイルを取り出す"));
  expect(onExport).toHaveBeenLastCalledWith(["assets/nested/b.bin"]);
  fireEvent.click(screen.getByRole("checkbox", { name: "すべて選択" }));
  fireEvent.click(screen.getByText("選択したファイルを取り出す"));
  expect(onExport).toHaveBeenLastCalledWith(files.map((file) => file.path));
  view.rerender(<SnapshotFiles key="second" {...props} />);
  expect(screen.getByText("0件を選択中")).toBeTruthy();
});
it("shows an empty snapshot without partial-operation controls", () => {
  render(<SnapshotFiles files={[]} busy={false} onExport={vi.fn()} onRestore={vi.fn()} />);
  expect(screen.getByText("保存済みファイルはありません。")).toBeTruthy();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
