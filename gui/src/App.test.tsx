// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { BranchInfo, CommitGraph, CommitLogEntry, SproutStatus } from "./lib/sprout";

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  confirm: vi.fn(),
  onDragDropEvent: vi.fn(),
  invoke: vi.fn(),
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
  });

  afterEach(cleanup);

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

  it("refreshes workspace state only from the update button", async () => {
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
    expect(mocks.confirm).toHaveBeenCalledWith(expect.stringContaining("元に戻せません"), expect.objectContaining({ kind: "warning" }));
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
    mocks.runSprout
      .mockResolvedValueOnce({ current_commit: commitEntry.id, branch: "main", branch_id: "main", at_branch_tip: true, bud: null, changes: [] })
      .mockResolvedValueOnce({ id: "rethink", name: "rethink", commit_id: commitEntry.id, comment: "", current: true });
    mockWorkspace();
    await user.click(screen.getByRole("button", { name: "枝を作って移動" }));
    expect(await screen.findByText("aaaaaaaaaaaa から枝 rethink を伸ばしました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["branch", "rethink", commitEntry.id, "--switch"], "");

    mocks.open.mockResolvedValueOnce("C:\\work\\out");
    mocks.runSprout.mockResolvedValueOnce({ commit_id: commitEntry.id, output: "C:\\work\\out", paths: ["design/main.psd"] });
    await user.click(screen.getByRole("button", { name: "ファイルを取り出す" }));
    expect(await screen.findByText("1件のファイルを C:\\work\\out へ書き出しました")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledWith(project, ["export", commitEntry.id, "--output", "C:\\work\\out"], "");
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

  it("selects branch names placed beside a stem by click and keyboard", async () => {
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
    expect(fork.closest(".branch-label")?.classList.contains("side")).toBe(true);
    expect(fork.textContent).toBe("分岐2（現在のブランチ）");
    expect(screen.getByRole("button", { name: "ブランチ main" }).closest(".branch-label")?.classList.contains("top")).toBe(true);

    await user.click(fork);
    expect(within(screen.getByRole("region", { name: "選択中のブランチ" })).getByRole("heading", { name: "分岐2" })).toBeTruthy();
    screen.getByRole("button", { name: "ブランチ copy" }).focus();
    await user.keyboard("{Enter}");
    expect(within(screen.getByRole("region", { name: "選択中のブランチ" })).getByRole("heading", { name: "copy" })).toBeTruthy();
  });
});
