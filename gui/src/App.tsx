import { useEffect, useRef, useState } from "react";
import { confirm as confirmDialog, open, save } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import BranchPanel from "./components/BranchPanel";
import BudPanel from "./components/BudPanel";
import ComparePanel from "./components/ComparePanel";
import CommitPanel from "./components/CommitPanel";
import FilePanel from "./components/FilePanel";
import ProjectMenu, { RecentProjectList, projectName } from "./components/ProjectMenu";
import SavePanel from "./components/SavePanel";
import SproutMap, { type MapSelection } from "./components/SproutMap";
import "./App.css";
import {
  isUninitializedProject,
  normalizeCliError,
  runSprout,
  type Bud,
  type CommitDeletion,
  type CommitDetail,
  type CommitGraph,
  type CommitResult,
  type GoResult,
  type PathOperationResult,
  type SproutCliError,
  type SproutStatus,
} from "./lib/sprout";
import { loadSettings, nextRecentProjects, removeRecentProject, saveSettings } from "./lib/settings";
import { clipboardImage, discardPastedThumbnail, savePastedPreview, readClipboardFiles, savePastedThumbnail, thumbnailImageProblem } from "./lib/clipboard";

type Notice = SproutCliError & { kind: "error" | "success" | "warning" };

const emptyGraph: CommitGraph = { current_commit: null, at_branch_tip: true, commits: [], branches: [], tags: [], buds: [] };
const UNCHANGED_NOTE = "作業フォルダは変更していません。";

function shortId(value: string | null): string {
  return value ? value.slice(0, 12) : "-";
}

/** Describe a delete-commit dry run so the confirmation lists every reference it moves. */
function deletionSummary(preview: CommitDeletion): string {
  const parent = preview.parent_id ? `親の芽（${shortId(preview.parent_id)}）` : "コミットなし";
  const lines = [`スナップショット「${preview.commit.message}」（${shortId(preview.commit.id)}）を削除します。元に戻せません。`];
  if (preview.moved_branches.length > 0) {
    lines.push(`ブランチ ${preview.moved_branches.map((branch) => branch.name).join(", ")} は${parent}へ移ります。`);
  }
  if (preview.moved_current) lines.push(`いまここも${parent}へ移ります。作業ファイルは変わらず、未保存の変更として残ります。`);
  if (preview.reconnected_children.length > 0) {
    lines.push(`子の芽 ${preview.reconnected_children.length}件は${preview.parent_id ? "親の芽へつなぎ直されます" : "根になります"}。`);
  }
  if (preview.rebased_buds.length > 0) lines.push(`つぼみ ${preview.rebased_buds.length}件の起点は${parent}へ付け替わります。`);
  if (preview.reclaimable_objects.length > 0) {
    lines.push(`${preview.reclaimable_objects.length}個のオブジェクト（${preview.reclaimable_bytes} bytes）が sprout gc で回収できるようになります。`);
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
  const [selection, setSelection] = useState<MapSelection>(null);
  const [comparison, setComparison] = useState<{ source: string; target: string } | null>(null);
  useEffect(() => { setComparison(null); }, [projectDir]);
  const [filesOpen, setFilesOpen] = useState(false);
  const [recentProjects, setRecentProjects] = useState<string[]>([]);
  const [sproutProgram, setSproutProgram] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [initCandidate, setInitCandidate] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [thumbnailPath, setThumbnailPath] = useState("");
  const pastedThumbnail = useRef("");
  const pasteHandler = useRef<(event: ClipboardEvent) => void>(() => {});
  const operationActive = useRef(false);

  useEffect(() => {
    void loadSettings()
      .then((settings) => {
        setRecentProjects(settings.recentProjects);
        setSproutProgram(settings.sproutProgram);
      })
      .catch((error) => setNotice({ ...normalizeCliError(error), kind: "error" }));
  }, []);

  /** Run one operation at a time; resolves true only when it completed without an error. */
  async function execute(operation: () => Promise<void>): Promise<boolean> {
    if (operationActive.current) return false;
    operationActive.current = true;
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

  async function fetchWorkspace(path: string) {
    const nextStatus = await runSprout<SproutStatus>(path, ["status", "--tracked", "--untracked"], sproutProgram);
    const nextGraph = await runSprout<CommitGraph>(path, ["tree"], sproutProgram);
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
      .onDragDropEvent((event) => {
        if (event.payload.type === "drop" && projectDir && !operationActive.current) {
          if (selection?.kind === "commit" && !filesOpen && !comparison) addPreviews(selection.id, event.payload.paths);
          else trackPaths(event.payload.paths);
        }
      })
      .then((stop) => {
        if (disposed) stop();
        else unlisten = stop;
      })
      .catch(() => undefined);
    return () => {
      disposed = true;
      unlisten?.();
    };
  }, [projectDir, sproutProgram, selection, filesOpen, comparison]);

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
      const result = await runSprout<PathOperationResult>(projectDir, ["track", ...paths], sproutProgram);
      await fetchWorkspace(projectDir);
      setNotice({
        code: result.paths.length ? "paths_tracked" : "no_paths_tracked",
        message: result.paths.length ? `${result.paths.length}件を追跡対象に追加しました` : "追跡対象に追加されたファイルはありません",
        details: { paths: result.paths },
        kind: result.paths.length ? "success" : "warning",
      });
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
      const result = await runSprout<PathOperationResult>(projectDir, ["untrack", path], sproutProgram);
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
      title: "コミットのサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected === "string") replaceThumbnailPath(selected);
    });
  }

  function commitChanges() {
    if (!projectDir) return;
    const message = commitMessage.trim();
    if (!message) {
      setNotice({ code: "message_required", message: "コミットメッセージを入力してください", details: {}, kind: "warning" });
      return;
    }
    void execute(async () => {
      const args = ["commit", "-m", message];
      if (thumbnailPath) args.push("--thumbnail", thumbnailPath);
      const result = await runSprout<CommitResult>(projectDir, args, sproutProgram);
      setCommitMessage("");
      replaceThumbnailPath("");
      await fetchWorkspace(projectDir);
      setSelection(null);
      setNotice({
        code: "committed",
        message: result.created_branch
          ? `新しい枝 ${result.branch} を作り、${shortId(result.id)} を保存しました`
          : `コミット ${shortId(result.id)} を作成しました`,
        details: { id: result.id },
        kind: "success",
      });
    });
  }

  function selectCommit(commitId: string) {
    if (!projectDir) return;
    if (operationActive.current) return;
    if (comparison) { setComparison({ ...comparison, target: commitId }); return; }
    setSelection({ kind: "commit", id: commitId });
    setFilesOpen(false);
    void execute(async () => {
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
    });
  }

  function selectBud(budId: string) {
    setComparison(null);
    setSelection({ kind: "bud", id: budId });
    setFilesOpen(false);
  }

  function selectBranch(branchId: string) {
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
    return editBranch(branchId, (current) => ["branch", current, "--rename", name], (current) => `ブランチ ${current} の名前を ${name} に変更しました`);
  }

  function setBranchComment(branchId: string, comment: string) {
    return editBranch(branchId, (current) => ["branch", current, "--set-comment", comment], (current) => `ブランチ ${current} のコメントを変更しました`);
  }

  function deleteBranch(branchId: string) {
    const branch = graph.branches.find((item) => item.id === branchId);
    if (!projectDir || !branch || operationActive.current) return;
    void confirmDialog(`ブランチ ${branch.name} を削除します。この枝のスナップショットは削除されず、「削除済みブランチ由来」として残ります。続行しますか？`, {
      title: "ブランチを削除",
      kind: "warning",
      okLabel: "削除",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (accepted) void editBranch(branchId, (current) => ["branch", "--delete", current], (current) => `ブランチ ${current} を削除しました`);
    });
  }

  function selectUnsaved() {
    setComparison(null);
    setSelection({ kind: "unsaved" });
    setFilesOpen(false);
  }

  function closeSelection() {
    setSelection(null);
    setCommitDetail(null);
  }

  /** Run an edit of one snapshot's annotations, then refresh the map and its detail. */
  function editCommit(commitId: string, args: string[], message: string): Promise<boolean> {
    if (!projectDir) return Promise.resolve(false);
    return execute(async () => {
      await runSprout(projectDir, args, sproutProgram);
      await fetchWorkspace(projectDir);
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
      setNotice({ code: "annotation_updated", message, details: { commit_id: commitId }, kind: "success" });
    });
  }

  function saveNote(commitId: string, note: string) {
    const deleting = !note.trim();
    return editCommit(
      commitId,
      deleting ? ["note", commitId, "--delete"] : ["note", commitId, note],
      deleting ? `${shortId(commitId)} のメモを削除しました` : `${shortId(commitId)} のメモを保存しました`,
    );
  }

  function addLabel(commitId: string, label: string) {
    return editCommit(commitId, ["label", commitId, label], `ラベル「${label.trim()}」を追加しました`);
  }

  function removeLabel(commitId: string, label: string) {
    return editCommit(commitId, ["label", commitId, "--delete", label], `ラベル「${label}」を外しました`);
  }

  function createTag(commitId: string, name: string, comment: string) {
    const args = ["tag", name, commitId];
    if (comment.trim()) args.push("--comment", comment);
    return editCommit(commitId, args, `タグ ${name} を付けました`);
  }

  function setTagComment(commitId: string, name: string, comment: string) {
    return editCommit(commitId, ["tag", name, "--set-comment", comment], `タグ ${name} のコメントを変更しました`);
  }

  function deleteTag(commitId: string, name: string) {
    if (!projectDir || operationActive.current) return;
    void confirmDialog(`タグ ${name} を削除します。スナップショットは削除されません。続行しますか？`, {
      title: "タグを削除",
      kind: "warning",
      okLabel: "削除",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (accepted) void editCommit(commitId, ["tag", "--delete", name], `タグ ${name} を削除しました`);
    });
  }

  function setCommitThumbnail(commitId: string) {
    if (!projectDir || operationActive.current) return;
    void open({
      multiple: false,
      title: "コミットのサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected !== "string") return;
      void execute(() => applyCommitThumbnail(commitId, selected));
    });
  }

  async function applyCommitThumbnail(commitId: string, path: string) {
    await runSprout(projectDir, ["thumbnail", commitId, path], sproutProgram);
    await fetchWorkspace(projectDir);
    setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
    setNotice({ code: "thumbnail_saved", message: `${shortId(commitId)} のサムネイルを保存しました`, details: { commit_id: commitId }, kind: "success" });
  }

  /** Ctrl+V with an image sets the thumbnail of the open save form or commit; text pastes pass through. */
  function pasteThumbnail(event: ClipboardEvent) {
    if (event.defaultPrevented || comparison || !projectDir || !status || filesOpen || operationActive.current) return;
    const commitId = selection?.kind === "commit" && commitDetail?.id === selection.id ? commitDetail.id : null;
    const saveForm = selection === null || selection.kind === "unsaved";
    if (!commitId && !saveForm) return;
    const image = clipboardImage(event.clipboardData);
    if (!image) return;
    event.preventDefault();
    const problem = thumbnailImageProblem(image);
    if (problem) {
      setNotice({ code: "unsupported_clipboard_image", message: problem, details: { media_type: image.type, size: image.size }, kind: "warning" });
      return;
    }
    void execute(async () => {
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

  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => pasteHandler.current(event);
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  function updateCommitMessage(commitId: string, message: string) {
    if (!projectDir) return;
    const normalized = message.trim();
    if (!normalized) {
      setNotice({ code: "message_required", message: "コミットメッセージを入力してください", details: {}, kind: "warning" });
      return;
    }
    void execute(async () => {
      await runSprout(projectDir, ["message", commitId, normalized], sproutProgram);
      await fetchWorkspace(projectDir);
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
      setNotice({ code: "message_updated", message: `${shortId(commitId)} のコミットメッセージを変更しました`, details: { commit_id: commitId }, kind: "success" });
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
      try {
        await runSprout<GoResult>(projectDir, ["go", commitId], sproutProgram);
        await runSprout(projectDir, ["branch", name, commitId, "--switch"], sproutProgram);
      } catch (error) {
        await fetchWorkspace(projectDir);
        throw normalizeCliError(error);
      }
      await fetchWorkspace(projectDir);
      setNotice({ code: "branch_created", message: `${shortId(commitId)} から枝 ${name} を伸ばしました`, details: { name }, kind: "success" });
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
      const result = await runSprout<{ paths: string[]; output: string }>(projectDir, ["export", commitId, ...fileArguments(paths), "--output", selected], sproutProgram);
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
      const args = ["restore", commitId, ...fileArguments(paths)];
      try {
        await runSprout(projectDir, args, sproutProgram);
      } catch (cause) {
        const error = normalizeCliError(cause);
        if (error.code !== "uncommitted_changes" || error.details.can_discard !== true) throw unchangedError(cause);
        const discard = await confirmDialog(`対象に未保存の変更があります。\n${targets}\nこの対象の未保存変更を破棄して戻しますか？破棄した変更は元に戻せません。`, {
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
    const args = ["preview", replacement ? "replace" : "add", commitId, ...(replacement ? [replacement] : []), ...fileArguments(paths)];
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
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
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
      if (!await confirmDialog("このプレビューを削除します。続行しますか？", { title: "プレビューを削除", kind: "warning", okLabel: "削除", cancelLabel: "キャンセル" })) return false;
      await runSprout(projectDir, ["preview", "delete", commitId, id], sproutProgram);
      return true;
    });
  }

  function exportPreview(commitId: string, id: string, name: string) {
    void execute(async () => {
      const output = await save({ title: "プレビューを取り出す", defaultPath: name });
      if (!output) return;
      await runSprout(projectDir, ["preview", "export", commitId, id, "--output", output], sproutProgram);
      setNotice({ code: "preview_exported", message: `プレビューを ${output} へ取り出しました`, details: {}, kind: "success" });
    });
  }

  function orderPreviews(commitId: string, ids: string[]) {
    previewOperation(commitId, async () => {
      await runSprout(projectDir, ["preview", "order", commitId, ...ids], sproutProgram);
      return true;
    });
  }

  function restoreBud(budId: string) {
    if (!projectDir) return;
    void execute(async () => {
      let result: { restored: Bud; saved: Bud | null };
      try {
        result = await runSprout(projectDir, ["bud", "--restore", budId], sproutProgram);
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
    void confirmDialog("このつぼみを捨てます。元に戻せません。続行しますか？", {
      title: "つぼみを捨てる",
      kind: "warning",
      okLabel: "捨てる",
      cancelLabel: "キャンセル",
    }).then((accepted) => {
      if (!accepted) return;
      void execute(async () => {
        await runSprout(projectDir, ["bud", "--drop", budId, "--yes"], sproutProgram);
        await fetchWorkspace(projectDir);
        setSelection(null);
        setNotice({ code: "bud_dropped", message: "つぼみを捨てました", details: {}, kind: "success" });
      });
    });
  }

  function openSaveForm() {
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
      const preview = await runSprout<CommitDeletion>(projectDir, ["delete-commit", commitId, "--dry-run"], sproutProgram);
      const accepted = await confirmDialog(deletionSummary(preview), {
        title: "この葉を削除",
        kind: "warning",
        okLabel: "削除",
        cancelLabel: "キャンセル",
      });
      if (!accepted) return;
      await runSprout<CommitDeletion>(projectDir, ["delete-commit", commitId, "--yes"], sproutProgram);
      await fetchWorkspace(projectDir);
      closeSelection();
      setNotice({ code: "commit_deleted", message: `スナップショット ${shortId(commitId)} を削除しました`, details: { commit_id: commitId }, kind: "success" });
    });
  }

  const selectedBud = selection?.kind === "bud" ? graph.buds.find((bud) => bud.id === selection.id) : undefined;
  const selectedBranch = selection?.kind === "branch" ? graph.branches.find((branch) => branch.id === selection.id) : undefined;
  const noticePath = typeof notice?.details.path === "string" ? notice.details.path : null;

  function sidePanel() {
    if (comparison) return <ComparePanel projectDir={projectDir} program={sproutProgram} commits={graph.commits} source={comparison.source} target={comparison.target} busy={busy} onChange={(source, target) => setComparison({ source, target })} onClose={() => setComparison(null)} />;
    if (filesOpen) {
      return <FilePanel tracked={tracked} untracked={untracked} busy={busy} onAddFiles={() => chooseTrackFiles(false)} onAddFolder={() => chooseTrackFiles(true)} onTrack={(path) => trackPaths([path])} onUntrack={untrackPath} onClose={() => setFilesOpen(false)} />;
    }
    if (selection?.kind === "commit") {
      if (!commitDetail || commitDetail.id !== selection.id) return <p className="muted">読み込み中…</p>;
      return <CommitPanel projectDir={projectDir} program={sproutProgram} detail={commitDetail} branches={graph.branches} tags={graph.tags} current={currentCommit === commitDetail.id} unsavedCount={changes.length} busy={busy} onGo={goTo} onGrow={growBranch} onSetThumbnail={setCommitThumbnail} onUpdateMessage={updateCommitMessage} onCompare={(source) => setComparison({ source, target: "" })} onRestoreFiles={restoreFiles} onExport={exportFiles} onDelete={(commitId) => void deleteCommit(commitId)} onClose={closeSelection} previews={{
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
      return <BudPanel bud={selectedBud} baseMessage={base?.message ?? null} branches={graph.branches} busy={busy} onRestore={restoreBud} onDrop={dropBud} onClose={closeSelection} />;
    }
    return <SavePanel changes={changes} growsBranch={status?.at_branch_tip === false} message={commitMessage} thumbnailPath={thumbnailPath} thumbnailPasted={Boolean(thumbnailPath) && pastedThumbnail.current === thumbnailPath} busy={busy} onMessageChange={setCommitMessage} onChooseThumbnail={chooseThumbnail} onClearThumbnail={() => replaceThumbnailPath("")} onSave={commitChanges} />;
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
            <button className={`button ghost${filesOpen ? " pressed" : ""}`} onClick={() => { setComparison(null); setFilesOpen(!filesOpen); }} aria-pressed={filesOpen} disabled={busy}>ファイル</button>
            <button className="button primary" onClick={openSaveForm} disabled={busy}>保存</button>
          </>
        )}
        <button className={`icon-button${settingsOpen ? " pressed" : ""}`} onClick={() => setSettingsOpen(!settingsOpen)} aria-label="設定" aria-pressed={settingsOpen} disabled={busy}>⚙</button>
      </header>

      {busy && <div className="loading-bar" aria-label="操作中" />}
      {notice && <div className={`notice ${notice.kind}`} role="alert"><div><strong>{notice.kind === "error" ? "操作を完了できませんでした" : notice.kind === "warning" ? "確認してください" : "完了"}</strong><p>{notice.message}</p>{noticePath && <p className="notice-path">{`対象: ${noticePath}`}</p>}</div><div className="notice-actions">{notice.code === "repository_locked" && projectDir && <button onClick={refreshProject}>再試行</button>}<button aria-label="通知を閉じる" onClick={() => setNotice(null)}>×</button></div></div>}

      {settingsOpen && <section className="settings-panel" aria-label="CLI設定"><div><h2>Sprout CLI</h2><p>空欄の場合はPATH上のsproutを使用します。</p></div><input value={sproutProgram} onChange={(event) => setSproutProgram(event.currentTarget.value)} placeholder="例: C:\\Tools\\sprout.exe" aria-label="Sprout CLIのパス" disabled={busy} /><button className="button secondary" onClick={saveCliSetting} disabled={busy}>保存</button></section>}

      {!projectDir && (
        <main className="welcome">
          <div className="welcome-card">
            <p className="eyebrow">WELCOME TO SPROUT</p>
            <h2>制作データの芽を、静かに育てる。</h2>
            <p>フォルダを選ぶと、スナップショットを芽のように並べて行き来できます。</p>
            <button className="button primary large" onClick={chooseProject} disabled={busy}>プロジェクトを選択</button>
            <h3>最近使ったプロジェクト</h3>
            <RecentProjectList projects={recentProjects} current={projectDir} busy={busy} onOpen={openProject} onForget={forgetRecentProject} />
          </div>
        </main>
      )}

      {projectDir && initCandidate && (
        <main className="welcome">
          <div className="welcome-card">
            <p className="eyebrow">NOT INITIALIZED</p>
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
            <p className="eyebrow">COULD NOT OPEN</p>
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
        <main className="workspace">
          <section className="map-area" aria-label="スナップショット">
            <h2 className="sr-only">{projectName(projectDir)}</h2>
            <SproutMap graph={graph} selection={selection} unsavedCount={changes.length} projectDir={projectDir} sproutProgram={sproutProgram} onSelect={selectCommit} onSelectBud={selectBud} onSelectBranch={selectBranch} onSelectUnsaved={selectUnsaved} />
          </section>
          <aside className="detail-panel">{sidePanel()}</aside>
        </main>
      )}
    </div>
  );
}

export default App;
