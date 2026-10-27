import { useEffect, useRef, useState } from "react";
import { confirm as confirmDialog, open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import BudPanel from "./components/BudPanel";
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
  type CommitDetail,
  type CommitGraph,
  type CommitResult,
  type GoResult,
  type PathOperationResult,
  type SproutCliError,
  type SproutStatus,
} from "./lib/sprout";
import { loadSettings, nextRecentProjects, removeRecentProject, saveSettings } from "./lib/settings";

type Notice = SproutCliError & { kind: "error" | "success" | "warning" };

const emptyGraph: CommitGraph = { commits: [], branches: [], tags: [] };
const UNCHANGED_NOTE = "作業フォルダは変更していません。";

function shortId(value: string | null): string {
  return value ? value.slice(0, 12) : "-";
}

function currentCommitOf(graph: CommitGraph): string | null {
  if (graph.current_commit !== undefined) return graph.current_commit ?? null;
  return graph.branches.find((branch) => branch.current)?.commit_id ?? null;
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
  const [filesOpen, setFilesOpen] = useState(false);
  const [recentProjects, setRecentProjects] = useState<string[]>([]);
  const [sproutProgram, setSproutProgram] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [initCandidate, setInitCandidate] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [commitMessage, setCommitMessage] = useState("");
  const [thumbnailPath, setThumbnailPath] = useState("");
  const operationActive = useRef(false);

  useEffect(() => {
    void loadSettings()
      .then((settings) => {
        setRecentProjects(settings.recentProjects);
        setSproutProgram(settings.sproutProgram);
      })
      .catch((error) => setNotice({ ...normalizeCliError(error), kind: "error" }));
  }, []);

  async function execute(operation: () => Promise<void>) {
    if (operationActive.current) return;
    operationActive.current = true;
    setBusy(true);
    setNotice(null);
    try {
      await operation();
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
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
      if (current?.kind === "bud" && !(nextGraph.buds ?? []).some((bud) => bud.id === current.id)) return null;
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
          trackPaths(event.payload.paths);
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
  }, [projectDir, sproutProgram]);

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

  function chooseThumbnail() {
    if (operationActive.current) return;
    void open({
      multiple: false,
      title: "コミットのサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected === "string") setThumbnailPath(selected);
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
      setThumbnailPath("");
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
    setSelection({ kind: "commit", id: commitId });
    setFilesOpen(false);
    void execute(async () => {
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
    });
  }

  function selectBud(budId: string) {
    setSelection({ kind: "bud", id: budId });
    setFilesOpen(false);
  }

  function selectUnsaved() {
    setSelection({ kind: "unsaved" });
    setFilesOpen(false);
  }

  function closeSelection() {
    setSelection(null);
    setCommitDetail(null);
  }

  function setCommitThumbnail(commitId: string) {
    if (!projectDir || operationActive.current) return;
    void open({
      multiple: false,
      title: "コミットのサムネイルを選択",
      filters: [{ name: "画像", extensions: ["png", "jpg", "jpeg", "webp"] }],
    }).then((selected) => {
      if (typeof selected !== "string") return;
      void execute(async () => {
        await runSprout(projectDir, ["thumbnail", commitId, selected], sproutProgram);
        await fetchWorkspace(projectDir);
        setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
        setNotice({ code: "thumbnail_saved", message: `${shortId(commitId)} のサムネイルを保存しました`, details: { commit_id: commitId }, kind: "success" });
      });
    });
  }

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
      current_commit: result.current_commit,
      at_branch_tip: result.at_branch_tip,
      changes: result.changes,
    });
    setGraph((current) => ({
      ...current,
      current_commit: result.current_commit,
      at_branch_tip: result.at_branch_tip,
      branches: current.branches.map((branch) => ({ ...branch, current: branch.name === result.branch })),
      buds: result.bud ? [result.bud, ...(current.buds ?? [])] : current.buds,
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

  function exportFiles(commitId: string) {
    if (!projectDir || operationActive.current) return;
    void open({ directory: true, multiple: false, title: "書き出し先のフォルダを選択" }).then((selected) => {
      if (typeof selected !== "string") return;
      void execute(async () => {
        const result = await runSprout<{ paths: string[]; output: string }>(projectDir, ["export", commitId, "--output", selected], sproutProgram);
        setNotice({ code: "exported", message: `${result.paths.length}件のファイルを ${result.output} へ書き出しました`, details: {}, kind: "success" });
      });
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
  const currentCommit = currentCommitOf(graph);
  const selectedBud = selection?.kind === "bud" ? (graph.buds ?? []).find((bud) => bud.id === selection.id) : undefined;
  const noticePath = typeof notice?.details.path === "string" ? notice.details.path : null;

  function sidePanel() {
    if (filesOpen) {
      return <FilePanel tracked={tracked} untracked={untracked} busy={busy} onAddFiles={() => chooseTrackFiles(false)} onAddFolder={() => chooseTrackFiles(true)} onTrack={(path) => trackPaths([path])} onUntrack={untrackPath} onClose={() => setFilesOpen(false)} />;
    }
    if (selection?.kind === "commit") {
      if (!commitDetail || commitDetail.id !== selection.id) return <p className="muted">読み込み中…</p>;
      return <CommitPanel detail={commitDetail} branches={graph.branches} tags={graph.tags} current={currentCommit === commitDetail.id} unsavedCount={changes.length} busy={busy} onGo={goTo} onGrow={growBranch} onSetThumbnail={setCommitThumbnail} onUpdateMessage={updateCommitMessage} onExport={exportFiles} onClose={closeSelection} />;
    }
    if (selectedBud) {
      const base = graph.commits.find((commit) => commit.id === selectedBud.base_commit_id);
      return <BudPanel bud={selectedBud} baseMessage={base?.message ?? "最初の保存前"} busy={busy} onRestore={restoreBud} onDrop={dropBud} onClose={closeSelection} />;
    }
    return <SavePanel changes={changes} growsBranch={status?.at_branch_tip === false} message={commitMessage} thumbnailPath={thumbnailPath} busy={busy} onMessageChange={setCommitMessage} onChooseThumbnail={chooseThumbnail} onClearThumbnail={() => setThumbnailPath("")} onSave={commitChanges} />;
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
        {status && <span className="chip" aria-label="現在のブランチ">{status.branch}</span>}
        {status && (
          <span className={`chip${changes.length ? " unsaved" : ""}`} aria-label="保存状態">
            {changes.length ? `未保存の変更 ${changes.length}` : "保存済み"}
          </span>
        )}
        <span className="spacer" />
        {status && (
          <>
            <button className="button ghost" onClick={refreshProject} disabled={busy}>更新</button>
            <button className={`button ghost${filesOpen ? " pressed" : ""}`} onClick={() => setFilesOpen(!filesOpen)} aria-pressed={filesOpen} disabled={busy}>ファイル</button>
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

      {projectDir && status && !initCandidate && (
        <main className="workspace">
          <section className="map-area" aria-label="スナップショット">
            <h2 className="sr-only">{projectName(projectDir)}</h2>
            <SproutMap graph={graph} selection={selection} unsavedCount={changes.length} projectDir={projectDir} sproutProgram={sproutProgram} onSelect={selectCommit} onSelectBud={selectBud} onSelectUnsaved={selectUnsaved} />
          </section>
          <aside className="detail-panel">{sidePanel()}</aside>
        </main>
      )}
    </div>
  );
}

export default App;
