import { useEffect, useRef, useState } from "react";
import { confirm as confirmDialog, open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import CommitTree from "./components/CommitTree";
import "./App.css";
import {
  canDiscardChanges,
  isUninitializedProject,
  normalizeCliError,
  runSprout,
  type BranchInfo,
  type CommitDetail,
  type CommitGraph,
  type CommitLogEntry,
  type CommitResult,
  type PathOperationResult,
  type SproutCliError,
  type SproutStatus,
} from "./lib/sprout";
import { loadSettings, nextRecentProjects, removeRecentProject, saveSettings } from "./lib/settings";

type Notice = SproutCliError & { kind: "error" | "success" | "warning" };
type WorkspaceTab = "status" | "tree" | "commit" | "history" | "branches";

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
};

const tabs: Array<{ id: WorkspaceTab; label: string }> = [
  { id: "status", label: "ステータス" },
  { id: "tree", label: "ツリー" },
  { id: "commit", label: "コミット" },
  { id: "history", label: "履歴" },
  { id: "branches", label: "ブランチ" },
];

function projectName(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

function shortId(value: string | null): string {
  return value ? value.slice(0, 12) : "-";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ja-JP");
}

function App() {
  const [projectDir, setProjectDir] = useState("");
  const [status, setStatus] = useState<SproutStatus | null>(null);
  const [history, setHistory] = useState<CommitLogEntry[]>([]);
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [graph, setGraph] = useState<CommitGraph>({ commits: [], branches: [], tags: [] });
  const [commitDetail, setCommitDetail] = useState<CommitDetail | null>(null);
  const [recentProjects, setRecentProjects] = useState<string[]>([]);
  const [sproutProgram, setSproutProgram] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [initCandidate, setInitCandidate] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("status");
  const [commitMessage, setCommitMessage] = useState("");
  const [thumbnailPath, setThumbnailPath] = useState("");
  const [branchName, setBranchName] = useState("");
  const [branchComment, setBranchComment] = useState("");
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
    const nextStatus = await runSprout<SproutStatus>(
      path,
      ["status", "--tracked", "--untracked"],
      sproutProgram,
    );
    const [nextHistory, nextBranches, nextGraph] = await Promise.all([
      runSprout<CommitLogEntry[]>(path, ["log"], sproutProgram),
      runSprout<BranchInfo[]>(path, ["branch"], sproutProgram),
      runSprout<CommitGraph>(path, ["tree"], sproutProgram),
    ]);
    setProjectDir(path);
    setStatus(nextStatus);
    setHistory(nextHistory);
    setBranches(nextBranches);
    setGraph(nextGraph);
    if (commitDetail && !nextHistory.some((entry) => entry.id === commitDetail.id)) {
      setCommitDetail(null);
    }
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

  function openProject(path: string) {
    void execute(async () => {
      setInitCandidate("");
      try {
        await fetchWorkspace(path);
        await rememberProject(path);
      } catch (error) {
        const cliError = normalizeCliError(error);
        setStatus(null);
        setProjectDir(path);
        if (isUninitializedProject(cliError)) setInitCandidate(path);
        if (cliError.code === "sprout_not_found") setSettingsOpen(true);
        throw cliError;
      }
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

  function chooseProject() {
    void execute(async () => {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Sproutプロジェクトを選択",
      });
      if (typeof selected !== "string") return;
      setInitCandidate("");
      try {
        await fetchWorkspace(selected);
        await rememberProject(selected);
      } catch (error) {
        const cliError = normalizeCliError(error);
        setStatus(null);
        setProjectDir(selected);
        if (isUninitializedProject(cliError)) setInitCandidate(selected);
        if (cliError.code === "sprout_not_found") setSettingsOpen(true);
        throw cliError;
      }
    });
  }

  function initializeProject() {
    if (!initCandidate) return;
    void execute(async () => {
      await runSprout(initCandidate, ["init", "."], sproutProgram);
      await fetchWorkspace(initCandidate);
      await rememberProject(initCandidate);
      setInitCandidate("");
      setNotice({
        code: "initialized",
        message: "Sproutプロジェクトを初期化しました",
        details: {},
        kind: "success",
      });
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
      setNotice({ code: "committed", message: `コミット ${shortId(result.id)} を作成しました`, details: { id: result.id }, kind: "success" });
    });
  }

  function selectCommit(commitId: string, destination: "history" | "tree" = "history") {
    if (!projectDir) return;
    setActiveTab(destination);
    void execute(async () => {
      setCommitDetail(await runSprout<CommitDetail>(projectDir, ["show", commitId], sproutProgram));
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

  async function runWithDiscard<T>(args: string[], action: string): Promise<T | null> {
    try {
      return await runSprout<T>(projectDir, args, sproutProgram);
    } catch (error) {
      const cliError = normalizeCliError(error);
      if (!canDiscardChanges(cliError)) throw cliError;
      const accepted = await confirmDialog(
        `未保存の追跡対象ファイルの変更を破棄して${action}します。この操作は取り消せません。続行しますか？`,
        { title: "変更の破棄を確認", kind: "warning", okLabel: "破棄して続行", cancelLabel: "キャンセル" },
      );
      if (!accepted) {
        setNotice({ code: "discard_cancelled", message: `${action}をキャンセルしました`, details: {}, kind: "warning" });
        return null;
      }
      return runSprout<T>(projectDir, [...args, "--discard"], sproutProgram);
    }
  }

  function restoreCommit(commitId: string) {
    if (!projectDir) return;
    void execute(async () => {
      const result = await runWithDiscard<{ commit_id: string }>(["restore", commitId], "復元");
      if (!result) return;
      await fetchWorkspace(projectDir);
      setNotice({ code: "restored", message: `${shortId(result.commit_id)} の内容を復元しました`, details: result, kind: "success" });
    });
  }

  function createBranch() {
    if (!projectDir) return;
    const name = branchName.trim();
    if (!name) {
      setNotice({ code: "branch_name_required", message: "ブランチ名を入力してください", details: {}, kind: "warning" });
      return;
    }
    void execute(async () => {
      const args = ["branch", name];
      if (branchComment.trim()) args.push("--comment", branchComment.trim());
      await runSprout(projectDir, args, sproutProgram);
      setBranchName("");
      setBranchComment("");
      await fetchWorkspace(projectDir);
      setNotice({ code: "branch_created", message: `ブランチ ${name} を作成しました`, details: { name }, kind: "success" });
    });
  }

  function switchBranch(name: string) {
    if (!projectDir) return;
    void execute(async () => {
      const result = await runWithDiscard<{ branch: string }>(["switch", name], "ブランチ切り替え");
      if (!result) return;
      await fetchWorkspace(projectDir);
      setNotice({ code: "branch_switched", message: `${result.branch} に切り替えました`, details: result, kind: "success" });
    });
  }

  const tracked = status?.tracked ?? [];
  const untracked = status?.untracked ?? [];

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand"><div className="brand-mark" aria-hidden="true"><span /><span /></div><div><p className="eyebrow">OFFLINE SNAPSHOTS</p><h1>Sprout</h1></div></div>
        <div className="header-actions">
          <button className="button secondary" onClick={() => setSettingsOpen(!settingsOpen)} disabled={busy}>CLI設定</button>
          <button className="button primary" onClick={chooseProject} disabled={busy}>フォルダを開く</button>
        </div>
      </header>

      {notice && <div className={`notice ${notice.kind}`} role="alert"><div><strong>{notice.kind === "error" ? "操作を完了できませんでした" : notice.kind === "warning" ? "確認してください" : "完了"}</strong><p>{notice.message}</p></div><div className="notice-actions">{notice.code === "repository_locked" && projectDir && <button onClick={refreshProject}>再試行</button>}<button aria-label="通知を閉じる" onClick={() => setNotice(null)}>×</button></div></div>}

      {settingsOpen && <section className="settings-panel" aria-label="CLI設定"><div><h2>Sprout CLI</h2><p>空欄の場合はPATH上のsproutを使用します。</p></div><input value={sproutProgram} onChange={(event) => setSproutProgram(event.currentTarget.value)} placeholder="例: C:\\Tools\\sprout.exe" aria-label="Sprout CLIのパス" disabled={busy} /><button className="button secondary" onClick={saveCliSetting} disabled={busy}>保存</button></section>}

      <main className="workspace">
        <aside className="sidebar">
          <div className="sidebar-heading"><h2>最近使ったプロジェクト</h2><span>{recentProjects.length}</span></div>
          {recentProjects.length === 0 ? <p className="muted">開いたプロジェクトがここに表示されます。</p> : <nav className="recent-list" aria-label="最近使ったプロジェクト">{recentProjects.map((path) => <div className={`recent-item${path === projectDir ? " active" : ""}`} key={path}><button className="recent-project" onClick={() => openProject(path)} disabled={busy} title={path}><span>{projectName(path)}</span><small>{path}</small></button><button className="recent-remove" onClick={() => forgetRecentProject(path)} disabled={busy} aria-label={`${projectName(path)}を最近使った一覧から削除`} title="一覧から削除">×</button></div>)}</nav>}
        </aside>

        <section className="content">
          {busy && <div className="loading-bar" aria-label="操作中" />}
          {!projectDir && <div className="empty-state"><div className="empty-illustration" aria-hidden="true"><span /></div><p className="eyebrow">WELCOME TO SPROUT</p><h2>制作データの現在地を、静かに残す。</h2><p>フォルダを選ぶと、追跡、コミット、履歴、ブランチ、復元をこの画面から操作できます。</p><button className="button primary large" onClick={chooseProject} disabled={busy}>プロジェクトを選択</button></div>}

          {projectDir && initCandidate && <div className="empty-state compact"><p className="eyebrow">NOT INITIALIZED</p><h2>このフォルダはまだSproutプロジェクトではありません</h2><p className="path-label">{initCandidate}</p><p>.sprout管理情報を作成します。既存ファイルの内容は変更しません。</p><div className="action-row"><button className="button primary" onClick={initializeProject} disabled={busy}>このフォルダを初期化</button><button className="button secondary" onClick={chooseProject} disabled={busy}>別のフォルダを選ぶ</button></div></div>}

          {projectDir && status && <>
            <div className="project-heading"><div><p className="eyebrow">CURRENT PROJECT</p><h2>{projectName(projectDir)}</h2><p className="path-label">{projectDir}</p></div><button className="button secondary" onClick={refreshProject} disabled={busy}>更新</button></div>
            <div className="summary-grid"><article><span>ブランチ</span><strong>{status.branch}</strong></article><article><span>変更</span><strong>{status.changes.length}</strong></article><article><span>追跡中</span><strong>{tracked.length}</strong></article><article><span>未追跡</span><strong>{untracked.length}</strong></article></div>
            <nav className="workspace-tabs" aria-label="プロジェクト操作">{tabs.map((tab) => <button key={tab.id} className={activeTab === tab.id ? "active" : ""} onClick={() => setActiveTab(tab.id)} disabled={busy}>{tab.label}</button>)}</nav>

            {activeTab === "status" && <div className="panel-grid">
              <section className="changes-card"><div className="card-heading"><div><p className="eyebrow">WORKING TREE</p><h3>現在の変更</h3></div><span>{status.changes.length}件</span></div>{status.changes.length === 0 ? <div className="clean-state"><span>✓</span>作業ツリーはクリーンです</div> : <div className="change-list">{status.changes.map((change) => <div className="change-row" key={`${change.state}:${change.path}`}><span className={`state-badge ${change.state}`}>{stateLabels[change.state] ?? change.state}</span><span>{change.path}</span></div>)}</div>}</section>
              <section className="operation-card drop-zone"><div className="card-heading"><div><p className="eyebrow">TRACKING</p><h3>追跡ファイル</h3></div><span>{tracked.length}件</span></div><p className="card-copy">ファイルまたはフォルダをこのウィンドウへドロップして追加できます。</p><div className="action-row padded"><button className="button secondary" onClick={() => chooseTrackFiles(false)} disabled={busy}>ファイルを追加</button><button className="button secondary" onClick={() => chooseTrackFiles(true)} disabled={busy}>フォルダを追加</button></div><div className="file-list">{tracked.length === 0 ? <p className="muted">追跡中のファイルはありません。</p> : tracked.map((path) => <div className="file-row" key={path}><span title={path}>{path}</span><button onClick={() => untrackPath(path)} disabled={busy}>追跡解除</button></div>)}</div>{untracked.length > 0 && <details className="untracked-list"><summary>未追跡ファイル（{untracked.length}件）</summary>{untracked.map((path) => <button key={path} onClick={() => trackPaths([path])} disabled={busy}><span>{path}</span><small>追跡する</small></button>)}</details>}</section>
            </div>}

            {activeTab === "tree" && <CommitTree graph={graph} selectedId={commitDetail?.id ?? null} detail={commitDetail} projectDir={projectDir} sproutProgram={sproutProgram} busy={busy} onSelect={(commitId) => selectCommit(commitId, "tree")} onRestore={restoreCommit} onSwitch={switchBranch} onSetThumbnail={setCommitThumbnail} onUpdateMessage={updateCommitMessage} />}

            {activeTab === "commit" && <section className="operation-card form-card"><p className="eyebrow">CREATE SNAPSHOT</p><h3>変更をコミット</h3><label>コミットメッセージ<textarea value={commitMessage} onChange={(event) => setCommitMessage(event.currentTarget.value)} placeholder="このスナップショットで行ったこと" disabled={busy} /></label><label>サムネイル（任意）<div className="path-picker"><input value={thumbnailPath} readOnly placeholder="PNG・JPEG・WebP（2 MiB以下）" /><button className="button secondary" onClick={chooseThumbnail} disabled={busy}>選択</button>{thumbnailPath && <button className="text-button" onClick={() => setThumbnailPath("")} disabled={busy}>解除</button>}</div></label><button className="button primary commit-button" onClick={commitChanges} disabled={busy || !commitMessage.trim()}>コミットを作成</button></section>}

            {activeTab === "history" && <div className="history-layout"><section className="operation-card history-list"><div className="card-heading"><div><p className="eyebrow">HISTORY</p><h3>コミット履歴</h3></div><span>{history.length}件</span></div>{history.length === 0 ? <p className="muted padded">コミットはまだありません。</p> : history.map((entry) => <button key={entry.id} className={commitDetail?.id === entry.id ? "active" : ""} onClick={() => selectCommit(entry.id)} disabled={busy}><strong>{entry.message}</strong><span>{shortId(entry.id)} · {formatDate(entry.created_at)}</span></button>)}</section><section className="operation-card commit-detail">{commitDetail ? <><p className="eyebrow">COMMIT DETAIL</p><h3>{commitDetail.message}</h3><dl><div><dt>ID</dt><dd>{commitDetail.id}</dd></div><div><dt>ブランチ</dt><dd>{commitDetail.branch_name}</dd></div><div><dt>日時</dt><dd>{formatDate(commitDetail.created_at)}</dd></div><div><dt>サムネイル</dt><dd>{commitDetail.thumbnail?.original_name ?? "なし"}</dd></div></dl><div className="file-list detail-files">{commitDetail.files.map((file) => <div className="file-row" key={file.path}><span>{file.path}</span><small>{file.size.toLocaleString()} bytes</small></div>)}</div><button className="button danger" onClick={() => restoreCommit(commitDetail.id)} disabled={busy}>このコミットを復元</button></> : <div className="detail-empty">履歴からコミットを選択すると詳細を表示します。</div>}</section></div>}

            {activeTab === "branches" && <div className="panel-grid"><section className="operation-card branch-list"><div className="card-heading"><div><p className="eyebrow">BRANCHES</p><h3>ブランチ一覧</h3></div><span>{branches.length}件</span></div>{branches.map((branch) => <div className={`branch-row ${branch.current ? "current" : ""}`} key={branch.name}><div><strong>{branch.name}{branch.current && <span>現在</span>}</strong><small>{shortId(branch.commit_id)}{branch.comment ? ` · ${branch.comment}` : ""}</small></div>{!branch.current && <button className="button secondary" onClick={() => switchBranch(branch.name)} disabled={busy}>切り替え</button>}</div>)}</section><section className="operation-card form-card"><p className="eyebrow">NEW BRANCH</p><h3>ブランチを作成</h3><label>ブランチ名<input value={branchName} onChange={(event) => setBranchName(event.currentTarget.value)} placeholder="例: design-a" disabled={busy} /></label><label>コメント（任意）<input value={branchComment} onChange={(event) => setBranchComment(event.currentTarget.value)} placeholder="用途や方針" disabled={busy} /></label><button className="button primary" onClick={createBranch} disabled={busy || !branchName.trim()}>作成</button></section></div>}
          </>}
        </section>
      </main>
    </div>
  );
}

export default App;
