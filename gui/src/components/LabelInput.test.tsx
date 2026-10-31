// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LabelInput from "./LabelInput";

const { runSprout } = vi.hoisted(() => ({ runSprout: vi.fn() }));
vi.mock("../lib/sprout", async (original) => ({ ...(await original<typeof import("../lib/sprout")>()), runSprout }));
afterEach(cleanup);
beforeEach(() => { runSprout.mockReset(); runSprout.mockResolvedValue([{ name: "Draft", leaf_count: 2 }, { name: "Submitted", leaf_count: 3 }]); });
const props = () => ({ projectDir: "C:/project", program: "", leafId: "first", labels: [] as string[], busy: false, onAdd: vi.fn().mockResolvedValue(true) });

it("loads all candidate counts on empty focus and adds only after an explicit mouse choice", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  render(<LabelInput {...callbacks} />);
  expect(runSprout).not.toHaveBeenCalled();
  await user.click(screen.getByRole("combobox"));
  const submitted = await screen.findByRole("option", { name: "Submitted 3件の葉" });
  expect(screen.getByRole("option", { name: "Draft 2件の葉" })).toBeTruthy();
  expect(runSprout).toHaveBeenCalledWith("C:/project", ["leaf", "label", "list"], "");
  expect(callbacks.onAdd).not.toHaveBeenCalled();
  await user.click(submitted);
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith("first", "Submitted");
  expect(screen.queryByRole("listbox")).toBeNull();
});

it("filters while typing, consumes Escape locally without losing the draft, and confirms by keyboard", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  render(<LabelInput {...callbacks} />);
  await user.type(screen.getByRole("combobox"), "Sub");
  await screen.findByRole("option", { name: "Submitted 3件の葉" });
  expect(screen.queryByRole("option", { name: /Draft/ })).toBeNull();
  expect(callbacks.onAdd).not.toHaveBeenCalled();
  const parent = vi.fn();
  window.addEventListener("keydown", parent);
  try { await user.keyboard("{Escape}"); } finally { window.removeEventListener("keydown", parent); }
  expect(parent).not.toHaveBeenCalled();
  expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("Sub");
  expect(screen.queryByRole("listbox")).toBeNull();
  await user.click(screen.getByRole("combobox"));
  await screen.findByRole("option", { name: "Submitted 3件の葉" });
  await user.keyboard("{ArrowDown}{Enter}");
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith("first", "Submitted");
});

it("starts ArrowUp at the last candidate and avoids repeated pending additions", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  let finish!: (result: boolean) => void;
  callbacks.onAdd.mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  render(<LabelInput {...callbacks} />);
  await user.click(screen.getByRole("combobox"));
  await screen.findByRole("option", { name: "Draft 2件の葉" });
  await user.keyboard("{ArrowUp}{Enter}{Enter}");
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith("first", "Submitted");
  await act(async () => { finish(true); });
});

it("prevents normalized duplicates and skips already attached options", async () => {
  const user = userEvent.setup();
  const callbacks = { ...props(), labels: ["Café"] };
  runSprout.mockResolvedValue([{ name: "Café", leaf_count: 2 }, { name: "Submitted", leaf_count: 3 }]);
  render(<LabelInput {...callbacks} />);
  await user.type(screen.getByRole("combobox"), "  Cafe\u0301  ");
  expect((await screen.findByRole("option", { name: "Café 2件の葉・追加済み" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole("button", { name: "追加" }) as HTMLButtonElement).disabled).toBe(true);
  await user.keyboard("{Enter}");
  expect(callbacks.onAdd).not.toHaveBeenCalled();
  await user.clear(screen.getByRole("combobox"));
  await user.keyboard("{ArrowDown}{Enter}");
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith("first", "Submitted");
});

it("keeps new-label input usable through loading, failures and retries", async () => {
  const user = userEvent.setup();
  const callbacks = props();
  let fail!: (failure: unknown) => void;
  runSprout.mockImplementationOnce(() => new Promise((_resolve, reject) => { fail = reject; }));
  render(<LabelInput {...callbacks} />);
  await user.type(screen.getByRole("combobox"), "New label");
  expect(screen.getByRole("status").textContent).toContain("読み込み中");
  await act(async () => { fail({ code: "offline", message: "temporary failure", details: {} }); });
  expect(screen.getByRole("status").textContent).toContain("temporary failure");
  expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("New label");
  await user.click(screen.getByRole("button", { name: "候補を再取得" }));
  expect(await screen.findByText("一致する候補はありません。新しいラベルを追加できます。")).toBeTruthy();
  await user.click(screen.getByRole("button", { name: "追加" }));
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith("first", "New label");
});

it("shows the empty-project state and preserves a refused new label", async () => {
  const user = userEvent.setup();
  runSprout.mockResolvedValue([]);
  const callbacks = props();
  callbacks.onAdd.mockResolvedValue(false);
  render(<LabelInput {...callbacks} />);
  await user.click(screen.getByRole("combobox"));
  expect(await screen.findByText("使用中のラベルはありません。新しいラベルを追加できます。")).toBeTruthy();
  await user.type(screen.getByRole("combobox"), "Keep draft");
  await user.click(screen.getByRole("button", { name: "追加" }));
  expect((screen.getByRole("combobox") as HTMLInputElement).value).toBe("Keep draft");
});

it.each(["project", "leaf"])("discards unfinished requests when the %s context is remounted", async (context) => {
  const user = userEvent.setup();
  const callbacks = props();
  let finish!: (values: unknown) => void;
  runSprout.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
  const view = render(<LabelInput key="old" {...callbacks} />);
  await user.click(screen.getByRole("combobox"));
  const next = context === "project" ? { ...callbacks, projectDir: "C:/other" } : { ...callbacks, leafId: "second" };
  view.rerender(<LabelInput key="new" {...next} />);
  await user.click(screen.getByRole("combobox"));
  await screen.findByRole("option", { name: "Draft 2件の葉" });
  await act(async () => { finish([{ name: "Old candidate", leaf_count: 99 }]); });
  expect(screen.queryByRole("option", { name: /Old candidate/ })).toBeNull();
  await user.click(screen.getByRole("option", { name: "Draft 2件の葉" }));
  expect(callbacks.onAdd).toHaveBeenCalledExactlyOnceWith(next.leafId, "Draft");
  expect(runSprout).toHaveBeenLastCalledWith(next.projectDir, ["leaf", "label", "list"], "");
});

it("refreshes counts after labels change and closes while another operation runs", async () => {
  const user = userEvent.setup();
  const initial = props();
  const view = render(<LabelInput {...initial} />);
  await user.click(screen.getByRole("combobox"));
  await screen.findByRole("option", { name: "Draft 2件の葉" });
  view.rerender(<LabelInput {...initial} busy />);
  expect(screen.queryByRole("listbox")).toBeNull();
  runSprout.mockResolvedValue([{ name: "Draft", leaf_count: 3 }]);
  view.rerender(<LabelInput {...initial} labels={["Draft"]} />);
  await user.click(screen.getByRole("combobox"));
  expect((await screen.findByRole("option", { name: "Draft 3件の葉・追加済み" }) as HTMLButtonElement).disabled).toBe(true);
  await waitFor(() => expect(runSprout).toHaveBeenCalledTimes(2));
});
