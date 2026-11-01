// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import SavePanel from "./SavePanel";
afterEach(cleanup);
function props() { return { changes: [{ state: "modified", path: "a.txt" }], growsBranch: false, message: "保存", thumbnailPath: "", thumbnailPasted: false, busy: false, onMessageChange: vi.fn(), onChooseThumbnail: vi.fn(), onClearThumbnail: vi.fn(), onSave: vi.fn(), onKeepAsBud: vi.fn(), onRevert: vi.fn() }; }
it("blocks clean, busy and empty saves including keyboard shortcuts", () => {
  const p = props();
  const { rerender } = render(<SavePanel {...p} changes={[]} />);
  expect((screen.getByRole("button", { name: "保存して葉にする" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("作業フォルダは保存済みの状態です")).toBeTruthy();
  fireEvent.keyDown(screen.getByRole("textbox", { name: "メッセージ" }), { key: "Enter", ctrlKey: true });
  rerender(<SavePanel {...p} busy />);
  fireEvent.keyDown(screen.getByRole("textbox", { name: "メッセージ" }), { key: "Enter", ctrlKey: true });
  rerender(<SavePanel {...p} message=" " />);
  fireEvent.keyDown(screen.getByRole("textbox", { name: "メッセージ" }), { key: "Enter", ctrlKey: true });
  expect(p.onSave).not.toHaveBeenCalled();
});
it("saves with Ctrl+Enter and leaves ordinary Enter for new lines", () => {
  const p = props(); render(<SavePanel {...p} />);
  const field = screen.getByRole("textbox", { name: "メッセージ" });
  fireEvent.keyDown(field, { key: "Enter" });
  expect(p.onSave).not.toHaveBeenCalled();
  fireEvent.keyDown(field, { key: "Enter", ctrlKey: true, isComposing: true });
  expect(p.onSave).not.toHaveBeenCalled();
  fireEvent.keyDown(field, { key: "Enter", ctrlKey: true });
  expect(p.onSave).toHaveBeenCalledOnce();
  expect(screen.getByText(/PNG・JPEG・WebP/).tagName).toBe("P");
});
