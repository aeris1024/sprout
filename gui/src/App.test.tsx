// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { SproutStatus } from "./lib/sprout";

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  confirm: vi.fn(),
  onDragDropEvent: vi.fn(),
  runSprout: vi.fn(),
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
  dragHandler: undefined as undefined | ((event: { payload: { type: string; paths: string[] } }) => void),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: mocks.open,
  confirm: mocks.confirm,
}));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ onDragDropEvent: mocks.onDragDropEvent }),
}));
vi.mock("./lib/sprout", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./lib/sprout")>()),
  runSprout: mocks.runSprout,
}));
vi.mock("./lib/settings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./lib/settings")>()),
  loadSettings: mocks.loadSettings,
  saveSettings: mocks.saveSettings,
}));

const project = "C:\\work\\sprout-project";
const cleanStatus: SproutStatus = {
  branch: "main",
  changes: [],
  tracked: ["design/main.psd"],
  untracked: ["notes.txt"],
};
const mainBranch = [{ name: "main", commit_id: "a".repeat(64), comment: "", current: true }];
const commitEntry = {
  id: "a".repeat(64),
  parent_id: null,
  created_at: "2026-08-09T00:00:00+00:00",
  message: "Initial design",
  note: null,
  note_updated_at: null,
  labels: [],
};

function mockWorkspace(status = cleanStatus, history = [commitEntry], branches = mainBranch) {
  mocks.runSprout.mockResolvedValueOnce(status).mockResolvedValueOnce(history).mockResolvedValueOnce(branches);
}

async function openWorkspace(user: ReturnType<typeof userEvent.setup>) {
  mocks.open.mockResolvedValueOnce(project);
  mockWorkspace();
  await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
  expect(await screen.findByRole("heading", { name: "sprout-project" })).toBeTruthy();
}

describe("Sprout GUI operations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.loadSettings.mockResolvedValue({ recentProjects: [], sproutProgram: "" });
    mocks.saveSettings.mockResolvedValue(undefined);
    mocks.confirm.mockResolvedValue(true);
    mocks.dragHandler = undefined;
    mocks.onDragDropEvent.mockImplementation(async (handler) => {
      mocks.dragHandler = handler;
      return vi.fn();
    });
  });

  afterEach(cleanup);

  it("offers init, loads the workspace, and remembers the project", async () => {
    const user = userEvent.setup();
    mocks.open.mockResolvedValue(project);
    mocks.runSprout
      .mockRejectedValueOnce({ code: "sprout_error", message: "not inside a Sprout project (run 'sprout init')", details: {} })
      .mockResolvedValueOnce({ root: project });
    mockWorkspace({ ...cleanStatus, tracked: [], untracked: [] }, [], mainBranch);

    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    expect(await screen.findByRole("heading", { name: "このフォルダはまだSproutプロジェクトではありません" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "このフォルダを初期化" }));

    expect(await screen.findByRole("heading", { name: "sprout-project" })).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["init", "."], "");
    await waitFor(() => expect(mocks.saveSettings).toHaveBeenCalled());
  });

  it("tracks an untracked file and refreshes status", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ paths: ["notes.txt"] });
    mockWorkspace({ ...cleanStatus, tracked: ["design/main.psd", "notes.txt"], untracked: [] });

    await user.click(screen.getByRole("button", { name: /notes.txt/ }));

    expect(await screen.findByText("1件を追跡対象に追加しました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["track", "notes.txt"], "");

    mocks.runSprout.mockResolvedValueOnce({ paths: ["design/main.psd"] });
    mockWorkspace({ ...cleanStatus, tracked: ["notes.txt"], untracked: ["design/main.psd"] });
    await user.click(screen.getAllByRole("button", { name: "追跡解除" })[0]);
    expect(await screen.findByText("1件を追跡対象から外しました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["untrack", "design/main.psd"], "");
  });

  it("tracks paths dropped on the Tauri window", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await waitFor(() => expect(mocks.dragHandler).toBeTypeOf("function"));
    mocks.runSprout.mockResolvedValueOnce({ paths: ["dropped.png"] });
    mockWorkspace({ ...cleanStatus, tracked: [...(cleanStatus.tracked ?? []), "dropped.png"] });

    await act(async () => {
      mocks.dragHandler?.({ payload: { type: "drop", paths: ["C:\\work\\sprout-project\\dropped.png"] } });
    });

    expect(await screen.findByText("1件を追跡対象に追加しました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["track", "C:\\work\\sprout-project\\dropped.png"], "");
  });

  it("refreshes workspace state when the window regains focus", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mockWorkspace({ ...cleanStatus, changes: [
      { state: "modified", path: "design/main.psd" },
      { state: "added", path: "notes.txt" },
    ] });

    window.dispatchEvent(new Event("focus"));

    await waitFor(() => expect(screen.getByText("2", { selector: ".summary-grid strong" })).toBeTruthy());
  });

  it("commits with a selected thumbnail and reports the new id", async () => {
    const user = userEvent.setup();
    const image = "C:\\work\\preview.png";
    render(<App />);
    await openWorkspace(user);
    await user.click(screen.getByRole("button", { name: "コミット" }));
    await user.type(screen.getByLabelText("コミットメッセージ"), "Save design");
    mocks.open.mockResolvedValueOnce(image);
    await user.click(screen.getByRole("button", { name: "選択" }));
    mocks.runSprout.mockResolvedValueOnce({ id: "b".repeat(64), branch: "main", message: "Save design", removed_paths: [] });
    mockWorkspace(cleanStatus, [{ ...commitEntry, id: "b".repeat(64), message: "Save design" }, commitEntry]);

    await user.click(screen.getByRole("button", { name: "コミットを作成" }));

    expect(await screen.findByText(/コミット bbbbbbbbbbbb を作成しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["commit", "-m", "Save design", "--thumbnail", image], "");
  });

  it("blocks overlapping commands while a commit is running", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.click(screen.getByRole("button", { name: "コミット" }));
    await user.type(screen.getByLabelText("コミットメッセージ"), "Long snapshot");
    let finishCommit: (value: unknown) => void = () => undefined;
    const pendingCommit = new Promise((resolve) => {
      finishCommit = resolve;
    });
    mocks.runSprout.mockImplementationOnce(() => pendingCommit);
    mockWorkspace();

    const commitButton = screen.getByRole("button", { name: "コミットを作成" }) as HTMLButtonElement;
    await user.click(commitButton);
    expect(commitButton.disabled).toBe(true);
    commitButton.click();
    expect(mocks.runSprout.mock.calls.filter((call) => call[1][0] === "commit")).toHaveLength(1);

    await act(async () => {
      finishCommit({ id: "c".repeat(64), branch: "main", message: "Long snapshot", removed_paths: [] });
    });
    expect(await screen.findByText(/コミット cccccccccccc を作成しました/)).toBeTruthy();
  });

  it("loads commit detail and confirms discard before restore", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.click(screen.getByRole("button", { name: "履歴" }));
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_name: "main", thumbnail: null, files: [{ path: "design/main.psd", object_hash: "f".repeat(64), size: 42, mtime_ns: 0 }] });
    await user.click(screen.getByRole("button", { name: /Initial design/ }));
    expect(await screen.findByText("42 bytes")).toBeTruthy();

    mocks.runSprout
      .mockRejectedValueOnce({ code: "uncommitted_changes", message: "working tree has uncommitted changes", details: { can_discard: true } })
      .mockResolvedValueOnce({ commit_id: commitEntry.id, paths: null });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "このコミットを復元" }));

    expect(await screen.findByText(/の内容を復元しました/)).toBeTruthy();
    expect(mocks.confirm).toHaveBeenCalledWith(expect.stringContaining("取り消せません"), expect.objectContaining({ kind: "warning" }));
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["restore", commitEntry.id, "--discard"], "");
  });

  it("creates and switches branches", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.click(screen.getByRole("button", { name: "ブランチ" }));
    await user.type(screen.getByLabelText("ブランチ名"), "alternate");
    await user.type(screen.getByLabelText("コメント（任意）"), "別案");
    mocks.runSprout.mockResolvedValueOnce({ name: "alternate", commit_id: commitEntry.id, comment: "別案", current: false });
    const twoBranches = [...mainBranch, { name: "alternate", commit_id: commitEntry.id, comment: "別案", current: false }];
    mockWorkspace(cleanStatus, [commitEntry], twoBranches);
    await user.click(screen.getByRole("button", { name: "作成" }));
    expect(await screen.findByText("ブランチ alternate を作成しました")).toBeTruthy();

    mocks.runSprout.mockResolvedValueOnce({ branch: "alternate", commit_id: commitEntry.id });
    mockWorkspace({ ...cleanStatus, branch: "alternate" }, [commitEntry], twoBranches.map((branch) => ({ ...branch, current: branch.name === "alternate" })));
    await user.click(screen.getByRole("button", { name: "切り替え" }));
    expect(await screen.findByText("alternate に切り替えました")).toBeTruthy();
  });

  it("shows a retry action for repository locks", async () => {
    const user = userEvent.setup();
    mocks.open.mockResolvedValue(project);
    mocks.runSprout.mockRejectedValueOnce({ code: "repository_locked", message: "another operation is running", details: { retryable: true } });
    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    expect((await screen.findByRole("alert")).textContent).toContain("another operation is running");
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "再試行" }));
    expect(await screen.findByRole("heading", { name: "sprout-project" })).toBeTruthy();
  });
});
