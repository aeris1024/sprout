// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { BranchInfo, CommitDeletion, CommitGraph, CommitLogEntry, SproutStatus } from "./lib/sprout";

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  save: vi.fn(),
  confirm: vi.fn(),
  onDragDropEvent: vi.fn(),
  onFocusChanged: vi.fn(),
  focusHandler: undefined as undefined | ((event: { payload: boolean }) => void),
  invoke: vi.fn(),
  runSprout: vi.fn(),
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
  dragHandler: undefined as undefined | ((event: { payload: { type: string; paths: string[] } }) => void),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: mocks.open,
  save: mocks.save,
  confirm: mocks.confirm,
}));
vi.mock("@tauri-apps/api/window", () => ({
  getCurrentWindow: () => ({ onDragDropEvent: mocks.onDragDropEvent, onFocusChanged: mocks.onFocusChanged }),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));
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
  branch_id: "main",
  current_commit: "a".repeat(64),
  at_branch_tip: true,
  changes: [],
  tracked: ["design/main.psd"],
  untracked: ["notes.txt"],
};
const mainBranch = [{ id: "main", name: "main", commit_id: "a".repeat(64), comment: "", current: true }];
const commitEntry = {
  id: "a".repeat(64),
  parent_id: null,
  created_at: "2026-08-09T00:00:00+00:00",
  message: "Initial design",
  note: null,
  note_updated_at: null,
  labels: [],
};

function mockWorkspace(
  status: SproutStatus = cleanStatus,
  history: CommitLogEntry[] = [commitEntry],
  branches: BranchInfo[] = mainBranch,
  graphOverride?: CommitGraph,
) {
  const graph: CommitGraph = graphOverride ?? {
    current_commit: branches.find((branch) => branch.current)?.commit_id ?? null,
    at_branch_tip: true,
    commits: history.map((entry, index) => ({
      ...entry,
      parent_id: entry.parent_id ?? (index + 1 < history.length ? history[index + 1].id : null),
      branch_id: "main", branch_name: "main",
      attachments: [],
    })),
    branches,
    tags: [],
    buds: [],
  };
  mocks.runSprout.mockResolvedValueOnce(status).mockResolvedValueOnce(graph);
}

function clipboardData(file: File | null, text = "") {
  const items = file ? [{ kind: "file", type: file.type, getAsFile: () => file }] : [{ kind: "string", type: "text/plain", getAsFile: () => null }];
  return { items, files: file ? [file] : [], getData: () => text, types: file ? ["Files"] : ["text/plain"] };
}

function mockPasteCommands(tempPath: string) {
  mocks.invoke.mockImplementation(async (command: string) => {
    if (command === "save_pasted_thumbnail") return tempPath;
    if (command === "discard_pasted_thumbnail") return undefined;
    return "data:image/png;base64,AQID";
  });
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
    mocks.invoke.mockResolvedValue("data:image/png;base64,AQID");
    mocks.dragHandler = undefined;
    mocks.onDragDropEvent.mockImplementation(async (handler) => {
      mocks.dragHandler = handler;
      return vi.fn();
    });
    mocks.focusHandler = undefined;
    mocks.onFocusChanged.mockImplementation(async (handler) => {
      mocks.focusHandler = handler;
      return vi.fn();
    });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("shows one screen with a top bar, map area, and side panel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);

    expect(screen.queryByRole("navigation", { name: "プロジェクト操作" })).toBeNull();
    expect(screen.getByRole("region", { name: "スナップショット" })).toBeTruthy();
    expect(screen.getByLabelText("現在のブランチ").textContent).toBe("main");
    expect(screen.getByLabelText("保存状態").textContent).toBe("保存済み");
    for (const name of ["ファイル", "保存", "設定", "プロジェクトを切り替え"]) {
      expect(screen.getByRole("button", { name })).toBeTruthy();
    }
    expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
    expect(mocks.runSprout.mock.calls.map((call) => call[1][0])).toEqual(["status", "tree"]);
  });

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

  it("opens and forgets recent projects from the welcome screen and project menu", async () => {
    const user = userEvent.setup();
    mocks.loadSettings.mockResolvedValue({ recentProjects: [project], sproutProgram: "" });
    render(<App />);
    const removeName = "sprout-projectを最近使った一覧から削除";
    const recentProject = await screen.findByRole("button", { name: /sprout-project.*C:\\work\\sprout-project/ });
    mockWorkspace();
    await user.click(recentProject);
    expect(await screen.findByRole("heading", { name: "sprout-project" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "プロジェクトを切り替え" }));
    await user.click(screen.getByRole("button", { name: removeName }));
    await waitFor(() => expect(screen.queryByRole("button", { name: removeName })).toBeNull());
    expect(screen.getByRole("heading", { name: "sprout-project" })).toBeTruthy();
    expect(mocks.saveSettings).toHaveBeenLastCalledWith({ recentProjects: [], sproutProgram: "" });

    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "フォルダを開く…" }));
    await waitFor(() => expect(mocks.saveSettings).toHaveBeenLastCalledWith({ recentProjects: [project], sproutProgram: "" }));
    await user.click(screen.getByRole("button", { name: "プロジェクトを切り替え" }));
    expect(await screen.findByRole("button", { name: removeName })).toBeTruthy();
  });

  it("saves the CLI path from the settings gear", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "設定" }));
    const settings = screen.getByRole("region", { name: "CLI設定" });
    await user.type(within(settings).getByLabelText("Sprout CLIのパス"), "C:\\Tools\\sprout.exe");
    await user.click(within(settings).getByRole("button", { name: "保存" }));
    expect(await screen.findByText("CLI設定を保存しました")).toBeTruthy();
    expect(mocks.saveSettings).toHaveBeenLastCalledWith({ recentProjects: [], sproutProgram: "C:\\Tools\\sprout.exe" });
  });

  it("tracks and untracks files from the file panel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.click(screen.getByRole("button", { name: "ファイル" }));
    const panel = screen.getByRole("region", { name: "追跡ファイル" });
    mocks.runSprout.mockResolvedValueOnce({ paths: ["notes.txt"] });
    mockWorkspace({ ...cleanStatus, tracked: ["design/main.psd", "notes.txt"], untracked: [] });

    await user.click(within(panel).getByRole("button", { name: "追跡する" }));

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

  it("refreshes workspace state from the update button and ignores DOM focus events", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const initialCalls = mocks.runSprout.mock.calls.length;
    mockWorkspace({ ...cleanStatus, changes: [
      { state: "modified", path: "design/main.psd" },
      { state: "added", path: "notes.txt" },
    ] });

    window.dispatchEvent(new Event("focus"));
    expect(mocks.runSprout).toHaveBeenCalledTimes(initialCalls);

    await user.click(screen.getByRole("button", { name: "更新" }));

    await waitFor(() => expect(screen.getByLabelText("保存状態").textContent).toBe("未保存の変更 2"));
    expect(screen.getByRole("heading", { name: "未保存の変更 2件" })).toBeTruthy();
  });

  it("commits with a selected thumbnail and reports the new id", async () => {
    const user = userEvent.setup();
    const image = "C:\\work\\preview.png";
    render(<App />);
    await openWorkspace(user);
    await user.type(screen.getByLabelText("メッセージ"), "Save design");
    mocks.open.mockResolvedValueOnce(image);
    await user.click(screen.getByRole("button", { name: "選択" }));
    mocks.runSprout.mockResolvedValueOnce({ id: "b".repeat(64), branch: "main", branch_id: "main", created_branch: false, message: "Save design", removed_paths: [] });
    mockWorkspace(cleanStatus, [{ ...commitEntry, id: "b".repeat(64), message: "Save design" }, commitEntry]);

    await user.click(screen.getByRole("button", { name: "保存して葉にする" }));

    expect(await screen.findByText(/コミット bbbbbbbbbbbb を作成しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["commit", "-m", "Save design", "--thumbnail", image], "");
  });

  it("commits with a pasted clipboard image as the thumbnail and discards the temporary file", async () => {
    const user = userEvent.setup();
    const tempPath = "C:\temp\sprout-gui-paste-1-0\clipboard.png";
    mockPasteCommands(tempPath);
    render(<App />);
    await openWorkspace(user);
    await user.type(screen.getByLabelText("メッセージ"), "Save design");

    const image = new File([new Uint8Array([1, 2, 3])], "image.png", { type: "image/png" });
    fireEvent.paste(document.body, { clipboardData: clipboardData(image) });

    expect(await screen.findByDisplayValue("貼り付けた画像")).toBeTruthy();
    expect(mocks.invoke).toHaveBeenCalledWith("save_pasted_thumbnail", { mediaType: "image/png", data: "AQID" });
    mocks.runSprout.mockResolvedValueOnce({ id: "b".repeat(64), branch: "main", branch_id: "main", created_branch: false, message: "Save design", removed_paths: [] });
    mockWorkspace(cleanStatus, [{ ...commitEntry, id: "b".repeat(64), message: "Save design" }, commitEntry]);
    await user.click(screen.getByRole("button", { name: "保存して葉にする" }));

    expect(await screen.findByText(/コミット bbbbbbbbbbbb を作成しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["commit", "-m", "Save design", "--thumbnail", tempPath], "");
    expect(mocks.invoke).toHaveBeenCalledWith("discard_pasted_thumbnail", { path: tempPath });
  });

  it("keeps text pastes and rejects unsupported clipboard images without changing the thumbnail", async () => {
    const user = userEvent.setup();
    mockPasteCommands("unused");
    render(<App />);
    await openWorkspace(user);

    const message = screen.getByLabelText("メッセージ");
    const textPaste = fireEvent.paste(message, { clipboardData: clipboardData(null, "hello") });
    expect(textPaste).toBe(true);

    const gif = new File([new Uint8Array([1])], "anim.gif", { type: "image/gif" });
    fireEvent.paste(document.body, { clipboardData: clipboardData(gif) });
    expect(await screen.findByText(/サムネイルに使えない形式です/)).toBeTruthy();

    const large = new File([new Uint8Array(2 * 1024 * 1024 + 1)], "large.png", { type: "image/png" });
    fireEvent.paste(document.body, { clipboardData: clipboardData(large) });
    expect(await screen.findByText(/上限（2 MiB）を超えています/)).toBeTruthy();

    expect(mocks.invoke).not.toHaveBeenCalledWith("save_pasted_thumbnail", expect.anything());
    expect((screen.getByPlaceholderText(/Ctrl\+Vで画像を貼り付け/) as HTMLInputElement).value).toBe("");
  });

  it("reports a branch grown from a past snapshot", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.type(screen.getByLabelText("メッセージ"), "Alternative");
    mocks.runSprout.mockResolvedValueOnce({ id: "b".repeat(64), branch: "branch-20261028-120000", created_branch: true, message: "Alternative", removed_paths: [] });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "保存して葉にする" }));
    expect(await screen.findByText("新しい枝 branch-20261028-120000 を作り、bbbbbbbbbbbb を保存しました")).toBeTruthy();
  });

  it("blocks overlapping commands while a commit is running", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    await user.type(screen.getByLabelText("メッセージ"), "Long snapshot");
    let finishCommit: (value: unknown) => void = () => undefined;
    const pendingCommit = new Promise((resolve) => {
      finishCommit = resolve;
    });
    mocks.runSprout.mockImplementationOnce(() => pendingCommit);
    mockWorkspace();

    const commitButton = screen.getByRole("button", { name: "保存して葉にする" }) as HTMLButtonElement;
    await user.click(commitButton);
    expect(commitButton.disabled).toBe(true);
    commitButton.click();
    expect(mocks.runSprout.mock.calls.filter((call) => call[1][0] === "commit")).toHaveLength(1);

    await act(async () => {
      finishCommit({ id: "c".repeat(64), branch: "main", branch_id: "main", message: "Long snapshot", removed_paths: [] });
    });
    expect(await screen.findByText(/コミット cccccccccccc を作成しました/)).toBeTruthy();
  });

  it("moves to a snapshot without confirmation and updates from one reply", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const graph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "main", branch_name: "main", message: "Current tip", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "main", branch_name: "main", message: "Past commit", attachments: [] },
      ],
      branches: [{ id: "main", name: "main", commit_id: tipId, comment: "", current: true }],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace({ ...cleanStatus, current_commit: tipId, at_branch_tip: true, changes: [{ state: "modified", path: "design/main.psd" }] }, [], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });
    expect(screen.getByRole("button", { name: "未保存の芽" })).toBeTruthy();

    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: rootId, branch_id: "main", branch_name: "main", message: "Past commit", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Past commit" }));
    expect(screen.getByRole("button", { name: "Past commit" }).getAttribute("aria-pressed")).toBe("true");
    expect(await screen.findByText("移動すると、未保存の変更 1件は今の芽につぼみとして残ります。")).toBeTruthy();

    const bud = { id: "f".repeat(32), base_commit_id: tipId, branch_id: "main", branch_name: "main", created_at: "2026-10-28T00:00:00+00:00", changes: [{ state: "modified", path: "design/main.psd" }], files: [] };
    mocks.runSprout.mockResolvedValueOnce({ current_commit: rootId, branch: "main", branch_id: "main", at_branch_tip: false, bud, changes: [] });
    const callsBefore = mocks.runSprout.mock.calls.length;
    await user.click(screen.getByRole("button", { name: "ここへ移動" }));

    expect(await screen.findByText(/未保存の変更をつぼみに残して dddddddddddd へ移動しました/)).toBeTruthy();
    expect(mocks.runSprout.mock.calls.slice(callsBefore).map((call) => call[1])).toEqual([["go", rootId]]);
    expect(mocks.confirm).not.toHaveBeenCalled();
    expect(screen.getByLabelText("保存状態").textContent).toBe("保存済み");
    expect(screen.getByRole("button", { name: "つぼみ（1件の変更）" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "この芽にいます" })).toBeTruthy();
  });

  it("marks the current snapshot in its panel", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await screen.findByRole("region", { name: "選択中のスナップショット" });
    expect(screen.getByRole("button", { name: "この芽にいます" })).toBeTruthy();
  });

  it("reports untracked conflicts with the path when moving", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const graph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "main", branch_name: "main", message: "Current tip", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "main", branch_name: "main", message: "Past commit", attachments: [] },
      ],
      branches: [{ id: "main", name: "main", commit_id: tipId, comment: "", current: true }],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace(cleanStatus, [], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: rootId, branch_id: "main", branch_name: "main", message: "Past commit", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Past commit" }));
    mocks.runSprout.mockRejectedValueOnce({ code: "untracked_conflict", message: "untracked path would be overwritten: notes.txt", details: { path: "notes.txt" } });
    await user.click(await screen.findByRole("button", { name: "ここへ移動" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("untracked path would be overwritten: notes.txt（作業フォルダは変更していません。）");
    expect(alert.textContent).toContain("対象: notes.txt");
  });

  it("restores and drops buds from the bud panel", async () => {
    const user = userEvent.setup();
    const tipId = commitEntry.id;
    const bud = { id: "f".repeat(32), base_commit_id: tipId, branch_id: "main", branch_name: "main", created_at: "2026-10-28T00:00:00+00:00", changes: [{ state: "modified", path: "design/main.psd" }], files: [] };
    const graph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [{ ...commitEntry, branch_id: "main", branch_name: "main", attachments: [] }],
      branches: mainBranch,
      tags: [],
      buds: [bud],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace(cleanStatus, [], mainBranch, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    await user.click(screen.getByRole("button", { name: "つぼみ（1件の変更）" }));
    expect(screen.getByRole("heading", { name: "「Initial design」の上の変更 1件" })).toBeTruthy();

    mocks.confirm.mockResolvedValueOnce(false);
    await user.click(screen.getByRole("button", { name: "つぼみを捨てる" }));
    expect(mocks.confirm).toHaveBeenCalledWith(expect.stringContaining("ゴミ箱から戻せます"), expect.objectContaining({ kind: "warning" }));
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "bud")).toBe(false);

    mocks.runSprout.mockResolvedValueOnce({ restored: bud, saved: null });
    mockWorkspace({ ...cleanStatus, changes: [{ state: "modified", path: "design/main.psd" }] }, [], mainBranch, { ...graph, buds: [] });
    await user.click(screen.getByRole("button", { name: "このつぼみに戻る" }));
    expect(await screen.findByText("つぼみの変更に戻りました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["bud", "--restore", bud.id], "");
    expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
  });

  it("opens the save form from the unsaved bud, top bar, and Ctrl+S and warns about new branches", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const graph: CommitGraph = {
      current_commit: rootId,
      at_branch_tip: false,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "main", branch_name: "main", message: "Current tip", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "main", branch_name: "main", message: "Past commit", attachments: [] },
      ],
      branches: [{ id: "main", name: "main", commit_id: tipId, comment: "", current: true }],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace({ ...cleanStatus, current_commit: rootId, at_branch_tip: false, changes: [{ state: "modified", path: "design/main.psd" }] }, [], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: tipId, branch_id: "main", branch_name: "main", message: "Current tip", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Current tip" }));
    await screen.findByRole("region", { name: "選択中のスナップショット" });
    await user.keyboard("{Control>}s{/Control}");
    expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
    expect(screen.getByText("途中の芽から保存するため、新しい枝が自動で作られます。")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "ファイル" }));
    await user.click(screen.getByRole("button", { name: "保存" }));
    expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "未保存の芽" }));
    expect(screen.getByRole("button", { name: "未保存の芽" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("grows a named branch and exports files from a snapshot", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await user.click(await screen.findByRole("button", { name: "ここから枝を伸ばす" }));
    await user.type(screen.getByLabelText("新しい枝の名前"), "rethink");
    mocks.runSprout.mockResolvedValueOnce({ id: "rethink", name: "rethink", commit_id: commitEntry.id, comment: "", current: true, bud: null });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "枝を作って移動" }));
    expect(await screen.findByText("aaaaaaaaaaaa から枝 rethink を伸ばしました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["branch", "rethink", commitEntry.id, "--switch", "--keep-changes"], "");
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "go")).toBe(false);

    mocks.open.mockResolvedValueOnce("C:\\work\\out");
    mocks.runSprout.mockResolvedValueOnce({ commit_id: commitEntry.id, output: "C:\\work\\out", paths: ["design/main.psd"] });
    await user.click(screen.getByRole("button", { name: "ファイルを取り出す" }));
    expect(await screen.findByText("1件のファイルを C:\\work\\out へ書き出しました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["export", commitEntry.id, "--output", "C:\\work\\out"], "");
  });

  it("keeps the typed name and reports nothing moved when a branch is refused", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await user.click(await screen.findByRole("button", { name: "ここから枝を伸ばす" }));
    await user.type(screen.getByLabelText("新しい枝の名前"), "main");
    mocks.runSprout.mockRejectedValueOnce({ code: "sprout_error", message: "branch already exists: main", details: {} });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "枝を作って移動" }));
    expect(await screen.findByText(/branch already exists: main.*作業フォルダは変更していません/)).toBeTruthy();
    expect((screen.getByLabelText("新しい枝の名前") as HTMLInputElement).value).toBe("main");
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "go")).toBe(false);
  });

  it("reports a bud kept while growing a branch", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await user.click(await screen.findByRole("button", { name: "ここから枝を伸ばす" }));
    await user.type(screen.getByLabelText("新しい枝の名前"), "rethink");
    mocks.runSprout.mockResolvedValueOnce({ id: "rethink", bud: { id: "bud1" } });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "枝を作って移動" }));
    expect(await screen.findByText("未保存の変更をつぼみに残して aaaaaaaaaaaa から枝 rethink を伸ばしました")).toBeTruthy();
  });

  it("shows the sprout map with thumbnails and selected commit actions", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const thumbnail = {
      id: "attachment-fixture", position: 0,
      commit_id: tipId,
      role: "thumbnail",
      original_name: "tree.png",
      media_type: "image/png",
      object_hash: "f".repeat(64),
      size: 3,
      created_at: "2026-08-09T00:00:00+00:00",
      updated_at: "2026-08-09T00:00:00+00:00",
    };
    const videoPreview = {
      ...thumbnail,
      commit_id: rootId,
      role: "preview",
      original_name: "walkthrough.mp4",
      media_type: "video/mp4",
      object_hash: "7".repeat(64),
    };
    const treeGraph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "main", branch_name: "main", message: "Tree tip", attachments: [thumbnail] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "archived", branch_name: "archived", message: "Deleted branch root", attachments: [videoPreview] },
      ],
      branches: [
        { id: "main", name: "main", commit_id: tipId, comment: "", current: true },
        { id: "alternate", name: "alternate", commit_id: tipId, comment: "別案", current: false },
      ],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace(cleanStatus, [commitEntry], treeGraph.branches, treeGraph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    expect(screen.getByText("削除済みブランチ由来: archived")).toBeTruthy();
    expect(screen.getByRole("button", { name: "ブランチ main" }).textContent).toBe("main（現在のブランチ）");
    expect(screen.getByRole("button", { name: "ブランチ alternate" }).textContent).toBe("alternate");
    expect(screen.getByText("いまここ")).toBeTruthy();
    expect(await screen.findByRole("img", { name: "Tree tipのサムネイル" })).toBeTruthy();
    expect(document.querySelector("video, audio")).toBeNull();
    expect(mocks.invoke).toHaveBeenCalledTimes(1);

    const detail = { ...commitEntry, id: tipId, branch_id: "main", branch_name: "main", message: "Tree tip", thumbnail, attachments: [thumbnail], files: [] };
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: /Tree tip/ }));
    expect(await screen.findByRole("button", { name: "この芽にいます" })).toBeTruthy();
    expect(screen.getByText("main, alternate", { selector: "dd" })).toBeTruthy();

    const image = "C:\\work\\replacement.png";
    mocks.open.mockResolvedValueOnce(image);
    mocks.runSprout.mockResolvedValueOnce(thumbnail);
    mockWorkspace(cleanStatus, [commitEntry], treeGraph.branches, treeGraph);
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: "サムネイルを変更" }));
    expect(await screen.findByText(/のサムネイルを保存しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["thumbnail", tipId, image], "");
  });

  it("edits a selected commit message and refreshes the map and detail", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const detail = { ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] };
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: /Initial design/ }));
    expect(await screen.findByRole("button", { name: "メッセージを編集" })).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "メッセージを編集" }));
    const editor = screen.getByLabelText("コミットメッセージを編集");
    await user.clear(editor);
    await user.type(editor, "Renamed snapshot");
    const updatedEntry = { ...commitEntry, message: "Renamed snapshot" };
    mocks.runSprout.mockResolvedValueOnce({ commit_id: commitEntry.id, message: "Renamed snapshot" });
    mockWorkspace(cleanStatus, [updatedEntry]);
    mocks.runSprout.mockResolvedValueOnce({ ...detail, message: "Renamed snapshot" });
    await user.click(within(editor.closest("form") as HTMLElement).getByRole("button", { name: "保存" }));

    expect(await screen.findByText(/のコミットメッセージを変更しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["message", commitEntry.id, "Renamed snapshot"], "");
    expect(screen.getByRole("heading", { name: "Renamed snapshot" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Renamed snapshot" })).toBeTruthy();
  });

  it("registers a past commit thumbnail after a dialog focus event", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const rootEntry = { ...commitEntry, id: rootId, parent_id: null, message: "Past commit" };
    const tipEntry = { ...commitEntry, id: tipId, parent_id: rootId, message: "Current tip" };
    const graph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...tipEntry, branch_id: "main", branch_name: "main", attachments: [] },
        { ...rootEntry, branch_id: "main", branch_name: "main", attachments: [] },
      ],
      branches: [{ id: "main", name: "main", commit_id: tipId, comment: "", current: true }],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace(cleanStatus, [tipEntry, rootEntry], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    const detail = { ...rootEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] };
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: /Past commit/ }));
    expect(await screen.findByRole("button", { name: "サムネイルを登録" })).toBeTruthy();

    const image = "C:\\work\\past.png";
    let finishDialog: (value: string) => void = () => undefined;
    mocks.open.mockImplementationOnce(() => new Promise<string>((resolve) => {
      finishDialog = resolve;
    }));
    await user.click(screen.getByRole("button", { name: "サムネイルを登録" }));
    const callsBeforeFocus = mocks.runSprout.mock.calls.length;
    window.dispatchEvent(new Event("focus"));
    expect(mocks.runSprout).toHaveBeenCalledTimes(callsBeforeFocus);

    const thumbnail = {
      id: "attachment-fixture", position: 0,
      commit_id: rootId,
      role: "thumbnail" as const,
      original_name: "past.png",
      media_type: "image/png",
      object_hash: "f".repeat(64),
      size: 3,
      created_at: "2026-08-09T00:00:00+00:00",
      updated_at: "2026-08-09T00:00:00+00:00",
    };
    const updatedGraph: CommitGraph = {
      ...graph,
      commits: [graph.commits[0], { ...graph.commits[1], attachments: [thumbnail] }],
    };
    mocks.runSprout.mockResolvedValueOnce(thumbnail);
    mockWorkspace(cleanStatus, [tipEntry, rootEntry], graph.branches, updatedGraph);
    mocks.runSprout.mockResolvedValueOnce({ ...detail, thumbnail });
    await act(async () => finishDialog(image));

    expect(await screen.findByText(/のサムネイルを保存しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["thumbnail", rootId, image], "");
    expect(await screen.findByRole("img", { name: "Past commitのサムネイル" })).toBeTruthy();
  });

  it("registers a pasted clipboard image as the selected commit's thumbnail", async () => {
    const user = userEvent.setup();
    const tempPath = "C:\temp\sprout-gui-paste-1-1\clipboard.webp";
    mockPasteCommands(tempPath);
    render(<App />);
    await openWorkspace(user);
    const detail = { ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] };
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: /Initial design/ }));
    expect(await screen.findByRole("button", { name: "サムネイルを登録" })).toBeTruthy();

    mocks.runSprout.mockResolvedValueOnce({});
    mockWorkspace();
    mocks.runSprout.mockResolvedValueOnce(detail);
    const image = new File([new Uint8Array([1, 2, 3])], "image.webp", { type: "image/webp" });
    fireEvent.paste(document.body, { clipboardData: clipboardData(image) });

    expect(await screen.findByText(/のサムネイルを保存しました/)).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["thumbnail", commitEntry.id, tempPath], "");
    await waitFor(() => expect(mocks.invoke).toHaveBeenCalledWith("discard_pasted_thumbnail", { path: tempPath }));
  });

  it("selects leaves with the keyboard and zooms the map", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const leaf = screen.getByRole("button", { name: "Initial design" });
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    leaf.focus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("region", { name: "選択中のスナップショット" })).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenLastCalledWith(project, ["show", commitEntry.id], "");

    const canvas = screen.getByRole("group", { name: "芽のマップ" });
    const width = Number(canvas.getAttribute("width"));
    await user.click(screen.getByRole("button", { name: "縮小" }));
    expect(Number(canvas.getAttribute("width"))).toBeCloseTo(width * 0.75);
    await user.click(screen.getByRole("button", { name: "詳細を閉じる" }));
    expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
  });

  it.each([
    ["unsupported_repository_format", "unsupported repository schema version: 99 (expected 1)"],
    ["unsupported_restore_plan_version", "invalid restore recovery plan: unsupported version; backups retained"],
    ["unsupported_object_encoding", "unsupported object encoding 'future': abc123"],
  ])("shows compatibility reasons for %s without offering initialization", async (code, message) => {
    const user = userEvent.setup();
    mocks.open.mockResolvedValue(project);
    mocks.runSprout.mockRejectedValueOnce({ code, message, details: {} });
    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    expect((await screen.findByRole("alert")).textContent).toContain(message);
    expect(await screen.findByRole("heading", { name: "このプロジェクトを開けませんでした" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "このフォルダを初期化" })).toBeNull();
    expect(mocks.runSprout).toHaveBeenCalledTimes(1);
  });

  it.each(["restore", "purge"])("inspects trash and confirms %s with capacity and cancellation", async (action) => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const item = { id: "trash-1", kind: "commit", title: "Removed leaf", target_id: commitEntry.id,
      created_at: commitEntry.created_at, protected_bytes: 120, reclaimable_bytes: 40, objects: [] };
    mocks.runSprout.mockResolvedValueOnce([item]);
    await user.click(screen.getByRole("button", { name: "ゴミ箱" }));
    const region = await screen.findByRole("region", { name: "ゴミ箱" });
    expect(region.textContent).toContain("120 B");
    mocks.runSprout.mockResolvedValueOnce({ ...item, changes: [{ table: "commit_files", before: { path: "saved.bin", size: 7 }, after: null }] });
    await user.click(within(region).getByRole("button", { name: "Removed leafの復旧内容を確認" }));
    expect(await screen.findByText("パス: saved.bin")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["trash", "show", item.id], "");
    const buttonName = action === "restore" ? "Removed leafを復旧" : "Removed leafを完全削除";
    mocks.runSprout.mockResolvedValueOnce(item);
    mocks.confirm.mockResolvedValueOnce(false);
    await user.click(within(region).getByRole("button", { name: buttonName }));
    await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["trash", action, item.id, "--dry-run"], "");
    expect(mocks.runSprout.mock.calls.some((call) => call[1].join(" ") === `trash ${action} ${item.id}`)).toBe(false);
    if (action === "purge") {
      expect(mocks.confirm.mock.calls[0][0]).toContain("回収可能容量 40 B");
      expect(mocks.confirm.mock.calls[0][0]).toContain("元に戻せません");
    } else expect(mocks.confirm.mock.calls[0][0]).toContain("作業ファイルは変更しません");
    mocks.runSprout.mockResolvedValueOnce(item).mockResolvedValueOnce(item);
    if (action === "restore") mockWorkspace();
    mocks.runSprout.mockResolvedValueOnce([]);
    mocks.confirm.mockResolvedValueOnce(true);
    await user.click(within(region).getByRole("button", { name: buttonName }));
    expect(await screen.findByText("ゴミ箱は空です。")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["trash", action, item.id, ...(action === "purge" ? ["--yes"] : [])], "");
    await user.click(screen.getByRole("button", { name: "ゴミ箱を閉じる" }));
    expect(screen.queryByRole("region", { name: "ゴミ箱" })).toBeNull();
  });

  describe("maintenance panel", () => {
    const stats = { commits: 3, branches: 2, tracked_paths: 4, buds: 1, objects: 5, objects_bytes: 2048, logical_bytes: 4096, unique_bytes: 3072, dedup_saved_bytes: 1024 };
    const preview = { dry_run: true, removed_objects: 2, removed_temps: 1, freed_bytes: 2048, objects: ["a", "b"], temps: ["t"] };

    async function openPanel(user: ReturnType<typeof userEvent.setup>) {
      render(<App />);
      await openWorkspace(user);
      mocks.runSprout.mockResolvedValueOnce(stats);
      await user.click(screen.getByRole("button", { name: "保守" }));
      return screen.findByRole("region", { name: "保守" });
    }

    it("shows repository size and counts", async () => {
      const user = userEvent.setup();
      const panel = await openPanel(user);
      for (const text of ["3件", "2件", "4件", "1件", "5個", "4.0 KiB", "2.0 KiB", "1.0 KiB"]) expect(panel.textContent).toContain(text);
      expect(mocks.runSprout).toHaveBeenCalledWith(project, ["stats"], "");
    });

    it("collects only after confirmation and shows the result", async () => {
      const user = userEvent.setup();
      const panel = await openPanel(user);
      expect(panel.textContent).toContain("ゴミ箱に保持中のデータは回収しません");

      mocks.runSprout.mockResolvedValueOnce(preview);
      mocks.confirm.mockResolvedValueOnce(false);
      await user.click(within(panel).getByRole("button", { name: "回収できる容量を確認" }));
      await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
      expect(mocks.confirm.mock.calls[0][0]).toContain("オブジェクト 2個、一時ファイル 1個");
      expect(mocks.confirm.mock.calls[0][0]).toContain("2.0 KiB");
      expect(mocks.runSprout.mock.calls.some((call) => call[1].join(" ") === "gc")).toBe(false);

      mocks.runSprout
        .mockResolvedValueOnce(preview)
        .mockResolvedValueOnce({ ...preview, dry_run: false })
        .mockResolvedValueOnce({ ...stats, objects: 3, objects_bytes: 1024 });
      mocks.confirm.mockResolvedValueOnce(true);
      await user.click(within(panel).getByRole("button", { name: "回収できる容量を確認" }));
      expect(await within(panel).findByText(/オブジェクト 2個、一時ファイル 1個を削除し、2.0 KiBを回収しました/)).toBeTruthy();
      expect(mocks.runSprout).toHaveBeenCalledWith(project, ["gc"], "");
      expect(panel.textContent).toContain("3個");
    });

    it("says when nothing can be collected without asking", async () => {
      const user = userEvent.setup();
      const panel = await openPanel(user);
      mocks.runSprout.mockResolvedValueOnce({ ...preview, removed_objects: 0, removed_temps: 0, freed_bytes: 0, objects: [], temps: [] });
      await user.click(within(panel).getByRole("button", { name: "回収できる容量を確認" }));
      expect(await screen.findByText(/回収できる容量はありません/)).toBeTruthy();
      expect(mocks.confirm).not.toHaveBeenCalled();
    });

    it("shows a clean check and issues as results rather than failures", async () => {
      const user = userEvent.setup();
      const panel = await openPanel(user);
      mocks.runSprout.mockResolvedValueOnce({ ok: true, checked_objects: 12, issues: [] });
      await user.click(within(panel).getByRole("button", { name: "検査する" }));
      expect(await within(panel).findByText("問題はありません（12個を検査）")).toBeTruthy();
      expect(mocks.runSprout).toHaveBeenCalledWith(project, ["doctor", "--report"], "");

      mocks.runSprout.mockResolvedValueOnce({ ok: false, checked_objects: 12, issues: [{ kind: "corrupt_object", detail: "abc" }, { kind: "future_issue", detail: "x" }] });
      await user.click(within(panel).getByRole("button", { name: "検査する" }));
      expect(await within(panel).findByText("2件の問題が見つかりました（12個を検査）")).toBeTruthy();
      expect(within(panel).getByText("内容の破損: abc")).toBeTruthy();
      expect(within(panel).getByText("future_issue: x")).toBeTruthy();
      expect(screen.queryByText("操作を完了できませんでした")).toBeNull();
    });

    it("reports a failed collection and keeps the panel open", async () => {
      const user = userEvent.setup();
      const panel = await openPanel(user);
      mocks.runSprout.mockRejectedValueOnce({ code: "repository_locked", message: "another Sprout operation is already running", details: {} });
      await user.click(within(panel).getByRole("button", { name: "回収できる容量を確認" }));
      expect(await screen.findByText("another Sprout operation is already running")).toBeTruthy();
      expect(screen.getByRole("region", { name: "保守" })).toBeTruthy();
    });

    it("closes when another panel opens", async () => {
      const user = userEvent.setup();
      await openPanel(user);
      await user.click(screen.getByRole("button", { name: "ファイル" }));
      expect(screen.queryByRole("region", { name: "保守" })).toBeNull();
    });
  });

  it("shows trash restore conflicts without applying or losing the item", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const item = { id: "trash-1", kind: "preview_delete", title: "clip.wav", target_id: "preview-1",
      created_at: commitEntry.created_at, protected_bytes: 120, reclaimable_bytes: 40, objects: [] };
    mocks.runSprout.mockResolvedValueOnce([item]);
    await user.click(screen.getByRole("button", { name: "ゴミ箱" }));
    mocks.runSprout.mockRejectedValueOnce({ code: "trash_restore_conflict", message: "preview list changed", details: { trash_id: item.id } });
    await user.click(await screen.findByRole("button", { name: "clip.wavを復旧" }));
    expect((await screen.findByRole("alert")).textContent).toContain("preview list changed");
    expect(screen.getByRole("button", { name: "clip.wavを復旧" })).toBeTruthy();
    expect(mocks.confirm).not.toHaveBeenCalled();
    expect(mocks.runSprout.mock.calls.some((call) => call[1].join(" ") === `trash restore ${item.id}`)).toBe(false);
  });

  it("shows a retry action for repository locks", async () => {
    const user = userEvent.setup();
    mocks.open.mockResolvedValue(project);
    mocks.runSprout.mockRejectedValueOnce({ code: "repository_locked", message: "another operation is running", details: { retryable: true } });
    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    expect((await screen.findByRole("alert")).textContent).toContain("another operation is running");
    expect(await screen.findByRole("heading", { name: "このプロジェクトを開けませんでした" })).toBeTruthy();
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "再試行" }));
    expect(await screen.findByRole("heading", { name: "sprout-project" })).toBeTruthy();
  });

  it("identifies renamed, deleted, and reused branches by ID in panels and after moving", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const attachment = (id: string, role: string, position: number, name: string, size: number) => ({
      id, position, commit_id: rootId, role, original_name: name, media_type: role === "thumbnail" ? "image/png" : "application/x-future",
      object_hash: "7".repeat(64), size, created_at: "2026-10-28T00:00:00+00:00", updated_at: "2026-10-28T00:00:00+00:00",
    });
    const attachments = [attachment("t", "thumbnail", 0, "cover.png", 512), attachment("p1", "preview", 0, "turntable.bin", 2048), attachment("p2", "preview", 3, "sheet.bin", 3 * 1024 * 1024)];
    const rootBud = { id: "b".repeat(32), base_commit_id: null, branch_id: "gone-id", branch_name: "draft", created_at: "2026-10-28T00:00:00+00:00", changes: [{ state: "added", path: "scratch.psd" }], files: [] };
    const branches = [
      { id: "orig-id", name: "final", commit_id: rootId, comment: "", current: false },
      { id: "reused-id", name: "draft", commit_id: tipId, comment: "", current: true },
    ];
    const graph: CommitGraph = {
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "gone-id", branch_name: "draft", message: "Deleted work", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "orig-id", branch_name: "draft", message: "Renamed root", attachments: [] },
      ],
      branches,
      tags: [],
      buds: [rootBud],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace({ ...cleanStatus, branch: "draft", branch_id: "reused-id", current_commit: tipId }, [], branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: tipId, branch_id: "gone-id", branch_name: "draft", message: "Deleted work", thumbnail: null, attachments: [], files: [] });
    await user.click(screen.getByRole("button", { name: "Deleted work" }));
    expect(await screen.findByText("draft（削除済み）", { selector: "dd" })).toBeTruthy();
    expect(screen.getByText("なし", { selector: "dd" })).toBeTruthy();

    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: rootId, branch_id: "orig-id", branch_name: "draft", message: "Renamed root", thumbnail: attachments[0], attachments, files: [] });
    await user.click(screen.getByRole("button", { name: "Renamed root" }));
    expect(await screen.findByText("final（作成時: draft）", { selector: "dd" })).toBeTruthy();
    expect(within(screen.getByRole("list", { name: "添付" })).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "サムネイル: cover.png（image/png・512 B）",
      "プレビュー: turntable.bin（application/x-future・2.0 KiB）",
      "プレビュー: sheet.bin（application/x-future・3.0 MiB）",
    ]);

    mocks.runSprout.mockResolvedValueOnce({ current_commit: rootId, branch: "final", branch_id: "orig-id", at_branch_tip: true, bud: null, changes: [] });
    await user.click(screen.getByRole("button", { name: "ここへ移動" }));
    expect(await screen.findByText(/dddddddddddd へ移動しました/)).toBeTruthy();
    expect(screen.getByLabelText("現在のブランチ").textContent).toBe("final");
    expect(screen.getByText("final（現在のブランチ）")).toBeTruthy();
    expect(screen.getByText("draft")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "最初の保存前のつぼみ（1件の変更）" }));
    expect(screen.getByRole("heading", { name: "最初の保存前の変更 1件" })).toBeTruthy();
    expect(screen.getByText(/draft（削除済み）/)).toBeTruthy();
    expect(screen.getByText("退避したブランチは削除済みのため、戻しても今のブランチのままです。")).toBeTruthy();
  });

  it("lists buds kept before the first commit on an empty map and restores them", async () => {
    const user = userEvent.setup();
    const rootBud = { id: "c".repeat(32), base_commit_id: null, branch_id: "main", branch_name: "main", created_at: "2026-10-28T00:00:00+00:00", changes: [{ state: "added", path: "first.psd" }, { state: "added", path: "second.psd" }], files: [] };
    const graph: CommitGraph = { current_commit: null, at_branch_tip: true, commits: [], branches: [{ id: "main", name: "main", commit_id: null, comment: "", current: true }], tags: [], buds: [rootBud] };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace({ ...cleanStatus, current_commit: null }, [], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    expect(screen.getByText("最初の保存をすると、ここに芽が出ます。")).toBeTruthy();
    expect(screen.queryByText("いまここ")).toBeNull();
    await user.click(screen.getByRole("button", { name: "最初の保存前のつぼみ（2件の変更）" }));
    expect(screen.getByRole("heading", { name: "最初の保存前の変更 2件" })).toBeTruthy();
    expect(screen.queryByText(/戻しても今のブランチのまま/)).toBeNull();

    mocks.runSprout.mockResolvedValueOnce({ restored: rootBud, saved: null });
    mockWorkspace({ ...cleanStatus, current_commit: null, changes: rootBud.changes }, [], graph.branches, { ...graph, buds: [] });
    await user.click(screen.getByRole("button", { name: "このつぼみに戻る" }));
    expect(await screen.findByText("つぼみの変更に戻りました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["bud", "--restore", rootBud.id], "");
  });

  describe("snapshot notes, labels, and tags", () => {
    const detailOf = (overrides: Partial<CommitLogEntry> = {}) => ({ ...commitEntry, ...overrides, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] });
    const graphWith = (overrides: Partial<CommitLogEntry>, tags: CommitGraph["tags"] = []): CommitGraph => ({
      current_commit: commitEntry.id,
      at_branch_tip: true,
      commits: [{ ...commitEntry, ...overrides, branch_id: "main", branch_name: "main", attachments: [] }],
      branches: mainBranch,
      tags,
      buds: [],
    });

    /** Queue the CLI reply for an edit plus the refreshed workspace and detail. */
    function mockEdit(reply: unknown, overrides: Partial<CommitLogEntry>, tags: CommitGraph["tags"] = []) {
      mocks.runSprout.mockResolvedValueOnce(reply);
      mockWorkspace(cleanStatus, [], mainBranch, graphWith(overrides, tags));
      mocks.runSprout.mockResolvedValueOnce(detailOf(overrides));
    }

    async function openDetail(user: ReturnType<typeof userEvent.setup>) {
      render(<App />);
      await openWorkspace(user);
      mocks.runSprout.mockResolvedValueOnce(detailOf());
      await user.click(screen.getByRole("button", { name: "Initial design" }));
      await screen.findByRole("region", { name: "選択中のスナップショット" });
    }

    const id = commitEntry.id;
    const sentArgs = () => mocks.runSprout.mock.calls.map((call) => call[1]);

    it("writes, keeps on refusal, and deletes a note", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      const memo = within(screen.getByRole("region", { name: "メモ" }));
      expect(memo.getByText("メモはありません")).toBeTruthy();

      await user.click(memo.getByRole("button", { name: "メモを書く" }));
      await user.type(memo.getByRole("textbox", { name: "メモを編集" }), "x".repeat(5));
      mocks.runSprout.mockRejectedValueOnce({ code: "sprout_error", message: "note exceeds 20000 character limit", details: {} });
      await user.click(memo.getByRole("button", { name: "保存" }));
      expect(await screen.findByText("note exceeds 20000 character limit")).toBeTruthy();
      expect((memo.getByRole("textbox", { name: "メモを編集" }) as HTMLTextAreaElement).value).toBe("xxxxx");

      await user.clear(memo.getByRole("textbox", { name: "メモを編集" }));
      await user.type(memo.getByRole("textbox", { name: "メモを編集" }), "色味を確認");
      mockEdit({ commit_id: id, note: "色味を確認", note_updated_at: "now", labels: [] }, { note: "色味を確認", note_updated_at: "now" });
      await user.click(memo.getByRole("button", { name: "保存" }));
      expect(await screen.findByText(/のメモを保存しました/)).toBeTruthy();
      expect(sentArgs()).toContainEqual(["note", id, "色味を確認"]);
      expect(memo.getByText("色味を確認")).toBeTruthy();
      expect(memo.queryByRole("textbox")).toBeNull();

      await user.click(memo.getByRole("button", { name: "メモを編集" }));
      await user.clear(memo.getByRole("textbox", { name: "メモを編集" }));
      mockEdit({ commit_id: id, note: null, note_updated_at: null, labels: [] }, {});
      await user.click(memo.getByRole("button", { name: "保存" }));
      expect(await screen.findByText(/のメモを削除しました/)).toBeTruthy();
      expect(sentArgs()).toContainEqual(["note", id, "--delete"]);
      expect(memo.getByText("メモはありません")).toBeTruthy();
    });

    it("adds and removes labels and keeps a refused label in the input", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      const labels = within(screen.getByRole("region", { name: "ラベル" }));
      expect(labels.getByRole("button", { name: "追加" }).hasAttribute("disabled")).toBe(true);

      await user.type(labels.getByRole("textbox", { name: "追加するラベル" }), "a".repeat(65));
      mocks.runSprout.mockRejectedValueOnce({ code: "sprout_error", message: "label exceeds 64 character limit", details: {} });
      await user.click(labels.getByRole("button", { name: "追加" }));
      expect(await screen.findByText("label exceeds 64 character limit")).toBeTruthy();
      expect((labels.getByRole("textbox", { name: "追加するラベル" }) as HTMLInputElement).value).toHaveLength(65);

      await user.clear(labels.getByRole("textbox", { name: "追加するラベル" }));
      await user.type(labels.getByRole("textbox", { name: "追加するラベル" }), "承認済み");
      mockEdit({ commit_id: id, note: null, note_updated_at: null, labels: ["承認済み"] }, { labels: ["承認済み"] });
      await user.click(labels.getByRole("button", { name: "追加" }));
      expect(await screen.findByText("ラベル「承認済み」を追加しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["label", id, "承認済み"]);
      expect((labels.getByRole("textbox", { name: "追加するラベル" }) as HTMLInputElement).value).toBe("");

      mockEdit({ commit_id: id, note: null, note_updated_at: null, labels: [] }, {});
      await user.click(labels.getByRole("button", { name: "ラベル「承認済み」を外す" }));
      expect(await screen.findByText("ラベル「承認済み」を外しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["label", id, "--delete", "承認済み"]);
      expect(labels.getByText("ラベルはありません")).toBeTruthy();
    });

    it("creates, comments on, and deletes tags after confirmation", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      const tagRegion = () => within(screen.getByRole("region", { name: "タグ" }));
      const tag = { name: "提出版", commit_id: id, comment: "初稿", created_at: "2026-10-29T00:00:00+00:00" };

      await user.type(tagRegion().getByRole("textbox", { name: "新しいタグの名前" }), "提出版");
      await user.type(tagRegion().getByRole("textbox", { name: "新しいタグのコメント" }), "初稿");
      mockEdit(tag, {}, [tag]);
      await user.click(tagRegion().getByRole("button", { name: "タグを付ける" }));
      expect(await screen.findByText("タグ 提出版 を付けました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["tag", "提出版", id, "--comment", "初稿"]);
      expect(tagRegion().getByText("#提出版")).toBeTruthy();
      expect(tagRegion().getByText("初稿")).toBeTruthy();
      expect(screen.getByText("#提出版", { selector: "text" })).toBeTruthy();

      await user.click(tagRegion().getByRole("button", { name: "タグ「提出版」のコメントを編集" }));
      const comment = tagRegion().getByRole("textbox", { name: "タグ「提出版」のコメント" });
      await user.clear(comment);
      await user.type(comment, "最終版");
      mockEdit({ ...tag, comment: "最終版" }, {}, [{ ...tag, comment: "最終版" }]);
      await user.click(tagRegion().getByRole("button", { name: "保存" }));
      expect(await screen.findByText("タグ 提出版 のコメントを変更しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["tag", "提出版", "--set-comment", "最終版"]);
      expect(tagRegion().getByText("最終版")).toBeTruthy();

      mocks.confirm.mockResolvedValueOnce(false);
      await user.click(tagRegion().getByRole("button", { name: "タグ「提出版」を削除" }));
      expect(mocks.confirm).toHaveBeenCalledWith(expect.stringContaining("スナップショットは削除されません"), expect.objectContaining({ kind: "warning" }));
      expect(sentArgs().some((args) => args[0] === "tag" && args.includes("--delete"))).toBe(false);

      mocks.confirm.mockResolvedValueOnce(true);
      mockEdit({ name: "提出版", deleted: true }, {});
      await user.click(tagRegion().getByRole("button", { name: "タグ「提出版」を削除" }));
      expect(await screen.findByText("タグ 提出版 を削除しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["tag", "--delete", "提出版"]);
      expect(tagRegion().getByText("タグはありません")).toBeTruthy();
    });

    const deletion = (dryRun: boolean): CommitDeletion => ({
      dry_run: dryRun,
      commit: { id, created_at: commitEntry.created_at, message: "Initial design" },
      parent_id: null,
      moved_branches: [{ id: "main", name: "main", current: true }],
      moved_current: true,
      reconnected_children: [],
      rebased_buds: [],
      reclaimable_objects: ["f".repeat(64)],
      reclaimable_bytes: 12,
    });

    it("deletes a snapshot only after confirming its previewed effects", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      const deleteButton = () => screen.getByRole("button", { name: "この葉を削除" });

      mocks.runSprout.mockResolvedValueOnce(deletion(true));
      mocks.confirm.mockResolvedValueOnce(false);
      await user.click(deleteButton());
      await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
      const [message, options] = mocks.confirm.mock.calls[0];
      expect(message).toContain("Initial design");
      expect(message).toContain("ブランチ main はコミットなしへ移ります");
      expect(message).toContain("作業ファイルは変わらず、未保存の変更として残ります");
      expect(message).toContain("sprout gc");
      expect(options).toEqual(expect.objectContaining({ kind: "warning", okLabel: "削除" }));
      expect(sentArgs()).toContainEqual(["delete-commit", id, "--dry-run"]);
      expect(sentArgs().some((args) => args.includes("--yes"))).toBe(false);
      expect(screen.getByRole("region", { name: "選択中のスナップショット" })).toBeTruthy();

      mocks.runSprout.mockResolvedValueOnce(deletion(true)).mockResolvedValueOnce(deletion(false));
      mockWorkspace({ ...cleanStatus, current_commit: null }, [], [{ ...mainBranch[0], commit_id: null }], {
        current_commit: null, at_branch_tip: true, commits: [], tags: [], buds: [],
        branches: [{ ...mainBranch[0], commit_id: null }],
      });
      await user.click(deleteButton());
      expect(await screen.findByText(`スナップショット ${id.slice(0, 12)} を削除しました`)).toBeTruthy();
      expect(sentArgs()).toContainEqual(["delete-commit", id, "--yes"]);
      expect(screen.queryByRole("region", { name: "選択中のスナップショット" })).toBeNull();
    });

    it("reports a failed confirmation without deleting and allows retrying", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      mocks.runSprout.mockResolvedValueOnce(deletion(true));
      mocks.confirm.mockRejectedValueOnce("dialog.message not allowed");

      await user.click(screen.getByRole("button", { name: "この葉を削除" }));
      expect(await screen.findByText("dialog.message not allowed")).toBeTruthy();
      expect(sentArgs().some((args) => args.includes("--yes"))).toBe(false);
      expect(screen.getByRole("region", { name: "選択中のスナップショット" })).toBeTruthy();

      mocks.runSprout.mockResolvedValueOnce(deletion(true));
      mocks.confirm.mockResolvedValueOnce(false);
      await user.click(screen.getByRole("button", { name: "この葉を削除" }));
      await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(2));
      expect(sentArgs().some((args) => args.includes("--yes"))).toBe(false);
    });

    it("reports a refused deletion preview without asking", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      mocks.runSprout.mockRejectedValueOnce({ code: "tagged_commit", message: "commit is tagged", details: {} });
      await user.click(screen.getByRole("button", { name: "この葉を削除" }));
      expect(await screen.findByText("commit is tagged")).toBeTruthy();
      expect(mocks.confirm).not.toHaveBeenCalled();
      expect(sentArgs().some((args) => args.includes("--yes"))).toBe(false);
    });

    it("disables deleting a tagged snapshot and says why", async () => {
      const user = userEvent.setup();
      await openDetail(user);
      const tag = { name: "提出版", commit_id: id, comment: "", created_at: "2026-10-29T00:00:00+00:00" };
      const tagRegion = within(screen.getByRole("region", { name: "タグ" }));
      await user.type(tagRegion.getByRole("textbox", { name: "新しいタグの名前" }), "提出版");
      mockEdit(tag, {}, [tag]);
      await user.click(tagRegion.getByRole("button", { name: "タグを付ける" }));
      await screen.findByText("タグ 提出版 を付けました");

      const deleteButton = screen.getByRole("button", { name: "この葉を削除" });
      expect(deleteButton.hasAttribute("disabled")).toBe(true);
      expect(deleteButton.getAttribute("title")).toContain("タグ付きの葉は削除できません");
    });
  });

  describe("branch panel", () => {
    const rootId = "d".repeat(64);
    const tipId = "e".repeat(64);
    const branchGraph = (side: Partial<BranchInfo> | null): CommitGraph => ({
      current_commit: tipId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: rootId, branch_id: "main-id", branch_name: "main", message: "Main tip", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "side-id", branch_name: "side", message: "Side root", attachments: [] },
      ],
      branches: [
        { id: "main-id", name: "main", commit_id: tipId, comment: "", current: true },
        ...(side ? [{ id: "side-id", name: "side", commit_id: rootId, comment: "別案", current: false, ...side }] : []),
      ],
      tags: [],
      buds: [],
    });
    const status = { ...cleanStatus, branch_id: "main-id", current_commit: tipId };
    const sentArgs = () => mocks.runSprout.mock.calls.map((call) => call[1]);

    async function openMap(user: ReturnType<typeof userEvent.setup>) {
      render(<App />);
      mocks.open.mockResolvedValueOnce(project);
      const graph = branchGraph({});
      mockWorkspace(status, [], graph.branches, graph);
      await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
      await screen.findByRole("heading", { name: "sprout-project" });
    }

    it("renames and comments on a branch chosen from the map and keeps it selected by ID", async () => {
      const user = userEvent.setup();
      await openMap(user);
      await user.click(screen.getByRole("button", { name: "ブランチ side" }));
      const panel = within(screen.getByRole("region", { name: "選択中のブランチ" }));
      expect(panel.getByRole("heading", { name: "side" })).toBeTruthy();
      expect(panel.getByText("別案")).toBeTruthy();
      expect(panel.getByRole("button", { name: `Side root（${rootId.slice(0, 12)}）` })).toBeTruthy();

      await user.click(panel.getByRole("button", { name: "名前を変更" }));
      const nameInput = panel.getByRole("textbox", { name: "新しい名前" });
      await user.clear(nameInput);
      await user.type(nameInput, "main");
      mocks.runSprout.mockRejectedValueOnce({ code: "sprout_error", message: "branch already exists: main", details: {} });
      await user.click(panel.getByRole("button", { name: "名前を変更" }));
      expect(await screen.findByText("branch already exists: main")).toBeTruthy();
      expect((panel.getByRole("textbox", { name: "新しい名前" }) as HTMLInputElement).value).toBe("main");

      await user.clear(panel.getByRole("textbox", { name: "新しい名前" }));
      await user.type(panel.getByRole("textbox", { name: "新しい名前" }), "idea");
      mocks.runSprout.mockResolvedValueOnce({ id: "side-id", name: "idea", previous_name: "side" });
      let graph = branchGraph({ name: "idea" });
      mockWorkspace(status, [], graph.branches, graph);
      await user.click(panel.getByRole("button", { name: "名前を変更" }));
      expect(await screen.findByText("ブランチ side の名前を idea に変更しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["branch", "side", "--rename", "idea"]);
      const renamed = within(screen.getByRole("region", { name: "選択中のブランチ" }));
      expect(renamed.getByRole("heading", { name: "idea" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "ブランチ idea" }).getAttribute("aria-pressed")).toBe("true");

      await user.click(renamed.getByRole("button", { name: "コメントを編集" }));
      await user.clear(renamed.getByRole("textbox", { name: "ブランチのコメントを編集" }));
      mocks.runSprout.mockResolvedValueOnce({ id: "side-id", name: "idea", comment: "" });
      graph = branchGraph({ name: "idea", comment: "" });
      mockWorkspace(status, [], graph.branches, graph);
      await user.click(renamed.getByRole("button", { name: "保存" }));
      expect(await screen.findByText("ブランチ idea のコメントを変更しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["branch", "idea", "--set-comment", ""]);
      expect(renamed.getByText("コメントはありません")).toBeTruthy();

      mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, id: rootId, branch_id: "side-id", branch_name: "side", message: "Side root", thumbnail: null, attachments: [], files: [] });
      await user.click(renamed.getByRole("button", { name: `Side root（${rootId.slice(0, 12)}）` }));
      expect(await screen.findByText("idea（作成時: side）", { selector: "dd" })).toBeTruthy();
    });

    it("protects the current branch and deletes another after confirmation", async () => {
      const user = userEvent.setup();
      await openMap(user);
      await user.click(screen.getByRole("button", { name: "現在のブランチ" }));
      const current = within(screen.getByRole("region", { name: "選択中のブランチ" }));
      expect(current.getByText("現在のブランチ")).toBeTruthy();
      expect(current.getByRole("button", { name: "ブランチを削除" }).hasAttribute("disabled")).toBe(true);
      expect(current.getByText(/現在のブランチは削除できません/)).toBeTruthy();

      await user.click(screen.getByRole("button", { name: "ブランチ side" }));
      mocks.confirm.mockResolvedValueOnce(false);
      await user.click(screen.getByRole("button", { name: "ブランチを削除" }));
      expect(mocks.confirm).toHaveBeenCalledWith(expect.stringContaining("「削除済みブランチ由来」として残ります"), expect.objectContaining({ kind: "warning" }));
      expect(sentArgs().some((args) => args.includes("--delete"))).toBe(false);

      mocks.confirm.mockResolvedValueOnce(true);
      mocks.runSprout.mockResolvedValueOnce({ id: "side-id", name: "side", deleted: true });
      const graph = branchGraph(null);
      mockWorkspace(status, [], graph.branches, graph);
      await user.click(screen.getByRole("button", { name: "ブランチを削除" }));
      expect(await screen.findByText("ブランチ side を削除しました")).toBeTruthy();
      expect(sentArgs()).toContainEqual(["branch", "--delete", "side"]);
      expect(screen.queryByRole("region", { name: "選択中のブランチ" })).toBeNull();
      expect(screen.getByText("削除済みブランチ由来: side")).toBeTruthy();
    });
  });

  it("selects branch names hanging below a stem by click and keyboard", async () => {
    const user = userEvent.setup();
    const rootId = "d".repeat(64);
    const midId = "e".repeat(64);
    const tipId = "f".repeat(64);
    const graph: CommitGraph = {
      current_commit: midId,
      at_branch_tip: true,
      commits: [
        { ...commitEntry, id: tipId, parent_id: midId, branch_id: "main-id", branch_name: "main", message: "Top", attachments: [] },
        { ...commitEntry, id: midId, parent_id: rootId, branch_id: "main-id", branch_name: "main", message: "Middle", attachments: [] },
        { ...commitEntry, id: rootId, parent_id: null, branch_id: "main-id", branch_name: "main", message: "Root", attachments: [] },
      ],
      branches: [
        { id: "main-id", name: "main", commit_id: tipId, comment: "", current: false },
        { id: "fork-id", name: "分岐2", commit_id: midId, comment: "", current: true },
        { id: "copy-id", name: "copy", commit_id: midId, comment: "", current: false },
      ],
      tags: [],
      buds: [],
    };
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace({ ...cleanStatus, branch: "分岐2", branch_id: "fork-id", current_commit: midId }, [], graph.branches, graph);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });

    const fork = screen.getByRole("button", { name: "ブランチ 分岐2" });
    expect(fork.closest(".branch-label")?.classList.contains("below")).toBe(true);
    expect(fork.textContent).toBe("分岐2（現在のブランチ）");
    expect(screen.getByRole("button", { name: "ブランチ main" }).closest(".branch-label")?.classList.contains("end")).toBe(true);

    await user.click(fork);
    expect(within(screen.getByRole("region", { name: "選択中のブランチ" })).getByRole("heading", { name: "分岐2" })).toBeTruthy();
    screen.getByRole("button", { name: "ブランチ copy" }).focus();
    await user.keyboard("{Enter}");
    expect(within(screen.getByRole("region", { name: "選択中のブランチ" })).getByRole("heading", { name: "copy" })).toBeTruthy();
  });
  it("selects comparison snapshots from the map without moving the working tree", async () => {
    const user = userEvent.setup();
    render(<App />);
    mocks.open.mockResolvedValueOnce(project);
    mockWorkspace(cleanStatus, [commitEntry, { ...commitEntry, id: "b".repeat(64), message: "Second design" }]);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    await screen.findByRole("heading", { name: "sprout-project" });
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", files: [], attachments: [], thumbnail: null });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await user.click(await screen.findByRole("button", { name: "比較元にする" }));
    await user.click(screen.getByRole("button", { name: "Second design" }));
    mocks.runSprout.mockResolvedValueOnce([]);
    await user.click(screen.getByRole("button", { name: "比較する" }));
    await screen.findByText("差分はありません");
    expect(mocks.runSprout).toHaveBeenLastCalledWith(project, ["diff", commitEntry.id, "b".repeat(64)], "");
    expect(mocks.runSprout.mock.calls.map((call) => call[1][0])).toEqual(["status", "tree", "show", "diff"]);
  });

  async function openSavedFiles(user: ReturnType<typeof userEvent.setup>) {
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce({ ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [
      { path: "assets/a.bin", size: 123, object_hash: "a", mtime_ns: 0 },
      { path: "assets/sub/b.bin", size: 456, object_hash: "b", mtime_ns: 0 },
      { path: "other.bin", size: 789, object_hash: "c", mtime_ns: 0 },
    ] });
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await screen.findByRole("region", { name: "保存済みファイル" });
  }

  it("exports only selected directory files without force or workspace mutation", async () => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    expect(screen.getByText("123 B")).toBeTruthy();
    await user.click(screen.getByRole("checkbox", { name: "assets/ 配下を選択" }));
    mocks.open.mockResolvedValueOnce("C:\\export");
    mocks.runSprout.mockResolvedValueOnce({ paths: ["assets/a.bin", "assets/sub/b.bin"], output: "C:\\export" });
    await user.click(screen.getByRole("button", { name: "選択したファイルを取り出す" }));
    await screen.findByText(/2件のファイルを.*へ書き出しました/);
    expect(mocks.runSprout).toHaveBeenLastCalledWith(project, ["export", commitEntry.id, "assets/a.bin", "assets/sub/b.bin", "--output", "C:\\export"], "");
    expect(mocks.runSprout.mock.calls.map((call) => call[1][0])).toEqual(["status", "tree", "show", "export"]);
  });

  it("restores one file and refreshes changes without moving snapshot references", async () => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    await user.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
    mocks.runSprout.mockResolvedValueOnce({ commit_id: commitEntry.id, paths: ["assets/a.bin"] });
    mockWorkspace({ ...cleanStatus, changes: [{ state: "modified", path: "assets/a.bin" }] });
    await user.click(screen.getByRole("button", { name: "選択したファイルだけ戻す" }));
    await screen.findByText("1件のファイルを戻しました");
    expect(mocks.confirm.mock.calls[0][0]).toContain("assets/a.bin");
    expect(mocks.confirm.mock.calls[0][0]).toContain("選択外のファイル・現在位置・ブランチ先端は変わりません");
    expect(mocks.runSprout.mock.calls.map((call) => call[1])).toEqual([
      ["status", "--tracked", "--untracked"], ["tree"], ["show", commitEntry.id],
      ["restore", commitEntry.id, "assets/a.bin"], ["status", "--tracked", "--untracked"], ["tree"],
    ]);
    expect(screen.getByLabelText("保存状態").textContent).toBe("未保存の変更 1");
  });

  it.each(["export", "restore"])("cancels %s before any CLI write", async (operation) => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    await user.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
    if (operation === "export") mocks.open.mockResolvedValueOnce(null);
    else mocks.confirm.mockResolvedValueOnce(false);
    await user.click(screen.getByRole("button", { name: operation === "export" ? "選択したファイルを取り出す" : "選択したファイルだけ戻す" }));
    await waitFor(() => expect((screen.getByRole("button", { name: "保存" }) as HTMLButtonElement).disabled).toBe(false));
    expect(mocks.runSprout.mock.calls.map((call) => call[1][0])).toEqual(["status", "tree", "show"]);
  });

  it.each([false, true])("retries with discard only after explicit approval: %s", async (accepted) => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    await user.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
    mocks.confirm.mockResolvedValueOnce(true).mockResolvedValueOnce(accepted);
    mocks.runSprout.mockRejectedValueOnce({ code: "uncommitted_changes", message: "Unsaved", details: { can_discard: true } });
    if (accepted) {
      mocks.runSprout.mockResolvedValueOnce({ commit_id: commitEntry.id, paths: ["assets/a.bin"] });
      mockWorkspace();
    }
    await user.click(screen.getByRole("button", { name: "選択したファイルだけ戻す" }));
    await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(2));
    await waitFor(() => expect((screen.getByRole("button", { name: "保存" }) as HTMLButtonElement).disabled).toBe(false));
    const calls = mocks.runSprout.mock.calls.filter((call) => call[1][0] === "restore");
    expect(calls.map((call) => call[1])).toEqual(accepted
      ? [["restore", commitEntry.id, "assets/a.bin"], ["restore", commitEntry.id, "assets/a.bin", "--discard"]]
      : [["restore", commitEntry.id, "assets/a.bin"]]);
  });

  it.each(["unsafe_restore_path", "untracked_conflict", "restore_path_conflict"])("shows %s without bypassing safety", async (code) => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    await user.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
    mocks.runSprout.mockRejectedValueOnce({ code, message: "Cannot restore", details: { path: "assets/a.bin" } });
    await user.click(screen.getByRole("button", { name: "選択したファイルだけ戻す" }));
    expect(await screen.findByText(/Cannot restore/)).toBeTruthy();
    expect(screen.getByText("対象: assets/a.bin")).toBeTruthy();
    expect(mocks.confirm).toHaveBeenCalledTimes(1);
    expect(mocks.runSprout.mock.calls.filter((call) => call[1][0] === "restore")).toHaveLength(1);
  });

  it("reports an export collision without forcing overwrite", async () => {
    const user = userEvent.setup();
    await openSavedFiles(user);
    await user.click(screen.getByRole("checkbox", { name: /assets\/a.bin/ }));
    mocks.open.mockResolvedValueOnce("C:\\export");
    mocks.runSprout.mockRejectedValueOnce({ code: "output_exists", message: "Already exists", details: { path: "assets/a.bin" } });
    await user.click(screen.getByRole("button", { name: "選択したファイルを取り出す" }));
    await screen.findByText("Already exists");
    expect(mocks.runSprout.mock.calls.filter((call) => call[1][0] === "export")).toHaveLength(1);
    expect(mocks.runSprout.mock.lastCall?.[1]).not.toContain("--force");
  });

  const previewDetail = {
    ...commitEntry, branch_id: "main", branch_name: "main", files: [], thumbnail: null,
    attachments: [
      { id: "p1", role: "preview", position: 0, original_name: "voice.wav", media_type: "audio/wav", size: 12 },
      { id: "p2", role: "preview", position: 1, original_name: "model.stl", media_type: "application/octet-stream", size: 24 },
    ],
  };
  const smallPreviewPlan = { previews: [{ original_name: "new.bin", size: 12 }], additional_bytes: 12, requires_confirmation: false };
  async function openPreviewWorkspace(user: ReturnType<typeof userEvent.setup>) {
    render(<App />);
    await openWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce(previewDetail);
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await screen.findByRole("region", { name: "プレビュー管理" });
  }
  function previewRefresh() {
    mockWorkspace();
    mocks.runSprout.mockResolvedValueOnce(previewDetail);
  }

  it("edits preview metadata and materials, retains refused input and shows the representative", async () => {
    const user = userEvent.setup();
    render(<App />);
    await openWorkspace(user);
    const detail = { ...previewDetail, files: [{ path: "scene.blend", file_id: "asset-1", size: 4, mtime_ns: 0, object_hash: "hash" }] };
    mocks.runSprout.mockResolvedValueOnce(detail);
    await user.click(screen.getByRole("button", { name: "Initial design" }));
    await screen.findByRole("region", { name: "プレビュー管理" });
    await user.click(screen.getAllByText("表示名・説明・対象素材を編集")[0]);
    const form = screen.getByRole("form", { name: "voice.wavのメタ情報" });
    await user.type(within(form).getByLabelText("表示名"), "Review");
    await user.type(within(form).getByLabelText("説明"), "Notes");
    await user.click(within(form).getByRole("checkbox", { name: "このコミットの代表プレビュー" }));
    await user.click(within(form).getByRole("checkbox", { name: "scene.blend" }));
    mocks.runSprout.mockRejectedValueOnce({ code: "invalid_preview_material", message: "material changed", details: {} });
    await user.click(within(form).getByRole("button", { name: "メタ情報を保存" }));
    expect((await screen.findByRole("alert")).textContent).toContain("material changed");
    expect((within(form).getByLabelText("表示名") as HTMLInputElement).value).toBe("Review");
    const metadata = { display_name: "Review", description: "Notes", is_primary: true, file_ids: ["asset-1"] };
    mocks.runSprout.mockResolvedValueOnce(metadata);
    mockWorkspace();
    mocks.runSprout.mockResolvedValueOnce({ ...detail, attachments: [{ ...detail.attachments[0], ...metadata, updated_at: "changed" }, detail.attachments[1]] });
    await user.click(within(form).getByRole("button", { name: "メタ情報を保存" }));
    expect(await screen.findByText("代表")).toBeTruthy();
    expect(screen.getByText("対象素材: scene.blend")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["preview", "metadata", commitEntry.id, "p1", "--name=Review", "--description=Notes", "--primary", "--file-id", "asset-1"], "");
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "preview" && call[1][1] === "image")).toBe(false);
  });

  it.each([false, true])("confirms a large preview before registration: %s", async (accepted) => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.open.mockResolvedValueOnce(["C:\\movie.mp4"]);
    mocks.runSprout.mockResolvedValueOnce({ ...smallPreviewPlan, requires_confirmation: true, additional_bytes: 200000000, previews: [{ original_name: "movie.mp4", size: 200000000 }] });
    mocks.confirm.mockResolvedValueOnce(accepted);
    if (accepted) { mocks.runSprout.mockResolvedValueOnce([]); previewRefresh(); }
    await user.click(screen.getByRole("button", { name: "プレビューを追加" }));
    await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
    await waitFor(() => expect((screen.getByRole("button", { name: "保存" }) as HTMLButtonElement).disabled).toBe(false));
    expect(mocks.confirm.mock.calls[0][0]).toContain("200,000,000");
    const calls = mocks.runSprout.mock.calls.filter((call) => call[1][0] === "preview").map((call) => call[1]);
    expect(calls).toEqual(accepted ? [
      ["preview", "add", commitEntry.id, "C:\\movie.mp4", "--dry-run"],
      ["preview", "add", commitEntry.id, "C:\\movie.mp4", "--yes"],
    ] : [["preview", "add", commitEntry.id, "C:\\movie.mp4", "--dry-run"]]);
  });

  it("adds multiple preview files from a native drop instead of tracking them", async () => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.runSprout.mockResolvedValueOnce(smallPreviewPlan).mockResolvedValueOnce([]);
    previewRefresh();
    act(() => mocks.dragHandler?.({ payload: { type: "drop", paths: ["C:\\one.wav", "C:\\two.bin"] } }));
    await screen.findByText("プレビューの操作が完了しました");
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["preview", "add", commitEntry.id, "C:\\one.wav", "C:\\two.bin"], "");
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "track")).toBe(false);
  });

  it.each(["replace", "delete", "order"])("uses stable attachment IDs for preview %s", async (action) => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    if (action === "replace") {
      mocks.open.mockResolvedValueOnce("C:\\new.wav");
      mocks.runSprout.mockResolvedValueOnce(smallPreviewPlan);
    }
    mocks.runSprout.mockResolvedValueOnce([]);
    previewRefresh();
    const name = action === "replace" ? "voice.wavを置き換え" : action === "delete" ? "voice.wavを削除" : "voice.wavを下へ";
    await user.click(screen.getByRole("button", { name }));
    await screen.findByText("プレビューの操作が完了しました");
    expect(mocks.runSprout).toHaveBeenCalledWith(project, action === "replace"
      ? ["preview", "replace", commitEntry.id, "p1", "C:\\new.wav"]
      : action === "delete" ? ["preview", "delete", commitEntry.id, "p1"] : ["preview", "order", commitEntry.id, "p2", "p1"], "");
  });

  it("exports a preview to a chosen file without force", async () => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.save.mockResolvedValueOnce("C:\\out.wav");
    mocks.runSprout.mockResolvedValueOnce({ output: "C:\\out.wav" });
    await user.click(screen.getByRole("button", { name: "voice.wavを取り出す" }));
    await screen.findByText(/プレビューを.*へ取り出しました/);
    expect(mocks.runSprout).toHaveBeenLastCalledWith(project, ["preview", "export", commitEntry.id, "p1", "--output", "C:\\out.wav"], "");
  });

  it("preserves the displayed preview order on failure", async () => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.runSprout.mockRejectedValueOnce({ code: "repository_locked", message: "Preview locked", details: {} });
    await user.click(screen.getByRole("button", { name: "voice.wavを下へ" }));
    await screen.findByText("Preview locked");
    const list = within(screen.getByRole("region", { name: "プレビュー管理" })).getByRole("list");
    expect(within(list).getAllByRole("listitem")[0].textContent).toContain("voice.wav");
    expect(mocks.runSprout.mock.calls.filter((call) => call[1][0] === "preview")).toHaveLength(1);
  });

  it.each([false, true])("pastes arbitrary preview files and cleans up after failure=%s", async (failure) => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.invoke.mockImplementation(async (command: string) => command === "save_pasted_preview" ? "C:\\temp\\voice.wav" : undefined);
    mocks.runSprout.mockResolvedValueOnce(smallPreviewPlan);
    if (failure) mocks.runSprout.mockRejectedValueOnce({ code: "preview_error", message: "Cannot add", details: {} });
    else { mocks.runSprout.mockResolvedValueOnce([]); previewRefresh(); }
    fireEvent.paste(screen.getByRole("group", { name: "プレビュー貼り付け領域" }), { clipboardData: clipboardData(new File(["voice"], "voice.wav", { type: "audio/wav" })) });
    await waitFor(() => expect(mocks.invoke).toHaveBeenCalledWith("discard_pasted_thumbnail", { path: "C:\\temp\\voice.wav" }));
    expect(mocks.invoke).toHaveBeenCalledWith("save_pasted_preview", { name: "voice.wav", data: "dm9pY2U=" });
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "thumbnail")).toBe(false);
    if (failure) await screen.findByText("Cannot add");
  });

  it("pastes an image as a preview only inside the dedicated area", async () => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.invoke.mockImplementation(async (command: string) => command === "save_pasted_preview" ? "C:\\temp\\image.png" : undefined);
    mocks.runSprout.mockResolvedValueOnce(smallPreviewPlan).mockResolvedValueOnce([]);
    previewRefresh();
    fireEvent.paste(screen.getByRole("group", { name: "プレビュー貼り付け領域" }), { clipboardData: clipboardData(new File(["image"], "image.png", { type: "image/png" })) });
    await screen.findByText("プレビューの操作が完了しました");
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["preview", "add", commitEntry.id, "C:\\temp\\image.png"], "");
    expect(mocks.runSprout.mock.calls.some((call) => call[1][0] === "thumbnail")).toBe(false);
  });

  it("adds native Explorer clipboard paths when WebView files are absent", async () => {
    const user = userEvent.setup();
    await openPreviewWorkspace(user);
    mocks.invoke.mockImplementation(async (command: string) => command === "read_clipboard_files" ? ["C:\\source.pdf"] : undefined);
    mocks.runSprout.mockResolvedValueOnce(smallPreviewPlan).mockResolvedValueOnce([]);
    previewRefresh();
    fireEvent.paste(screen.getByRole("group", { name: "プレビュー貼り付け領域" }), { clipboardData: clipboardData(null) });
    await screen.findByText("プレビューの操作が完了しました");
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["preview", "add", commitEntry.id, "C:\\source.pdf"], "");
  });

  describe("refresh when the window regains focus", () => {
    const changedStatus = { ...cleanStatus, changes: [{ state: "modified", path: "design/main.psd" }] };
    const focus = (focused = true) => act(async () => mocks.focusHandler?.({ payload: focused }));
    const statusCalls = () => mocks.runSprout.mock.calls.filter((call) => call[1][0] === "status").length;
    const saveState = () => screen.getByLabelText("保存状態").textContent;
    const secondEntry = { ...commitEntry, id: "b".repeat(64), parent_id: commitEntry.id, message: "External snapshot" };

    function deferred<T>() {
      let resolve: (value: T) => void = () => undefined;
      let reject: (reason: unknown) => void = () => undefined;
      const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
      return { promise, resolve, reject };
    }

    async function openFocusWorkspace(user: ReturnType<typeof userEvent.setup>) {
      render(<App />);
      await openWorkspace(user);
      await waitFor(() => expect(mocks.focusHandler).toBeTypeOf("function"));
    }

    async function showNotice(user: ReturnType<typeof userEvent.setup>) {
      mocks.runSprout.mockRejectedValueOnce({ code: "sprout_error", message: "Earlier failure", details: {} });
      await user.click(screen.getByRole("button", { name: "更新" }));
      expect(await screen.findByText("Earlier failure")).toBeTruthy();
    }

    it("updates changes, tracking, the top bar and the map on focus, and ignores blur", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      const calls = statusCalls();
      await focus(false);
      expect(statusCalls()).toBe(calls);

      mockWorkspace({ ...changedStatus, tracked: ["design/main.psd", "new.txt"], untracked: [] }, [secondEntry, commitEntry]);
      await focus();

      await waitFor(() => expect(saveState()).toBe("未保存の変更 1"));
      expect(screen.getByRole("heading", { name: "未保存の変更 1件" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "External snapshot" })).toBeTruthy();
      await user.click(screen.getByRole("button", { name: "ファイル" }));
      expect(screen.getByText("追跡中（2件）")).toBeTruthy();
    });

    it("does not refetch or interrupt while an operation runs", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      const commit = deferred<unknown>();
      await user.type(screen.getByLabelText("メッセージ"), "Save design");
      mocks.runSprout.mockReturnValueOnce(commit.promise);
      await user.click(screen.getByRole("button", { name: "保存して葉にする" }));
      const calls = mocks.runSprout.mock.calls.length;

      await focus();
      expect(mocks.runSprout).toHaveBeenCalledTimes(calls);

      mockWorkspace(cleanStatus, [secondEntry, commitEntry]);
      await act(async () => commit.resolve({ id: secondEntry.id, branch: "main", branch_id: "main", created_branch: false, message: "Save design", removed_paths: [] }));
      expect(await screen.findByText(/を作成しました/)).toBeTruthy();
      expect(mocks.runSprout).toHaveBeenCalledTimes(calls + 2);
    });

    it("throttles rapid focus changes and refetches once afterwards", async () => {
      const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"], shouldAdvanceTime: true });
      await openFocusWorkspace(user);
      const calls = statusCalls();
      mockWorkspace(changedStatus);
      await focus();
      await waitFor(() => expect(saveState()).toBe("未保存の変更 1"));
      for (let index = 0; index < 5; index += 1) {
        await focus(false);
        await focus();
      }
      expect(statusCalls()).toBe(calls + 1);

      mockWorkspace();
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });

      expect(statusCalls()).toBe(calls + 2);
      await waitFor(() => expect(saveState()).toBe("保存済み"));
      await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
      expect(statusCalls()).toBe(calls + 2);
    });

    it("keeps the notice, enabled buttons and drafts while refetching", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      await showNotice(user);
      await user.type(screen.getByLabelText("メッセージ"), "Half written");
      const pending = deferred<SproutStatus>();
      mocks.runSprout.mockReturnValueOnce(pending.promise);
      mocks.runSprout.mockResolvedValueOnce({ current_commit: commitEntry.id, at_branch_tip: true, commits: [{ ...commitEntry, branch_id: "main", branch_name: "main", attachments: [] }], branches: mainBranch, tags: [], buds: [] });

      await focus();

      expect(screen.queryByLabelText("操作中")).toBeNull();
      expect((screen.getByRole("button", { name: "更新" }) as HTMLButtonElement).disabled).toBe(false);
      expect((screen.getByLabelText("メッセージ") as HTMLTextAreaElement).disabled).toBe(false);
      await act(async () => pending.resolve(changedStatus));

      await waitFor(() => expect(saveState()).toBe("未保存の変更 1"));
      expect((screen.getByLabelText("メッセージ") as HTMLTextAreaElement).value).toBe("Half written");
      expect(screen.getByText("Earlier failure")).toBeTruthy();
    });

    it("keeps the selected leaf and a memo draft without reloading the detail", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      const detail = { ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] };
      mocks.runSprout.mockResolvedValueOnce(detail);
      await user.click(screen.getByRole("button", { name: "Initial design" }));
      await user.click(await screen.findByRole("button", { name: "メモを書く" }));
      await user.type(screen.getByRole("textbox", { name: "メモを編集" }), "Draft memo");
      mocks.runSprout.mockClear();
      mockWorkspace(changedStatus);

      await focus();

      await waitFor(() => expect(saveState()).toBe("未保存の変更 1"));
      expect(mocks.runSprout.mock.calls.map((call) => call[1][0])).toEqual(["status", "tree"]);
      expect(screen.getByRole("region", { name: "選択中のスナップショット" })).toBeTruthy();
      expect((screen.getByRole("textbox", { name: "メモを編集" }) as HTMLTextAreaElement).value).toBe("Draft memo");
    });

    it("clears the selection when the selected leaf disappeared", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      const detail = { ...commitEntry, branch_id: "main", branch_name: "main", thumbnail: null, attachments: [], files: [] };
      mocks.runSprout.mockResolvedValueOnce(detail);
      await user.click(screen.getByRole("button", { name: "Initial design" }));
      await screen.findByRole("region", { name: "選択中のスナップショット" });
      mockWorkspace(cleanStatus, []);

      await focus();

      await waitFor(() => expect(screen.queryByRole("region", { name: "選択中のスナップショット" })).toBeNull());
      expect(screen.getByRole("region", { name: "未保存の変更" })).toBeTruthy();
    });

    it("drops a late result when an operation started during the refetch", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      const stale = deferred<SproutStatus>();
      mocks.runSprout.mockReturnValueOnce(stale.promise);
      await focus();
      mockWorkspace({ ...cleanStatus, changes: [{ state: "added", path: "a.txt" }, { state: "added", path: "b.txt" }] });
      await user.click(screen.getByRole("button", { name: "更新" }));
      await waitFor(() => expect(saveState()).toBe("未保存の変更 2"));

      mockWorkspace(changedStatus);
      mocks.runSprout.mockReset();
      mocks.runSprout.mockResolvedValueOnce({ current_commit: commitEntry.id, at_branch_tip: true, commits: [], branches: mainBranch, tags: [], buds: [] });
      await act(async () => stale.resolve(changedStatus));
      await act(async () => undefined);

      expect(saveState()).toBe("未保存の変更 2");
    });

    it("warns once about repeated failures, does not block operations, and clears after success", async () => {
      const user = userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) });
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"], shouldAdvanceTime: true });
      await openFocusWorkspace(user);
      const locked = { code: "repository_locked", message: "another Sprout operation is already running", details: { retryable: true } };

      mocks.runSprout.mockRejectedValueOnce(locked);
      await focus();
      expect(await screen.findByText(/最新の状態を取得できませんでした/)).toBeTruthy();
      await user.click(screen.getByRole("button", { name: "通知を閉じる" }));

      mocks.runSprout.mockRejectedValueOnce(locked);
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
      await focus();
      await act(async () => undefined);
      expect(screen.queryByRole("alert")).toBeNull();
      expect((screen.getByRole("button", { name: "更新" }) as HTMLButtonElement).disabled).toBe(false);

      mockWorkspace(changedStatus);
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
      await focus();
      await waitFor(() => expect(saveState()).toBe("未保存の変更 1"));

      mocks.runSprout.mockRejectedValueOnce(locked);
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
      await focus();
      expect(await screen.findByText(/最新の状態を取得できませんでした/)).toBeTruthy();
      mockWorkspace();
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });
      await focus();
      await waitFor(() => expect(screen.queryByText(/最新の状態を取得できませんでした/)).toBeNull());
    });

    it("does not replace a notice the user is reading when the refetch fails", async () => {
      const user = userEvent.setup();
      await openFocusWorkspace(user);
      await showNotice(user);
      mocks.runSprout.mockRejectedValueOnce({ code: "repository_locked", message: "locked", details: {} });

      await focus();
      await act(async () => undefined);

      expect(screen.getByText("Earlier failure")).toBeTruthy();
      expect(screen.queryByText(/最新の状態を取得できませんでした/)).toBeNull();
    });

    it("does not refetch before a workspace is open", async () => {
      render(<App />);
      await waitFor(() => expect(mocks.focusHandler).toBeTypeOf("function"));
      await focus();
      expect(mocks.runSprout).not.toHaveBeenCalled();
    });
  });

  describe("drops and pastes follow the displayed panel", () => {
    const pngImage = () => new File([new Uint8Array([1, 2, 3])], "image.png", { type: "image/png" });
    const thumbnail = {
      id: "t1", position: 0, commit_id: commitEntry.id, role: "thumbnail" as const, original_name: "old.png", media_type: "image/png",
      object_hash: "f".repeat(64), size: 3, created_at: commitEntry.created_at, updated_at: commitEntry.created_at,
    };
    const leafChanges = () => mocks.runSprout.mock.calls.filter((call) => ["preview", "thumbnail", "track"].includes(call[1][0]));
    const drag = (payload: { type: string; paths: string[] }) => act(() => mocks.dragHandler?.({ payload }));

    /** Open a leaf detail, then show the named panel over it while the leaf stays selected. */
    async function showOverLeaf(user: ReturnType<typeof userEvent.setup>, panel: string) {
      await openPreviewWorkspace(user);
      if (panel === "trash") {
        mocks.runSprout.mockResolvedValueOnce([]);
        await user.click(screen.getByRole("button", { name: "ゴミ箱" }));
        await screen.findByRole("region", { name: "ゴミ箱" });
      }
      if (panel === "compare") {
        await user.click(screen.getByRole("button", { name: "比較元にする" }));
        await screen.findByRole("region", { name: "スナップショットの比較" });
      }
      if (panel === "files") await user.click(screen.getByRole("button", { name: "ファイル" }));
      if (panel === "settings") await user.click(screen.getByRole("button", { name: "設定" }));
      mocks.runSprout.mockClear();
    }

    it.each([
      ["trash", "ゴミ箱を閉じるとドロップできます"],
      ["compare", "比較を閉じるとドロップできます"],
      ["settings", "CLI設定を閉じるとドロップできます"],
    ])("adds nothing when files are dropped while %s is displayed", async (panel, message) => {
      const user = userEvent.setup();
      await showOverLeaf(user, panel);

      drag({ type: "enter", paths: ["C:\\one.wav"] });
      expect(screen.getByRole("status").textContent).toBe(message);
      drag({ type: "drop", paths: ["C:\\one.wav"] });

      expect(screen.queryByRole("status")).toBeNull();
      expect(await screen.findByText(new RegExp(`ドロップしたファイルは追加していません。${message}`))).toBeTruthy();
      expect(leafChanges()).toEqual([]);
    });

    it("tracks a drop instead of changing the leaf hidden behind the file panel", async () => {
      const user = userEvent.setup();
      await showOverLeaf(user, "files");
      mocks.runSprout.mockResolvedValueOnce({ paths: ["one.wav"] });
      mockWorkspace();

      drag({ type: "enter", paths: ["C:\\one.wav"] });
      expect(screen.getByRole("status").textContent).toBe("作業フォルダの追跡対象に追加します");
      drag({ type: "drop", paths: ["C:\\one.wav"] });

      expect(await screen.findByText("1件を追跡対象に追加しました")).toBeTruthy();
      expect(leafChanges().map((call) => call[1])).toEqual([["track", "C:\\one.wav"]]);
    });

    it("shows the destination leaf while hovering and clears it when the drag leaves", async () => {
      const user = userEvent.setup();
      await openPreviewWorkspace(user);

      drag({ type: "enter", paths: ["C:\\one.wav"] });
      expect(screen.getByRole("status").textContent).toBe(`葉「${commitEntry.message}」（${commitEntry.id.slice(0, 12)}）のプレビューに追加します`);
      drag({ type: "over", paths: [] });
      expect(screen.getByRole("status")).toBeTruthy();
      drag({ type: "leave", paths: [] });

      expect(screen.queryByRole("status")).toBeNull();
      expect(leafChanges()).toEqual([]);
    });

    it("shows the tracking destination while hovering over the save form", async () => {
      const user = userEvent.setup();
      render(<App />);
      await openWorkspace(user);
      await waitFor(() => expect(mocks.dragHandler).toBeTypeOf("function"));

      drag({ type: "enter", paths: ["C:\\one.wav"] });

      expect(screen.getByRole("status").textContent).toBe("作業フォルダの追跡対象に追加します");
    });

    it.each(["trash", "compare", "files", "settings"])("keeps the leaf thumbnail when an image is pasted while %s is displayed", async (panel) => {
      const user = userEvent.setup();
      mockPasteCommands("C:\\temp\\clipboard.png");
      await showOverLeaf(user, panel);

      fireEvent.paste(document.body, { clipboardData: clipboardData(pngImage()) });

      await act(async () => undefined);
      expect(mocks.invoke).not.toHaveBeenCalledWith("save_pasted_thumbnail", expect.anything());
      expect(mocks.confirm).not.toHaveBeenCalled();
      expect(leafChanges()).toEqual([]);
    });

    it.each(["メッセージ", "メモ"])("never changes a thumbnail when an image is pasted into the %s field", async (field) => {
      const user = userEvent.setup();
      mockPasteCommands("C:\\temp\\clipboard.png");
      let target: HTMLElement;
      if (field === "メッセージ") {
        render(<App />);
        await openWorkspace(user);
        target = screen.getByLabelText("メッセージ");
      } else {
        await openPreviewWorkspace(user);
        await user.click(screen.getByRole("button", { name: "メモを書く" }));
        target = screen.getByRole("textbox", { name: "メモを編集" });
      }

      const notPrevented = fireEvent.paste(target, { clipboardData: clipboardData(pngImage()) });

      expect(notPrevented).toBe(true);
      expect(await screen.findByText(/入力欄には画像を貼り付けられません/)).toBeTruthy();
      expect(mocks.invoke).not.toHaveBeenCalledWith("save_pasted_thumbnail", expect.anything());
      expect(screen.queryByText("貼り付けた画像を保存時のサムネイルにします")).toBeNull();
      expect(leafChanges()).toEqual([]);
    });

    it("stays quiet when text with an image is pasted into a text field", async () => {
      const user = userEvent.setup();
      render(<App />);
      await openWorkspace(user);

      const data = { ...clipboardData(pngImage(), "cell text"), getData: () => "cell text" };
      fireEvent.paste(screen.getByLabelText("メッセージ"), { clipboardData: data });

      await act(async () => undefined);
      expect(screen.queryByRole("alert")).toBeNull();
      expect(mocks.invoke).not.toHaveBeenCalledWith("save_pasted_thumbnail", expect.anything());
    });

    it.each([false, true])("confirms replacing an existing thumbnail by paste, accepted=%s", async (accepted) => {
      const user = userEvent.setup();
      mockPasteCommands("C:\\temp\\clipboard.png");
      mocks.confirm.mockResolvedValue(accepted);
      render(<App />);
      await openWorkspace(user);
      const detail = { ...commitEntry, branch_id: "main", branch_name: "main", thumbnail, attachments: [thumbnail], files: [] };
      mocks.runSprout.mockResolvedValueOnce(detail);
      await user.click(screen.getByRole("button", { name: /Initial design/ }));
      await screen.findByRole("button", { name: "サムネイルを変更" });
      if (accepted) {
        mocks.runSprout.mockResolvedValueOnce({});
        mockWorkspace();
        mocks.runSprout.mockResolvedValueOnce(detail);
      }

      fireEvent.paste(document.body, { clipboardData: clipboardData(pngImage()) });

      await waitFor(() => expect(mocks.confirm).toHaveBeenCalledTimes(1));
      expect(mocks.confirm.mock.calls[0][0]).toContain("置き換えます");
      if (accepted) {
        expect(await screen.findByText(/のサムネイルを保存しました/)).toBeTruthy();
        expect(mocks.runSprout).toHaveBeenCalledWith(project, ["thumbnail", commitEntry.id, "C:\\temp\\clipboard.png"], "");
      } else {
        await act(async () => undefined);
        expect(mocks.invoke).not.toHaveBeenCalledWith("save_pasted_thumbnail", expect.anything());
        expect(leafChanges()).toEqual([]);
      }
    });

    it("registers a first thumbnail by paste without asking", async () => {
      const user = userEvent.setup();
      mockPasteCommands("C:\\temp\\clipboard.png");
      await openPreviewWorkspace(user);
      mocks.runSprout.mockResolvedValueOnce({});
      previewRefresh();

      fireEvent.paste(document.body, { clipboardData: clipboardData(pngImage()) });

      expect(await screen.findByText(/のサムネイルを保存しました/)).toBeTruthy();
      expect(mocks.confirm).not.toHaveBeenCalled();
    });
  });
});
