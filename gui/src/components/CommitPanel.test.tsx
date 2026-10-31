// @vitest-environment jsdom
import type { ComponentProps } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommitPanel from "./CommitPanel";

afterEach(cleanup);

function props(): ComponentProps<typeof CommitPanel> {
  return {
    detail: { id: "first", parent_id: null, created_at: "2026-10-31T00:00:00Z", message: "作業中", note: null, note_updated_at: null, labels: [], branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] },
    projectDir: "C:/project", program: "", branches: [], tags: [], current: false, unsavedCount: 2, busy: false,
    onGo: vi.fn(), onGrow: vi.fn(), onSetThumbnail: vi.fn(), onUpdateMessage: vi.fn(), onExport: vi.fn(), onRestoreFiles: vi.fn(), onCompare: vi.fn(), onDelete: vi.fn(), onClose: vi.fn(),
    previews: { add: vi.fn(), paste: vi.fn(), pastePaths: vi.fn(), replace: vi.fn(), remove: vi.fn(), export: vi.fn(), order: vi.fn() },
    annotations: { onSaveNote: vi.fn(), onAddLabel: vi.fn(), onRemoveLabel: vi.fn(), onCreateTag: vi.fn(), onSetTagComment: vi.fn(), onDeleteTag: vi.fn() },
  };
}

it("keeps primary actions direct and sends each menu action to the selected leaf", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  render(<CommitPanel {...callbacks} />);
  expect(screen.queryByRole("menuitem")).toBeNull();
  await user.click(screen.getByRole("button", { name: "ここへ移動" }));
  expect(callbacks.onGo).toHaveBeenCalledWith("first");
  await user.click(screen.getByRole("button", { name: "ブランチを作る" }));
  await user.type(screen.getByRole("textbox", { name: "新しいブランチの名前" }), "new-work");
  await user.click(screen.getByRole("button", { name: "ブランチを作って移動" }));
  expect(callbacks.onGrow).toHaveBeenCalledWith("first", "new-work");
  for (const [name, callback] of [["サムネイルを登録", callbacks.onSetThumbnail], ["ファイルを取り出す", callbacks.onExport], ["この葉を削除", callbacks.onDelete]] as const) {
    await user.click(screen.getByRole("button", { name: "その他の操作" }));
    await user.click(screen.getByRole("menuitem", { name }));
    expect(callback).toHaveBeenCalledWith("first");
    expect(screen.queryByRole("menu")).toBeNull();
  }
});

it("supports keyboard navigation and consumes one Escape without closing the detail or losing a draft", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  render(<CommitPanel {...callbacks} />);
  await user.click(screen.getByRole("button", { name: "メッセージを編集" }));
  await user.type(screen.getByRole("textbox", { name: "メッセージを編集" }), "下書き");
  const trigger = screen.getByRole("button", { name: "その他の操作" });
  trigger.focus();
  await user.keyboard("{Enter}");
  expect(trigger.getAttribute("aria-expanded")).toBe("true");
  expect(document.activeElement).toBe(screen.getByRole("menuitem", { name: "サムネイルを登録" }));
  await user.keyboard("{End}");
  expect(document.activeElement).toBe(screen.getByRole("menuitem", { name: "この葉を削除" }));
  await user.keyboard("{Home}{ArrowDown}{Enter}");
  expect(callbacks.onExport).toHaveBeenCalledWith("first");
  await user.keyboard(" ");
  const parentEscape = vi.fn();
  window.addEventListener("keydown", parentEscape);
  try { await user.keyboard("{Escape}"); } finally { window.removeEventListener("keydown", parentEscape); }
  expect(parentEscape).not.toHaveBeenCalled();
  expect(document.activeElement).toBe(trigger);
  expect(trigger.getAttribute("aria-expanded")).toBe("false");
  expect((screen.getByRole("textbox", { name: "メッセージを編集" }) as HTMLTextAreaElement).value).toBe("作業中下書き");
  expect(callbacks.onClose).not.toHaveBeenCalled();
});

it("closes on outside pointer interaction, Tab departure, and a second click on the trigger", async () => {
  const user = userEvent.setup();
  render(<CommitPanel {...props()} />);
  const trigger = screen.getByRole("button", { name: "その他の操作" });
  await user.click(trigger);
  fireEvent.pointerDown(document.body);
  expect(screen.queryByRole("menu")).toBeNull();
  await user.click(trigger);
  await user.keyboard("{End}{Tab}");
  expect(screen.queryByRole("menu")).toBeNull();
  await user.click(trigger);
  await user.click(trigger);
  expect(screen.queryByRole("menu")).toBeNull();
});

it.each(["leaf", "project", "busy"])("invalidates an open menu on %s change", async (change) => {
  const user = userEvent.setup();
  const initial = props();
  const view = render(<CommitPanel {...initial} />);
  await user.click(screen.getByRole("button", { name: "その他の操作" }));
  const updated = change === "leaf" ? { ...initial, detail: { ...initial.detail, id: "second" } } : change === "project" ? { ...initial, projectDir: "C:/other" } : { ...initial, busy: true };
  view.rerender(<CommitPanel {...updated} />);
  expect(screen.queryByRole("menu")).toBeNull();
  expect(initial.onDelete).not.toHaveBeenCalled();
  if (change === "busy") {
    expect((screen.getByRole("button", { name: "その他の操作" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "ここへ移動" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "ブランチを作る" }) as HTMLButtonElement).disabled).toBe(true);
    view.rerender(<CommitPanel {...initial} />);
    expect(screen.queryByRole("menu")).toBeNull();
  }
});

it("keeps the current position disabled and exposes a tagged leaf's deletion reason", async () => {
  const user = userEvent.setup();
  const initial = props();
  render(<CommitPanel {...initial} current tags={[{ name: "milestone", commit_id: "first", created_at: "2026-10-31T00:00:00Z", comment: "" }]} />);
  expect((screen.getByRole("button", { name: "この葉にいます" }) as HTMLButtonElement).disabled).toBe(true);
  await user.click(screen.getByRole("button", { name: "その他の操作" }));
  const deletion = screen.getByRole("menuitem", { name: "この葉を削除" });
  expect((deletion as HTMLButtonElement).disabled).toBe(true);
  expect(document.getElementById(deletion.getAttribute("aria-describedby")!)?.textContent).toContain("タグ付きの葉は削除できません");
  await user.keyboard("{End}");
  expect(document.activeElement).toBe(screen.getByRole("menuitem", { name: "ファイルを取り出す" }));
});
