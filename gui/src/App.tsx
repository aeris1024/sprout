import { useEffect, useRef, useState, type CSSProperties } from "react";
import { confirm as confirmDialog, open, save } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { DragDropEvent } from "@tauri-apps/api/webview";
import BranchPanel from "./components/BranchPanel";
import BudPanel from "./components/BudPanel";
import ComparePanel from "./components/ComparePanel";
import CommitPanel from "./components/CommitPanel";
import FilePanel from "./components/FilePanel";
import ProjectMenu, { RecentProjectList, projectName } from "./components/ProjectMenu";
import TrashPanel from "./components/TrashPanel";
import MaintenancePanel from "./components/MaintenancePanel";
import PanelSplitter from "./components/PanelSplitter";
import SavePanel from "./components/SavePanel";
import SproutMap, { type MapSelection } from "./components/SproutMap";
import "./App.css";
import {
  isUninitializedProject,
  normalizeCliError,
  runSprout,
  type Bud,
  type StatusChange,
  type TrashItem,
  type CoverApplyResult,
  coverReasonLabel,
  type DoctorReport,
  type GcResult,
  type RepositoryStats,
  formatBytes,
  type CommitDeletion,
  type CommitDetail,
  type CommitGraph,
  type CommitResult,
  type GoResult,
  type PathOperationResult,
  type SproutCliError,
  type SproutStatus,
} from "./lib/sprout";
import { PANEL_WIDTH, savedPanelWidth } from "./lib/panelWidth";
import { loadSettings, nextRecentProjects, removeRecentProject, savePanelWidth, saveSettings } from "./lib/settings";
import { clipboardImage, discardPastedThumbnail, savePastedPreview, readClipboardFiles, savePastedThumbnail, thumbnailImageProblem } from "./lib/clipboard";

type Notice = SproutCliError & { kind: "error" | "success" | "warning" };

const emptyGraph: CommitGraph = { current_commit: null, at_branch_tip: true, commits: [], branches: [], tags: [], buds: [] };
const UNCHANGED_NOTE = "作業フォルダは変更していません。";
/** Refetch at most once per interval when focus changes quickly; a late focus gets one trailing refetch. */
const FOCUS_REFRESH_INTERVAL_MS = 2000;
const FOCUS_REFRESH_FAILED = "focus_refresh_failed";

/** Where a file dropped right now would go; "blocked" means the displayed panel takes no drops. */
type DropDestination =
  | { kind: "preview"; commitId: string; message: string }
  | { kind: "track"; message: string }
  | { kind: "blocked"; message: string };

function shortId(value: string | null): string {
  return value ? value.slice(0, 12) : "-";
}

/** End option parsing when editable positional text starts like an option. */
function positionalArguments(...values: string[]): string[] {
  return values.some((value) => value.startsWith("-")) ? ["--", ...values] : values;
}

/** Keep option values such as the literal --json separate from actual CLI flags. */
function textOption(flag: string, value: string): string[] {
  return value.startsWith("-") ? [`${flag === "-m" ? "--message" : flag}=${value}`] : [flag, value];
}

/** True for fields that take typed text; a focused checkbox or button does not capture a paste. */
function isTextField(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return target.closest('textarea, [contenteditable]:not([contenteditable="false"]), input:not([type="checkbox"], [type="radio"], [type="button"], [type="submit"], [type="file"])') !== null;
}

/** Describe a delete-commit dry run so the confirmation lists every reference it moves. */
function deletionSummary(preview: CommitDeletion): string {
  const parent = preview.parent_id ? `親の葉（${shortId(preview.parent_id)}）` : "葉のない状態";
  const lines = [`葉「${preview.commit.message}」（${shortId(preview.commit.id)}）をゴミ箱へ移します。参照が変更される前ならゴミ箱から復旧できます。`];
  if (preview.moved_branches.length > 0) {
    lines.push(`ブランチ ${preview.moved_branches.map((branch) => branch.name).join(", ")} は${parent}へ移ります。`);
  }
  if (preview.moved_current) lines.push(`いまここも${parent}へ移ります。作業ファイルは変わらず、未保存の変更として残ります。`);
  if (preview.reconnected_children.length > 0) {
    lines.push(`子の葉 ${preview.reconnected_children.length}件は${preview.parent_id ? "親の葉へつなぎ直されます" : "根になります"}。`);
  }
  if (preview.rebased_buds.length > 0) lines.push(`つぼみ ${preview.rebased_buds.length}件の起点は${parent}へ付け替わります。`);
  if (preview.reclaimable_objects.length > 0) {
    lines.push(`${preview.reclaimable_objects.length}個のオブジェクト（${preview.reclaimable_bytes} bytes）はゴミ箱に保持され、sprout maintenance gc から保護されます。`);
  }
  lines.push("続行しますか？");
  return lines.join("\n");
}

/** Report a refused move with its reason and path, and that nothing was changed. */
function unchangedError(error: unknown): SproutCliError {
  const cliError = normalizeCliError(error);
  return { ...cliError, message: `${cliError.message}（${UNCHANGED_NOTE}）` };
}

function App() {
  const [projectDir, setProjectDir] = useState("");
  const [status, setStatus] = useState<SproutStatus | null>(null);
  const [graph, setGraph] = useState<CommitGraph>(emptyGraph);
  const [commitDetail, setCommitDetail] = useState<CommitDetail | null>(null);
  const [commitLoadError, setCommitLoadError] = useState<{ id: string; error: SproutCliError } | null>(null);
  const [selection, setSelection] = useState<MapSelection>(null);
  const [comparison, setComparison] = useState<{ source: string; target: string } | null>(null);
  useEffect(() => { setComparison(null); }, [projectDir]);
  const [filesOpen, setFilesOpen] = useState(false);
  const [trashOpen, setTrashOpen] = useState(false);
  const [trashItems, setTrashItems] = useState<TrashItem[]>([]);
  useEffect(() => { setTrashOpen(false); setTrashItems([]); }, [projectDir]);
  const [maintenanceOpen, setMaintenanceOpen] = useState(false);
  const [repositoryStats, setRepositoryStats] = useState<RepositoryStats | null>(null);
  const [gcResult, setGcResult] = useState<GcResult | null>(null);
  const [doctorReport, setDoctorReport] = useState<DoctorReport | null>(null);
  useEffect(() => { setMaintenanceOpen(false); setRepositoryStats(null); setGcResult(null); setDoctorReport(null); }, [projectDir]);
  const [recentProjects, setRecentProjects] = useState<string[]>([]);
  const [sproutProgram, setSproutProgram] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(PANEL_WIDTH.default);
  const [initCandidate, setInitCandidate] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [thumbnailPath, setThumbnailPath] = useState("");
  const pastedThumbnail = useRef("");
  const pasteHandler = useRef<(event: ClipboardEvent) => void>(() => {});
  const dragDropHandler = useRef<(payload: DragDropEvent) => void>(() => {});
  const [dragging, setDragging] = useState(false);
  const operationActive = useRef(false);
  const detailRead = useRef<{ path: string; id: string; program: string } | null>(null);
  const operationsStarted = useRef(0);
  const focusHandler = useRef<() => void>(() => {});
  const focusRefresh = useRef({ running: false, startedAt: 0, failed: false, timer: undefined as ReturnType<typeof setTimeout> | undefined });

  useEffect(() => {
    const read = detailRead.current;
    const leafVisible = selection?.kind === "commit" && !filesOpen && !trashOpen && !maintenanceOpen && !comparison;
    if (read && (read.path !== projectDir || read.program !== sproutProgram || !leafVisible || selection?.id !== read.id || busy)) {
      detailRead.current = null;
    }
    // A panel switch or operation can cancel a pending read. Fetch again if that leaf becomes visible.
    if (!detailRead.current && !busy && projectDir && leafVisible && commitDetail?.id !== selection.id && commitLoadError?.id !== selection.id) {
      selectCommit(selection.id);
    }
  }, [projectDir, sproutProgram, selection, filesOpen, trashOpen, maintenanceOpen, comparison, busy]);
  useEffect(() => () => { detailRead.current = null; }, []);

  useEffect(() => {
    void loadSettings()
      .then((settings) => {
        setRecentProjects(settings.recentProjects);
        setSproutProgram(settings.sproutProgram);
        setPanelWidth(savedPanelWidth(settings.panelWidth));
      })
      .catch((error) => setNotice({ ...normalizeCliError(error), kind: "error" }));
  }, []);

  /** Run one operation at a time; resolves true only when it completed without an error. */
  async function execute(operation: () => Promise<void>): Promise<boolean> {
    if (operationActive.current) return false;
    detailRead.current = null;
    operationActive.current = true;
    operationsStarted.current += 1;
    setBusy(true);
    setNotice(null);
    try {
      await operation();
      return true;
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
      return false;
    } finally {
      operationActive.current = false;
      setBusy(false);
    }
  }

  async function fetchWorkspace(path: string, stillWanted: () => boolean = () => true) {
    const nextStatus = await runSprout<SproutStatus>(path, ["status", "--tracked", "--untracked"], sproutProgram);
    const nextGraph = await runSprout<CommitGraph>(path, ["leaf", "tree"], sproutProgram);
    if (!stillWanted()) return;
    setProjectDir(path);
    setStatus(nextStatus);
    setGraph(nextGraph);
    setSelection((current) => {
      if (current?.kind === "commit" && !nextGraph.commits.some((entry) => entry.id === current.id)) return null;
      if (current?.kind === "bud" && !nextGraph.buds.some((bud) => bud.id === current.id)) return null;
      if (current?.kind === "branch" && !nextGraph.branches.some((branch) => branch.id === current.id)) return null;
      return current;
    });
  }

  async function rememberProject(path: string) {
    const updated = nextRecentProjects(recentProjects, path);
    setRecentProjects(updated);
    try {
      await saveSettings({ recentProjects: updated, sproutProgram });
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
    }
  }

  function forgetRecentProject(path: string) {
    void execute(async () => {
      const updated = removeRecentProject(recentProjects, path);
      await saveSettings({ recentProjects: updated, sproutProgram });
      setRecentProjects(updated);
    });
  }

  async function loadProject(path: string) {
    detailRead.current = null;
    setComparison(null);
    setInitCandidate("");
    setCommitDetail(null);
    setSelection(null);
    setFilesOpen(false);
    try {
      await fetchWorkspace(path);
      await rememberProject(path);
    } catch (error) {
      const cliError = normalizeCliError(error);
      setStatus(null);
      setGraph(emptyGraph);
      setProjectDir(path);
      if (isUninitializedProject(cliError)) setInitCandidate(path);
      if (cliError.code === "sprout_not_found") setSettingsOpen(true);
      throw cliError;
    }
  }

  function openProject(path: string) {
    void execute(() => loadProject(path));
  }

  function chooseProject() {
    void execute(async () => {
      const selected = await open({ directory: true, multiple: false, title: "Sproutプロジェクトを選択" });
      if (typeof selected === "string") await loadProject(selected);
    });
  }

  function refreshProject() {
    if (!projectDir) return;
    void execute(async () => {
      await fetchWorkspace(projectDir);
    });
  }

  /**
   * Refetch quietly when the window regains focus: no busy state, so buttons and drafts stay usable,
   * and no execute(), so the current notice stays. A result is dropped if an operation started meanwhile.
   */
  function refreshOnFocus() {
    const refresh = focusRefresh.current;
    if (!workspaceOpen || operationActive.current) return;
    const wait = refresh.startedAt + FOCUS_REFRESH_INTERVAL_MS - Date.now();
    if (refresh.running || wait > 0) {
      refresh.timer ??= setTimeout(() => {
        refresh.timer = undefined;
        focusHandler.current();
      }, wait > 0 ? wait : FOCUS_REFRESH_INTERVAL_MS);
      return;
    }
    refresh.running = true;
    refresh.startedAt = Date.now();
    const operations = operationsStarted.current;
    const unchanged = () => operationsStarted.current === operations;
    void fetchWorkspace(projectDir, unchanged)
      .then(() => {
        refresh.failed = false;
        setNotice((current) => current?.code === FOCUS_REFRESH_FAILED ? null : current);
      })
      .catch((error) => {
        // Warn once per failure streak, and never over a notice the user is still reading.
        if (refresh.failed || !unchanged()) return;
        refresh.failed = true;
        const message = `最新の状態を取得できませんでした。表示は前回取得した内容です（${normalizeCliError(error).message}）`;
        setNotice((current) => current ?? { code: FOCUS_REFRESH_FAILED, message, details: {}, kind: "warning" });
      })
      .finally(() => {
        refresh.running = false;
      });
  }
  focusHandler.current = refreshOnFocus;

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let disposed = false;
    let appWindow: ReturnType<typeof getCurrentWindow>;
    try {
      appWindow = getCurrentWindow();
    } catch {
      return undefined;
    }
    void appWindow
      .onFocusChanged(({ payload: focused }) => {
        if (focused) focusHandler.current();
      })
      .then((stop) => {
        if (disposed) stop();
        else unlisten = stop;
      })
      .catch(() => undefined);
    return () => {
      disposed = true;
      unlisten?.();
      clearTimeout(focusRefresh.current.timer);
      focusRefresh.current.timer = undefined;
    };
  }, []);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let disposed = false;
    let appWindow: ReturnType<typeof getCurrentWindow>;
    try {
      appWindow = getCurrentWindow();
    } catch {
      return undefined;
    }
    void appWindow
      .onDragDropEvent((event) => dragDropHandler.current(event.payload))
      .then((stop) => {
        if (disposed) stop();
        else unlisten = stop;
      })
      .catch(() => undefined);
    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  function initializeProject() {
    if (!initCandidate) return;
    void execute(async () => {
      await runSprout(initCandidate, ["init", "."], sproutProgram);
      await fetchWorkspace(initCandidate);
      await rememberProject(initCandidate);
      setInitCandidate("");
      setNotice({ code: "initialized", message: "Sproutプロジェクトを初期化しました", details: {}, kind: "success" });
    });
  }

  function saveCliSetting() {
    void execute(async () => {
      const value = sproutProgram.trim();
      await saveSettings({ recentProjects, sproutProgram: value });
      setSproutProgram(value);
      setNotice({ code: "settings_saved", message: "CLI設定を保存しました", details: {}, kind: "success" });
    });
  }

  function trackPaths(paths: string[]) {
    if (!projectDir || paths.length === 0) return;
    void execute(async () => {
      const result = await runSprout<PathOperationResult>(projectDir, ["file", "track", ...paths], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({
        code: result.paths.length ? "paths_tracked" : "no_paths_tracked",
        message: result.paths.length ? `${result.paths.length}件を追跡対象に追加しました` : "追跡対象に追加されたファイルはありません",
        details: { paths: result.paths },
        kind: result.paths.length ? "success" : "warning",
      });
    });
  }

  function setCover(path: string) {
    void execute(async () => {
      const result = await runSprout<{ path: string; problem: string | null }>(projectDir, ["leaf", "thumbnail", "source", "set", ...fileArguments([path])], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice(result.problem
        ? { code: "cover_set", message: `${result.path} をサムネイル自動生成元にしました。ただし今はサムネイルを作れません: ${coverReasonLabel(result.problem)}`, details: {}, kind: "warning" }
        : { code: "cover_set", message: `${result.path} をサムネイル自動生成元にしました`, details: {}, kind: "success" });
    });
  }

  function clearCover() {
    void execute(async () => {
      await runSprout(projectDir, ["leaf", "thumbnail", "source", "clear"], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({ code: "cover_cleared", message: "サムネイル自動生成元を解除しました", details: {}, kind: "success" });
    });
  }

  function applyCover() {
    void execute(async () => {
      const plan = await runSprout<CoverApplyResult>(projectDir, ["leaf", "thumbnail", "source", "apply", "--dry-run"], sproutProgram);
      if (plan.applied.length === 0) {
        setNotice({ code: "cover_nothing", message: `サムネイルを作れる葉はありません（登録済み ${plan.kept}件・対象外 ${plan.skipped.length}件）`, details: {}, kind: "success" });
        return;
      }
      if (!await confirmDialog(`サムネイルのない ${plan.applied.length}件の葉に、サムネイル自動生成元からサムネイルを作ります。登録済みのサムネイルは変更しません。続行しますか？`, {
        title: "既存の葉へ適用", kind: "warning", okLabel: "適用", cancelLabel: "キャンセル",
      })) return;
      const result = await runSprout<CoverApplyResult>(projectDir, ["leaf", "thumbnail", "source", "apply"], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({ code: "cover_applied", message: `${result.applied.length}件の葉にサムネイルを作りました`, details: {}, kind: "success" });
    });
  }

  function chooseTrackFiles(directory: boolean) {
    if (!projectDir || operationActive.current) return;
    void open({
      directory,
      multiple: !directory,
      defaultPath: projectDir,
      title: directory ? "追跡するフォルダを選択" : "追跡するファイルを選択",
    }).then((selected) => {
      if (typeof selected === "string") trackPaths([selected]);
      if (Array.isArray(selected)) trackPaths(selected);
    });
  }

  function untrackPath(path: string) {
    if (!projectDir) return;
    void execute(async () => {
      const result = await runSprout<PathOperationResult>(projectDir, ["file", "untrack", path], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({
        code: result.paths.length ? "paths_untracked" : "no_paths_untracked",
        message: result.paths.length ? `${result.paths.length}件を追跡対象から外しました` : "追跡解除されたファイルはありません",
        details: { paths: result.paths },
        kind: result.paths.length ? "success" : "warning",
      });
    });
  }

  /** Change the save form's thumbnail, deleting a previously pasted temporary file. */
  function replaceThumbnailPath(path: string, pasted = false) {
    const previous = pastedThumbnail.current;
    if (previous && previous !== path) void discardPastedThumbnail(previous).catch(() => {});
    pastedThumbnail.current = pasted ? path : "";
    setThumbnailPath(path);
  }

  function chooseThumbnail() {
    if (operationActive.current) return;
    void open({
      multiple: false,
      title: "葉のサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected === "string") replaceThumbnailPath(selected);
    });
  }

  function commitChanges() {
    if (!projectDir) return;
    const message = commitMessage.trim();
    if (!message) {
      setNotice({ code: "message_required", message: "メッセージを入力してください", details: {}, kind: "warning" });
      return;
    }
    void execute(async () => {
      const args = ["leaf", "create", ...textOption("-m", message)];
      if (thumbnailPath) args.push("--thumbnail", thumbnailPath);
      const result = await runSprout<CommitResult>(projectDir, args, sproutProgram);
      setCommitMessage("");
      replaceThumbnailPath("");
      await fetchWorkspace(projectDir);
      setSelection(null);
      const saved = result.created_branch
        ? `新しいブランチ ${result.branch} を作り、${shortId(result.id)} を保存しました`
        : `葉 ${shortId(result.id)} を保存しました`;
      const noCover = result.cover && !result.cover.applied;
      setNotice({
        code: "committed",
        message: noCover ? `${saved}。サムネイルは作れませんでした: ${coverReasonLabel(result.cover?.reason)}` : saved,
        details: { id: result.id },
        kind: noCover ? "warning" : "success",
      });
    });
  }

  function selectCommit(commitId: string) {
    if (!projectDir) return;
    if (operationActive.current) {
      setNotice({ code: "operation_in_progress", message: "操作の実行中は葉を選べません。完了してから選んでください。", details: {}, kind: "warning" });
      return;
    }
    setTrashOpen(false);
    setMaintenanceOpen(false);
    if (comparison) { setComparison({ ...comparison, target: commitId }); return; }
    setSelection({ kind: "commit", id: commitId });
    setFilesOpen(false);
    setCommitLoadError(null);
    const read = { path: projectDir, id: commitId, program: sproutProgram };
    detailRead.current = read;
    void runSprout<CommitDetail>(projectDir, ["leaf", "show", commitId], sproutProgram)
      .then((detail) => {
        if (detailRead.current === read) setCommitDetail(detail);
      })
      .catch((error) => {
        if (detailRead.current !== read) return;
        const cliError = normalizeCliError(error);
        setCommitLoadError({ id: commitId, error: cliError });
        setNotice({ ...cliError, kind: "error" });
      });
  }

  function selectBud(budId: string) {
    setTrashOpen(false);
    setMaintenanceOpen(false);
    setComparison(null);
    setSelection({ kind: "bud", id: budId });
    setFilesOpen(false);
  }

  function selectBranch(branchId: string) {
    setTrashOpen(false);
    setMaintenanceOpen(false);
    setComparison(null);
    setSelection({ kind: "branch", id: branchId });
    setFilesOpen(false);
  }

  /** Run a branch edit by its current name, then refresh; the selection follows the branch ID. */
  function editBranch(branchId: string, args: (name: string) => string[], message: (name: string) => string): Promise<boolean> {
    const branch = graph.branches.find((item) => item.id === branchId);
    if (!projectDir || !branch) return Promise.resolve(false);
    return execute(async () => {
      await runSprout(projectDir, args(branch.name), sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({ code: "branch_updated", message: message(branch.name), details: { branch_id: branchId }, kind: "success" });
    });
  }

  function renameBranch(branchId: string, name: string) {
    return editBranch(branchId, (current) => ["branch", "rename", ...positionalArguments(current, name)], (current) => `ブランチ ${current} の名前を ${name} に変更しました`);
  }

  function setBranchComment(branchId: string, comment: string) {
    return editBranch(branchId, (current) => ["branch", "comment", ...positionalArguments(current, comment)], (current) => `ブランチ ${current} のコメントを変更しました`);
  }

  function deleteBranch(branchId: string) {
    const branch = graph.branches.find((item) => item.id === branchId);
    if (!projectDir || !branch || operationActive.current) return;
    void confirmDialog(`ブランチ ${branch.name} を削除します。このブランチの葉は削除されず、「削除済みブランチ由来」として残ります。ブランチはゴミ箱から戻せます。続行しますか？`, {
      title: "ブランチを削除",
      kind: "warning",
      okLabel: "削除",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (accepted) void editBranch(branchId, (current) => ["branch", "delete", current], (current) => `ブランチ ${current} を削除しました`);
    });
  }

  function renameBud(budId: string, name: string) {
    return execute(async () => {
      await runSprout(projectDir, ["bud", "rename", ...positionalArguments(budId, name)], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({ code: "bud_renamed", message: name.trim() ? `つぼみの名前を「${name.trim()}」にしました` : "つぼみの名前を消しました", details: { bud_id: budId }, kind: "success" });
    });
  }

  function selectUnsaved() {
    setTrashOpen(false);
    setMaintenanceOpen(false);
    setComparison(null);
    setSelection({ kind: "unsaved" });
    setFilesOpen(false);
  }

  function closeSelection() {
    detailRead.current = null;
    setSelection(null);
    setCommitDetail(null);
    setCommitLoadError(null);
  }

  /** Run an edit of one snapshot's annotations, then refresh the map and its detail. */
  function editCommit(commitId: string, args: string[], message: string): Promise<boolean> {
    if (!projectDir) return Promise.resolve(false);
    return execute(async () => {
      await runSprout(projectDir, args, sproutProgram);
      await fetchWorkspace(projectDir);
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["leaf", "show", commitId], sproutProgram));
      setNotice({ code: "annotation_updated", message, details: { commit_id: commitId }, kind: "success" });
    });
  }

  function saveNote(commitId: string, note: string) {
    const deleting = !note.trim();
    return editCommit(
      commitId,
      deleting ? ["leaf", "edit", commitId, "--clear-note"] : ["leaf", "edit", commitId, ...textOption("--note", note)],
      deleting ? `${shortId(commitId)} のメモを削除しました` : `${shortId(commitId)} のメモを保存しました`,
    );
  }

  function addLabel(commitId: string, label: string) {
    return editCommit(commitId, ["leaf", "label", "add", ...positionalArguments(commitId, label)], `ラベル「${label.trim()}」を追加しました`);
  }

  function removeLabel(commitId: string, label: string) {
    return editCommit(commitId, ["leaf", "label", "remove", ...positionalArguments(commitId, label)], `ラベル「${label}」を外しました`);
  }

  function createTag(commitId: string, name: string, comment: string) {
    const args = ["leaf", "tag", "create", name, commitId];
    if (comment.trim()) args.push(...textOption("--comment", comment));
    return editCommit(commitId, args, `タグ ${name} を付けました`);
  }

  function setTagComment(commitId: string, name: string, comment: string) {
    return editCommit(commitId, ["leaf", "tag", "comment", ...positionalArguments(name, comment)], `タグ ${name} のコメントを変更しました`);
  }

  function deleteTag(commitId: string, name: string) {
    if (!projectDir || operationActive.current) return;
    void confirmDialog(`タグ ${name} を削除します。葉は削除されません。タグはゴミ箱から戻せます。続行しますか？`, {
      title: "タグを削除",
      kind: "warning",
      okLabel: "削除",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (accepted) void editCommit(commitId, ["leaf", "tag", "delete", name], `タグ ${name} を削除しました`);
    });
  }

  function setCommitThumbnail(commitId: string) {
    if (!projectDir || operationActive.current) return;
    void open({
      multiple: false,
      title: "葉のサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected !== "string") return;
      void execute(() => applyCommitThumbnail(commitId, selected));
    });
  }

  async function applyCommitThumbnail(commitId: string, path: string) {
    await runSprout(projectDir, ["leaf", "thumbnail", "set", commitId, path], sproutProgram);
    await fetchWorkspace(projectDir);
    setCommitDetail(await runSprout<CommitDetail>(projectDir, ["leaf", "show", commitId], sproutProgram));
    setNotice({ code: "thumbnail_saved", message: `${shortId(commitId)} のサムネイルを保存しました`, details: { commit_id: commitId }, kind: "success" });
  }

  /** Ctrl+V with an image sets the thumbnail of the displayed save form or commit; text fields and text pastes pass through. */
  function pasteThumbnail(event: ClipboardEvent) {
    if (event.defaultPrevented || !workspaceOpen || settingsOpen || operationActive.current) return;
    const commitId = displayedPanel === "commit" ? commitDetail?.id ?? null : null;
    if (!commitId && displayedPanel !== "save") return;
    const image = clipboardImage(event.clipboardData);
    if (!image) return;
    if (isTextField(event.target)) {
      if (!event.clipboardData?.getData("text/plain")) {
        setNotice({ code: "image_paste_in_text_field", message: "入力欄には画像を貼り付けられません。サムネイルに使う場合は入力欄の外を選んでからCtrl+Vを押してください", details: {}, kind: "warning" });
      }
      return;
    }
    event.preventDefault();
    const problem = thumbnailImageProblem(image);
    if (problem) {
      setNotice({ code: "unsupported_clipboard_image", message: problem, details: { media_type: image.type, size: image.size }, kind: "warning" });
      return;
    }
    const replacing = commitId !== null && (Boolean(commitDetail?.thumbnail) || Boolean(graph.commits.find((commit) => commit.id === commitId)?.attachments.some((item) => item.role === "thumbnail")));
    void execute(async () => {
      if (replacing && !await confirmDialog(`葉「${commitDetail?.message}」（${shortId(commitId)}）の今のサムネイルを、貼り付けた画像に置き換えます。続行しますか？`, {
        title: "サムネイルを置き換え", kind: "warning", okLabel: "置き換え", cancelLabel: "キャンセル",
      })) return;
      const path = await savePastedThumbnail(image);
      if (!commitId) {
        replaceThumbnailPath(path, true);
        setNotice({ code: "thumbnail_pasted", message: "貼り付けた画像を保存時のサムネイルにします", details: {}, kind: "success" });
        return;
      }
      try {
        await applyCommitThumbnail(commitId, path);
      } finally {
        await discardPastedThumbnail(path).catch(() => {});
      }
    });
  }
  pasteHandler.current = pasteThumbnail;

  /** Decide a drop's destination from the panel on screen, never from a selection hidden behind it. */
  function dropDestination(): DropDestination | null {
    if (!workspaceOpen) return null;
    if (operationActive.current) return { kind: "blocked", message: "操作の実行中はドロップできません" };
    if (settingsOpen) return { kind: "blocked", message: "CLI設定を閉じるとドロップできます" };
    if (displayedPanel === "trash") return { kind: "blocked", message: "ゴミ箱を閉じるとドロップできます" };
    if (displayedPanel === "maintenance") return { kind: "blocked", message: "保守を閉じるとドロップできます" };
    if (displayedPanel === "compare") return { kind: "blocked", message: "比較を閉じるとドロップできます" };
    if (displayedPanel === "loading") return { kind: "blocked", message: "葉の詳細を表示してからドロップしてください" };
    if (displayedPanel === "commit" && commitDetail) return { kind: "preview", commitId: commitDetail.id, message: `葉「${commitDetail.message}」（${shortId(commitDetail.id)}）のプレビューに追加します` };
    return { kind: "track", message: "作業フォルダの追跡対象に追加します" };
  }

  function handleDragDrop(payload: DragDropEvent) {
    if (payload.type === "enter" || payload.type === "over") {
      setDragging(true);
      return;
    }
    setDragging(false);
    if (payload.type !== "drop") return;
    const destination = dropDestination();
    if (destination?.kind === "preview") addPreviews(destination.commitId, payload.paths);
    else if (destination?.kind === "track") trackPaths(payload.paths);
    else if (destination && !operationActive.current) setNotice({ code: "drop_ignored", message: `ドロップしたファイルは追加していません。${destination.message}`, details: {}, kind: "warning" });
  }
  dragDropHandler.current = handleDragDrop;

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => pasteHandler.current(event);
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  function updateCommitMessage(commitId: string, message: string) {
    if (!projectDir) return;
    const normalized = message.trim();
    if (!normalized) {
      setNotice({ code: "message_required", message: "メッセージを入力してください", details: {}, kind: "warning" });
      return;
    }
    void execute(async () => {
      await runSprout(projectDir, ["leaf", "edit", commitId, ...textOption("--message", normalized)], sproutProgram);
      await fetchWorkspace(projectDir);
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["leaf", "show", commitId], sproutProgram));
      setNotice({ code: "message_updated", message: `${shortId(commitId)} のメッセージを変更しました`, details: { commit_id: commitId }, kind: "success" });
    });
  }

  /** Apply a go reply to the map and top bar without fetching them again. */
  function applyGoResult(result: GoResult) {
    setStatus((current) => current && {
      ...current,
      branch: result.branch,
      branch_id: result.branch_id,
      current_commit: result.current_commit,
      at_branch_tip: result.at_branch_tip,
      changes: result.changes,
    });
    setGraph((current) => ({
      ...current,
      current_commit: result.current_commit,
      at_branch_tip: result.at_branch_tip,
      branches: current.branches.map((branch) => ({ ...branch, current: branch.id === result.branch_id })),
      buds: result.bud ? [result.bud, ...current.buds] : current.buds,
    }));
  }

  function goTo(commitId: string) {
    if (!projectDir) return;
    void execute(async () => {
      let result: GoResult;
      try {
        result = await runSprout<GoResult>(projectDir, ["go", commitId], sproutProgram);
      } catch (error) {
        throw unchangedError(error);
      }
      applyGoResult(result);
      setNotice({
        code: "moved",
        message: result.bud
          ? `未保存の変更をつぼみに残して ${shortId(result.current_commit)} へ移動しました`
          : `${shortId(result.current_commit)} へ移動しました`,
        details: {},
        kind: "success",
      });
    });
  }

  function growBranch(commitId: string, name: string) {
    if (!projectDir) return;
    void execute(async () => {
      let result: { bud: Bud | null };
      try {
        result = await runSprout<{ bud: Bud | null }>(projectDir, ["branch", "create", name, commitId, "--switch"], sproutProgram);
      } catch (error) {
        // A refused branch moves nothing; the refresh only guards against an unexpected failure.
        await fetchWorkspace(projectDir).catch(() => {});
        throw unchangedError(error);
      }
      await fetchWorkspace(projectDir);
      setNotice({
        code: "branch_created",
        message: result.bud
          ? `未保存の変更をつぼみに残して ${shortId(commitId)} からブランチ ${name} を作りました`
          : `${shortId(commitId)} からブランチ ${name} を作りました`,
        details: { name },
        kind: "success",
      });
    });
  }

  // Prefix option-like names so CLI argument parsing cannot treat them as flags.
  function fileArguments(paths: string[]) {
    return paths.map((path) => path.startsWith("-") ? `./${path}` : path);
  }

  function exportFiles(commitId: string, paths: string[] = []) {
    if (!projectDir) return;
    void execute(async () => {
      const selected = await open({ directory: true, multiple: false, title: "書き出し先のフォルダを選択" });
      if (typeof selected !== "string") return;
      const result = await runSprout<{ paths: string[]; output: string }>(projectDir, ["file", "export", commitId, ...fileArguments(paths), "--output", selected], sproutProgram);
      setNotice({ code: "exported", message: `${result.paths.length}件のファイルを ${result.output} へ書き出しました`, details: {}, kind: "success" });
    });
  }

  function restoreFiles(commitId: string, paths: string[]) {
    if (!projectDir || paths.length === 0) return;
    void execute(async () => {
      const targets = paths.join("\n");
      const accepted = await confirmDialog(`${shortId(commitId)} の次の${paths.length}件を作業フォルダへ戻します。\n${targets}\n対象の作業ファイルを保存時の内容に置き換えます。選択外のファイル・現在位置・ブランチ先端は変わりません。続行しますか？`, {
        title: "選択したファイルだけ戻す", kind: "warning", okLabel: "戻す", cancelLabel: "キャンセル",
      });
      if (!accepted) return;
      const args = ["file", "restore", commitId, ...fileArguments(paths)];
      try {
        await runSprout(projectDir, args, sproutProgram);
      } catch (cause) {
        const error = normalizeCliError(cause);
        if (error.code !== "uncommitted_changes" || error.details.can_discard !== true) throw unchangedError(cause);
        const discard = await confirmDialog(`対象に未保存の変更があります。\n${targets}\nこの対象の未保存変更を破棄して戻しますか？破棄した変更はゴミ箱からつぼみとして戻せます。`, {
          title: "未保存変更の破棄を確認", kind: "warning", okLabel: "変更を破棄して戻す", cancelLabel: "キャンセル",
        });
        if (!discard) return;
        try {
          await runSprout(projectDir, [...args, "--discard"], sproutProgram);
        } catch (failure) { throw unchangedError(failure); }
      }
      await fetchWorkspace(projectDir);
      setNotice({ code: "files_restored", message: `${paths.length}件のファイルを戻しました`, details: {}, kind: "success" });
    });
  }

  type PreviewPlan = { previews: { original_name: string; size: number }[]; additional_bytes: number; requires_confirmation: boolean };

  async function registerPreviews(commitId: string, paths: string[], replacement?: string) {
    const args = ["leaf", "preview", replacement ? "replace" : "add", commitId, ...(replacement ? [replacement] : []), ...fileArguments(paths)];
    const plan = await runSprout<PreviewPlan>(projectDir, [...args, "--dry-run"], sproutProgram);
    if (plan.requires_confirmation) {
      const accepted = await confirmDialog(`100 MiBを超えるファイルを含みます。\n${plan.previews.map((item) => `${item.original_name}: ${item.size.toLocaleString()} B`).join("\n")}\n容量は圧縮前で最大 ${plan.additional_bytes.toLocaleString()} B 増加します。登録しますか？`, {
        title: "大容量プレビューの確認", kind: "warning", okLabel: "登録", cancelLabel: "キャンセル",
      });
      if (!accepted) return false;
    }
    await runSprout(projectDir, [...args, ...(plan.requires_confirmation ? ["--yes"] : [])], sproutProgram);
    return true;
  }

  function previewOperation(commitId: string, operation: () => Promise<boolean>) {
    void execute(async () => {
      if (!await operation()) return;
      await fetchWorkspace(projectDir);
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["leaf", "show", commitId], sproutProgram));
      setNotice({ code: "preview_updated", message: "プレビューの操作が完了しました", details: {}, kind: "success" });
    });
  }

  function addPreviews(commitId: string, paths: string[]) {
    if (paths.length) previewOperation(commitId, () => registerPreviews(commitId, paths));
  }

  function choosePreviews(commitId: string, replacement?: string) {
    previewOperation(commitId, async () => {
      const selected = await open({ multiple: !replacement, title: replacement ? "プレビューを置き換え" : "プレビューを追加" });
      const paths = typeof selected === "string" ? [selected] : selected;
      return paths?.length ? registerPreviews(commitId, paths, replacement) : false;
    });
  }

  function pastePreviews(commitId: string, files: File[]) {
    previewOperation(commitId, async () => {
      const paths: string[] = [];
      try {
        for (const file of files) paths.push(await savePastedPreview(file));
        return await registerPreviews(commitId, paths);
      } finally {
        await Promise.all(paths.map((path) => discardPastedThumbnail(path).catch(() => {})));
      }
    });
  }

  function pasteNativePreviews(commitId: string) {
    previewOperation(commitId, async () => {
      const paths = await readClipboardFiles();
      return paths.length ? registerPreviews(commitId, paths) : false;
    });
  }

  function deletePreview(commitId: string, id: string) {
    previewOperation(commitId, async () => {
      if (!await confirmDialog("このプレビューをゴミ箱へ移します。添付一覧が変更される前ならゴミ箱から復旧できます。続行しますか？", { title: "プレビューを削除", kind: "warning", okLabel: "削除", cancelLabel: "キャンセル" })) return false;
      await runSprout(projectDir, ["leaf", "preview", "delete", commitId, id], sproutProgram);
      return true;
    });
  }

  function exportPreview(commitId: string, id: string, name: string) {
    void execute(async () => {
      const output = await save({ title: "プレビューを取り出す", defaultPath: name });
      if (!output) return;
      await runSprout(projectDir, ["leaf", "preview", "export", commitId, id, "--output", output], sproutProgram);
      setNotice({ code: "preview_exported", message: `プレビューを ${output} へ取り出しました`, details: {}, kind: "success" });
    });
  }

  function orderPreviews(commitId: string, ids: string[]) {
    previewOperation(commitId, async () => {
      await runSprout(projectDir, ["leaf", "preview", "order", commitId, ...ids], sproutProgram);
      return true;
    });
  }

  function restoreBud(budId: string) {
    if (!projectDir) return;
    void execute(async () => {
      let result: { restored: Bud; saved: Bud | null };
      try {
        result = await runSprout(projectDir, ["bud", "restore", budId], sproutProgram);
      } catch (error) {
        throw unchangedError(error);
      }
      await fetchWorkspace(projectDir);
      setSelection({ kind: "unsaved" });
      setNotice({
        code: "bud_restored",
        message: result.saved ? "今の変更をつぼみに残して、選んだつぼみに戻りました" : "つぼみの変更に戻りました",
        details: {},
        kind: "success",
      });
    });
  }

  function dropBud(budId: string) {
    if (!projectDir || operationActive.current) return;
    void confirmDialog("このつぼみをゴミ箱へ移します。ゴミ箱から戻せます。続行しますか？", {
      title: "つぼみを捨てる",
      kind: "warning",
      okLabel: "捨てる",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (!accepted) return;
      void execute(async () => {
        await runSprout(projectDir, ["bud", "delete", budId, "--yes"], sproutProgram);
        await fetchWorkspace(projectDir);
        setSelection(null);
        setNotice({ code: "bud_dropped", message: "つぼみをゴミ箱へ移しました", details: {}, kind: "success" });
      });
    });
  }

  function keepAsBud() {
    if (!projectDir || operationActive.current) return;
    void execute(async () => {
      try {
        await runSprout<Bud>(projectDir, ["bud", "save"], sproutProgram);
      } catch (error) {
        // Nothing to keep means the view was stale; refresh so the panel matches the working folder.
        if (normalizeCliError(error).code === "nothing_to_save") await fetchWorkspace(projectDir).catch(() => {});
        throw unchangedError(error);
      }
      await fetchWorkspace(projectDir);
      setNotice({ code: "bud_saved", message: "未保存の変更をつぼみへ移し、作業フォルダを今の葉の内容に戻しました", details: {}, kind: "success" });
    });
  }

  function revertUnsaved(change: StatusChange) {
    const commitId = status?.current_commit;
    if (!projectDir || operationActive.current) return;
    const untrack = change.state === "added";
    if (!untrack && !commitId) return;
    void execute(async () => {
      const accepted = await confirmDialog(untrack
        ? `${change.path} を追跡対象から外します。
ファイル自体は削除せず、未保存の変更からも外れます。続行しますか？`
        : `${change.path} を${commitId ? shortId(commitId) : ""}の内容に戻します。
${change.state === "deleted" ? "削除したファイルを復元します。" : "作業ファイルの変更内容は失われます。"}破棄した変更はゴミ箱からつぼみとして戻せます。続行しますか？`, {
        title: untrack ? "追跡から外す" : "未保存の変更を元に戻す", kind: "warning", okLabel: untrack ? "外す" : "元に戻す", cancelLabel: "キャンセル",
      });
      if (!accepted) return;
      try {
        await runSprout(projectDir, untrack ? ["file", "untrack", ...fileArguments([change.path])] : ["file", "restore", commitId!, ...fileArguments([change.path]), "--discard"], sproutProgram);
      } catch (error) {
        throw unchangedError(error);
      }
      await fetchWorkspace(projectDir);
      setNotice({
        code: untrack ? "paths_untracked" : "unsaved_reverted",
        message: untrack ? `${change.path} を追跡対象から外しました。ファイルは残っています` : `${change.path} を元に戻しました`,
        details: { path: change.path },
        kind: "success",
      });
    });
  }

  function openSaveForm() {
    setTrashOpen(false);
    setMaintenanceOpen(false);
    setComparison(null);
    setFilesOpen(false);
    setSelection({ kind: "unsaved" });
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s" && status) {
        event.preventDefault();
        openSaveForm();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [status]);

  const tracked = status?.tracked ?? [];
  const untracked = status?.untracked ?? [];
  const changes = status?.changes ?? [];
  const currentCommit = graph.current_commit;
  /** Preview the deletion, confirm its effects, then delete; cancelling changes nothing. */
  async function deleteCommit(commitId: string) {
    if (!projectDir || operationActive.current) return;
    await execute(async () => {
      const preview = await runSprout<CommitDeletion>(projectDir, ["leaf", "delete", commitId, "--dry-run"], sproutProgram);
      const accepted = await confirmDialog(deletionSummary(preview), {
        title: "この葉を削除",
        kind: "warning",
        okLabel: "削除",
        cancelLabel: "キャンセル",
      });
      if (!accepted) return;
      await runSprout<CommitDeletion>(projectDir, ["leaf", "delete", commitId, "--yes"], sproutProgram);
      await fetchWorkspace(projectDir);
      closeSelection();
      setNotice({ code: "commit_deleted", message: `葉 ${shortId(commitId)} を削除しました`, details: { commit_id: commitId }, kind: "success" });
    });
  }

  function openTrash() {
    void execute(async () => {
      const items = await runSprout<TrashItem[]>(projectDir, ["trash", "list"], sproutProgram);
      setTrashItems(items);
      setMaintenanceOpen(false);
      setTrashOpen(true);
    });
  }

  function openMaintenance() {
    void execute(async () => {
      setRepositoryStats(await runSprout<RepositoryStats>(projectDir, ["maintenance", "stats"], sproutProgram));
      setGcResult(null);
      setDoctorReport(null);
      setTrashOpen(false);
      setComparison(null);
      setFilesOpen(false);
      setMaintenanceOpen(true);
    });
  }

  function collectGarbage() {
    void execute(async () => {
      const preview = await runSprout<GcResult>(projectDir, ["maintenance", "gc", "--dry-run"], sproutProgram);
      if (preview.removed_objects === 0 && preview.removed_temps === 0) {
        setGcResult(null);
        setNotice({ code: "gc_nothing", message: "回収できる容量はありません。ゴミ箱に保持中のデータは、完全削除すると回収できます。", details: {}, kind: "success" });
        return;
      }
      if (!await confirmDialog(`オブジェクト ${preview.removed_objects}個、一時ファイル ${preview.removed_temps}個を削除し、${formatBytes(preview.freed_bytes)}を回収します。ゴミ箱に保持中のデータは回収しません。続行しますか？`, {
        title: "容量を回収", kind: "warning", okLabel: "回収", cancelLabel: "キャンセル",
      })) return;
      const result = await runSprout<GcResult>(projectDir, ["maintenance", "gc"], sproutProgram);
      setGcResult(result);
      setRepositoryStats(await runSprout<RepositoryStats>(projectDir, ["maintenance", "stats"], sproutProgram));
      setNotice({ code: "gc_done", message: `${formatBytes(result.freed_bytes)}を回収しました`, details: {}, kind: "success" });
    });
  }

  function checkRepository() {
    void execute(async () => {
      setDoctorReport(null);
      setDoctorReport(await runSprout<DoctorReport>(projectDir, ["maintenance", "doctor", "--report"], sproutProgram));
    });
  }

  function inspectTrash(item: TrashItem) {
    void execute(async () => {
      const detail = await runSprout<TrashItem>(projectDir, ["trash", "show", item.id], sproutProgram);
      setTrashItems((items) => items.map((entry) => entry.id === item.id ? detail : entry));
    });
  }

  function restoreTrash(item: TrashItem) {
    void execute(async () => {
      await runSprout(projectDir, ["trash", "restore", item.id, "--dry-run"], sproutProgram);
      const restoresBud = item.kind === "bud_delete" || item.kind === "discard";
      if (!await confirmDialog(restoresBud ? `「${item.title}」をつぼみとして戻します。作業ファイルは変更しません。` : `「${item.title}」を復旧します。削除時に変更した履歴の参照や添付情報を戻します。作業ファイルは変更しません。`, {
        title: "ゴミ箱から復旧", kind: "warning", okLabel: "復旧", cancelLabel: "キャンセル",
      })) return;
      await runSprout(projectDir, ["trash", "restore", item.id], sproutProgram);
      await fetchWorkspace(projectDir);
      setCommitDetail(null);
      setSelection(null);
      setTrashItems(await runSprout<TrashItem[]>(projectDir, ["trash", "list"], sproutProgram));
      setNotice({ code: "trash_restored", message: "復旧しました。作業ファイルは変更していません。", details: {}, kind: "success" });
    });
  }

  function purgeTrash(item: TrashItem) {
    void execute(async () => {
      const preview = await runSprout<TrashItem>(projectDir, ["trash", "purge", item.id, "--dry-run"], sproutProgram);
      if (!await confirmDialog(`「${preview.title}」（${preview.id}）の復旧データを完全削除します。元に戻せません。保持容量 ${preview.protected_bytes} B、回収可能容量 ${preview.reclaimable_bytes} B。実体の回収は次回のgcで行います。`, {
        title: "復旧データを完全削除", kind: "warning", okLabel: "完全削除", cancelLabel: "キャンセル",
      })) return;
      await runSprout(projectDir, ["trash", "purge", item.id, "--yes"], sproutProgram);
      setTrashItems(await runSprout<TrashItem[]>(projectDir, ["trash", "list"], sproutProgram));
      setNotice({ code: "trash_purged", message: "復旧データを完全削除しました。", details: {}, kind: "success" });
    });
  }

  const selectedBud = selection?.kind === "bud" ? graph.buds.find((bud) => bud.id === selection.id) : undefined;
  const selectedBranch = selection?.kind === "branch" ? graph.branches.find((branch) => branch.id === selection.id) : undefined;
  const noticePath = typeof notice?.details.path === "string" ? notice.details.path : null;
  const workspaceOpen = Boolean(projectDir && status && !initCandidate);
  // Follows the order of sidePanel() so drops and pastes act on what is actually displayed.
  const displayedPanel = trashOpen ? "trash" : maintenanceOpen ? "maintenance" : comparison ? "compare" : filesOpen ? "files"
    : selection?.kind === "commit" ? (commitDetail?.id === selection.id ? "commit" : "loading")
    : selectedBranch ? "branch" : selectedBud ? "bud" : "save";
  const hoverDestination = dragging ? dropDestination() : null;

  function sidePanel() {
    if (trashOpen) return <TrashPanel items={trashItems} busy={busy} onInspect={inspectTrash} onRestore={restoreTrash} onPurge={purgeTrash} onClose={() => setTrashOpen(false)} />;
    if (maintenanceOpen) return <MaintenancePanel stats={repositoryStats} gcResult={gcResult} doctor={doctorReport} busy={busy} onCollect={collectGarbage} onCheck={checkRepository} onClose={() => setMaintenanceOpen(false)} />;
    if (comparison) return <ComparePanel projectDir={projectDir} program={sproutProgram} commits={graph.commits} source={comparison.source} target={comparison.target} busy={busy} onChange={(source, target) => setComparison({ source, target })} onClose={() => setComparison(null)} />;
    if (filesOpen) {
      return <FilePanel tracked={tracked} untracked={untracked} busy={busy} onAddFiles={() => chooseTrackFiles(false)} onAddFolder={() => chooseTrackFiles(true)} onTrack={(path) => trackPaths([path])} onUntrack={untrackPath} cover={status?.cover} onSetCover={setCover} onClearCover={clearCover} onApplyCover={applyCover} onClose={() => setFilesOpen(false)} />;
    }
    if (selection?.kind === "commit") {
      if (!commitDetail || commitDetail.id !== selection.id) {
        if (commitLoadError?.id !== selection.id) return (
          <section className="panel-section" aria-label="葉の詳細を読み込み中" aria-busy="true">
            <div className="panel-heading">
              <p className="muted">読み込み中…</p>
              <button className="icon-button" onClick={closeSelection} aria-label="詳細を閉じる">×</button>
            </div>
          </section>
        );
        return (
          <section className="panel-section" aria-label="葉の読み込みエラー">
            <div className="panel-heading">
              <h3>葉の詳細を読み込めませんでした</h3>
              <button className="icon-button" onClick={closeSelection} aria-label="詳細を閉じる">×</button>
            </div>
            <p role="alert" className="panel-copy">{commitLoadError.error.message}</p>
            <button className="button primary" onClick={() => selectCommit(selection.id)} disabled={busy}>再試行</button>
          </section>
        );
      }
      return <CommitPanel projectDir={projectDir} program={sproutProgram} detail={commitDetail} branches={graph.branches} deletedBranches={graph.deleted_branches} tags={graph.tags} current={currentCommit === commitDetail.id} unsavedCount={changes.length} busy={busy} onGo={goTo} onGrow={growBranch} onSetThumbnail={setCommitThumbnail} onUpdateMessage={updateCommitMessage} onCompare={(source) => setComparison({ source, target: "" })} onRestoreFiles={restoreFiles} onExport={exportFiles} onDelete={(commitId) => void deleteCommit(commitId)} onClose={closeSelection} previews={{
        metadata: (id, data) => previewOperation(commitDetail.id, async () => {
          await runSprout(projectDir, ["leaf", "preview", "edit", commitDetail.id, id,
            `--name=${data.display_name}`, `--description=${data.description}`], sproutProgram);
          return true;
        }),
        add: () => choosePreviews(commitDetail.id),
        paste: (files) => pastePreviews(commitDetail.id, files),
        pastePaths: () => pasteNativePreviews(commitDetail.id),
        replace: (id) => choosePreviews(commitDetail.id, id),
        remove: (id) => deletePreview(commitDetail.id, id),
        export: (id, name) => exportPreview(commitDetail.id, id, name),
        order: (ids) => orderPreviews(commitDetail.id, ids),
      }} annotations={{
        onSaveNote: saveNote,
        onAddLabel: addLabel,
        onRemoveLabel: removeLabel,
        onCreateTag: createTag,
        onSetTagComment: (name, comment) => setTagComment(commitDetail.id, name, comment),
        onDeleteTag: (name) => deleteTag(commitDetail.id, name),
      }} />;
    }
    if (selectedBranch) {
      return <BranchPanel branch={selectedBranch} tip={graph.commits.find((commit) => commit.id === selectedBranch.commit_id)} busy={busy} onRename={renameBranch} onSetComment={setBranchComment} onDelete={deleteBranch} onOpenTip={selectCommit} onClose={closeSelection} />;
    }
    if (selectedBud) {
      const base = graph.commits.find((commit) => commit.id === selectedBud.base_commit_id);
      return <BudPanel bud={selectedBud} baseMessage={base?.message ?? null} branches={graph.branches} deletedBranches={graph.deleted_branches} busy={busy} onRestore={restoreBud} onDrop={dropBud} onRename={renameBud} onClose={closeSelection} />;
    }
    return <SavePanel changes={changes} growsBranch={status?.at_branch_tip === false} coverPath={status?.cover?.path} message={commitMessage} thumbnailPath={thumbnailPath} thumbnailPasted={Boolean(thumbnailPath) && pastedThumbnail.current === thumbnailPath} busy={busy} onMessageChange={setCommitMessage} onChooseThumbnail={chooseThumbnail} onClearThumbnail={() => replaceThumbnailPath("")} onSave={commitChanges} onKeepAsBud={keepAsBud} onRevert={revertUnsaved} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 22V11" />
            <path className="leaf-a" d="M12 13C12 8 8 6 4 6c0 4 3 7 8 7z" />
            <path className="leaf-b" d="M12 11c0-4 3-7 8-7 0 4-3 7-8 7z" />
          </svg>
          <h1>Sprout</h1>
        </div>
        <ProjectMenu
          projects={recentProjects}
          current={projectDir}
          busy={busy}
          onOpen={openProject}
          onForget={forgetRecentProject}
          onChoose={chooseProject}
        />
        {status && <button className={`chip chip-button${selection?.kind === "branch" && selection.id === status.branch_id ? " pressed" : ""}`} aria-label="現在のブランチ" title="ブランチの詳細を開く" onClick={() => selectBranch(status.branch_id)} disabled={busy}>{status.branch}</button>}
        {status && (
          <span className={`chip${changes.length ? " unsaved" : ""}`} aria-label="保存状態">
            {changes.length ? `未保存の変更 ${changes.length}` : "保存済み"}
          </span>
        )}
        <span className="spacer" />
        {status && (
          <>
            <button className="button ghost" onClick={refreshProject} disabled={busy}>更新</button>
            <button className={`button ghost${filesOpen ? " pressed" : ""}`} onClick={() => { setTrashOpen(false); setMaintenanceOpen(false); setComparison(null); setFilesOpen(!filesOpen); }} aria-pressed={filesOpen} disabled={busy}>ファイル</button>
            <button className="button ghost" onClick={openTrash} disabled={busy}>ゴミ箱</button>
            <button className={`button ghost${maintenanceOpen ? " pressed" : ""}`} onClick={openMaintenance} aria-pressed={maintenanceOpen} disabled={busy}>保守</button>
            <button className="button primary" onClick={openSaveForm} disabled={busy}>保存</button>
          </>
        )}
        <button className={`icon-button${settingsOpen ? " pressed" : ""}`} onClick={() => setSettingsOpen(!settingsOpen)} aria-label="設定" aria-pressed={settingsOpen} disabled={busy}>⚙</button>
      </header>

      {busy && <div className="loading-bar" aria-label="操作中" />}
      {hoverDestination && <div className={`drop-indicator ${hoverDestination.kind}`} role="status">{hoverDestination.message}</div>}
      {notice && <div className={`notice ${notice.kind}`} role="alert"><div><strong>{notice.kind === "error" ? "操作を完了できませんでした" : notice.kind === "warning" ? "確認してください" : "完了"}</strong><p>{notice.message}</p>{noticePath && <p className="notice-path">{`対象: ${noticePath}`}</p>}</div><div className="notice-actions">{notice.code === "repository_locked" && projectDir && <button onClick={refreshProject}>再試行</button>}<button aria-label="通知を閉じる" onClick={() => setNotice(null)}>×</button></div></div>}

      {settingsOpen && <section className="settings-panel" aria-label="CLI設定"><div><h2>Sprout CLI</h2><p>空欄の場合はPATH上のsproutを使用します。</p></div><input value={sproutProgram} onChange={(event) => setSproutProgram(event.currentTarget.value)} placeholder="例: C:\\Tools\\sprout.exe" aria-label="Sprout CLIのパス" disabled={busy} /><button className="button secondary" onClick={saveCliSetting} disabled={busy}>保存</button></section>}

      {!projectDir && (
        <main className="welcome">
          <div className="welcome-card">
            <p className="eyebrow">はじめに</p>
            <h2>制作データの芽を、静かに育てる。</h2>
            <p>フォルダを選ぶと、保存した状態を葉として並べ、行き来できます。</p>
            <button className="button primary large" onClick={chooseProject} disabled={busy}>プロジェクトを選択</button>
            <h3>最近使ったプロジェクト</h3>
            <RecentProjectList projects={recentProjects} current={projectDir} busy={busy} onOpen={openProject} onForget={forgetRecentProject} />
          </div>
        </main>
      )}

      {projectDir && initCandidate && (
        <main className="welcome">
          <div className="welcome-card">
            <p className="eyebrow">未初期化</p>
            <h2>このフォルダはまだSproutプロジェクトではありません</h2>
            <p className="path-label">{initCandidate}</p>
            <p>.sprout管理情報を作成します。既存ファイルの内容は変更しません。</p>
            <div className="action-row">
              <button className="button primary" onClick={initializeProject} disabled={busy}>このフォルダを初期化</button>
              <button className="button secondary" onClick={chooseProject} disabled={busy}>別のフォルダを選ぶ</button>
            </div>
          </div>
        </main>
      )}

      {projectDir && !status && !initCandidate && !busy && (
        <main className="welcome">
          <div className="welcome-card">
            <p className="eyebrow">開けませんでした</p>
            <h2>このプロジェクトを開けませんでした</h2>
            <p className="path-label">{projectDir}</p>
            <p>上の通知で理由を確認し、CLI設定を見直すか、別のフォルダを選んでください。</p>
            <div className="action-row">
              <button className="button primary" onClick={() => openProject(projectDir)}>もう一度開く</button>
              <button className="button secondary" onClick={chooseProject}>別のフォルダを選ぶ</button>
            </div>
            <h3>最近使ったプロジェクト</h3>
            <RecentProjectList projects={recentProjects} current={projectDir} busy={busy} onOpen={openProject} onForget={forgetRecentProject} />
          </div>
        </main>
      )}

      {projectDir && status && !initCandidate && (
        <main className="workspace" style={{ "--panel-width": `${panelWidth}px` } as CSSProperties}>
          <section className="map-area" aria-label="マップ">
            <h2 className="sr-only">{projectName(projectDir)}</h2>
            <SproutMap graph={graph} selection={selection} unsavedCount={changes.length} projectDir={projectDir} sproutProgram={sproutProgram} onSelect={selectCommit} onSelectBud={selectBud} onSelectBranch={selectBranch} onSelectUnsaved={selectUnsaved} />
          </section>
          <PanelSplitter
            width={panelWidth}
            onResize={setPanelWidth}
            onCommit={(width) => void savePanelWidth(width).catch((error) => setNotice({ ...normalizeCliError(error), kind: "error" }))}
          />
          <aside className="detail-panel">{sidePanel()}</aside>
        </main>
      )}
    </div>
  );
}

export default App;
