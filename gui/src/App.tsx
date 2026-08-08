import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";
import {
  isUninitializedProject,
  normalizeCliError,
  runSprout,
  type SproutCliError,
  type SproutStatus,
} from "./lib/sprout";
import {
  loadSettings,
  nextRecentProjects,
  saveSettings,
} from "./lib/settings";

type Notice = SproutCliError & { kind: "error" | "success" };

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
};

function projectName(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

function App() {
  const [projectDir, setProjectDir] = useState("");
  const [status, setStatus] = useState<SproutStatus | null>(null);
  const [recentProjects, setRecentProjects] = useState<string[]>([]);
  const [sproutProgram, setSproutProgram] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [initCandidate, setInitCandidate] = useState("");
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void loadSettings()
      .then((settings) => {
        setRecentProjects(settings.recentProjects);
        setSproutProgram(settings.sproutProgram);
      })
      .catch((error) => {
        setNotice({ ...normalizeCliError(error), kind: "error" });
      });
  }, []);

  async function rememberProject(path: string) {
    const updated = nextRecentProjects(recentProjects, path);
    setRecentProjects(updated);
    try {
      await saveSettings({ recentProjects: updated, sproutProgram });
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
    }
  }

  async function openProject(path: string) {
    setBusy(true);
    setNotice(null);
    setInitCandidate("");
    try {
      const result = await runSprout<SproutStatus>(
        path,
        ["status", "--tracked", "--untracked"],
        sproutProgram,
      );
      setProjectDir(path);
      setStatus(result);
      await rememberProject(path);
    } catch (error) {
      const cliError = normalizeCliError(error);
      setStatus(null);
      setProjectDir(path);
      if (isUninitializedProject(cliError)) {
        setInitCandidate(path);
      } else if (cliError.code === "sprout_not_found") {
        setSettingsOpen(true);
      }
      setNotice({ ...cliError, kind: "error" });
    } finally {
      setBusy(false);
    }
  }

  async function chooseProject() {
    const selected = await open({
      directory: true,
      multiple: false,
      title: "Sproutプロジェクトを選択",
    });
    if (typeof selected === "string") {
      await openProject(selected);
    }
  }

  async function initializeProject() {
    if (!initCandidate) return;
    setBusy(true);
    setNotice(null);
    try {
      await runSprout(initCandidate, ["init", "."], sproutProgram);
      setNotice({
        code: "initialized",
        message: "Sproutプロジェクトを初期化しました",
        details: {},
        kind: "success",
      });
      await openProject(initCandidate);
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
      setBusy(false);
    }
  }

  async function saveCliSetting() {
    try {
      await saveSettings({ recentProjects, sproutProgram: sproutProgram.trim() });
      setSproutProgram(sproutProgram.trim());
      setNotice({
        code: "settings_saved",
        message: "CLI設定を保存しました",
        details: {},
        kind: "success",
      });
    } catch (error) {
      setNotice({ ...normalizeCliError(error), kind: "error" });
    }
  }

  const trackedCount = status?.tracked?.length ?? 0;
  const untrackedCount = status?.untracked?.length ?? 0;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </div>
          <div>
            <p className="eyebrow">OFFLINE SNAPSHOTS</p>
            <h1>Sprout</h1>
          </div>
        </div>
        <div className="header-actions">
          <button className="button secondary" onClick={() => setSettingsOpen(!settingsOpen)}>
            CLI設定
          </button>
          <button className="button primary" onClick={() => void chooseProject()} disabled={busy}>
            フォルダを開く
          </button>
        </div>
      </header>

      {notice && (
        <div className={`notice ${notice.kind}`} role="alert">
          <div>
            <strong>{notice.kind === "error" ? "操作を完了できませんでした" : "完了"}</strong>
            <p>{notice.message}</p>
          </div>
          <div className="notice-actions">
            {notice.code === "repository_locked" && projectDir && (
              <button onClick={() => void openProject(projectDir)}>再試行</button>
            )}
            <button aria-label="通知を閉じる" onClick={() => setNotice(null)}>×</button>
          </div>
        </div>
      )}

      {settingsOpen && (
        <section className="settings-panel" aria-label="CLI設定">
          <div>
            <h2>Sprout CLI</h2>
            <p>空欄の場合はPATH上のsproutを使用します。</p>
          </div>
          <input
            value={sproutProgram}
            onChange={(event) => setSproutProgram(event.currentTarget.value)}
            placeholder="例: C:\\Tools\\sprout.exe"
            aria-label="Sprout CLIのパス"
          />
          <button className="button secondary" onClick={() => void saveCliSetting()}>
            保存
          </button>
        </section>
      )}

      <main className="workspace">
        <aside className="sidebar">
          <div className="sidebar-heading">
            <h2>最近使ったプロジェクト</h2>
            <span>{recentProjects.length}</span>
          </div>
          {recentProjects.length === 0 ? (
            <p className="muted">開いたプロジェクトがここに表示されます。</p>
          ) : (
            <nav className="recent-list" aria-label="最近使ったプロジェクト">
              {recentProjects.map((path) => (
                <button
                  className={path === projectDir ? "active" : ""}
                  key={path}
                  onClick={() => void openProject(path)}
                  disabled={busy}
                  title={path}
                >
                  <span>{projectName(path)}</span>
                  <small>{path}</small>
                </button>
              ))}
            </nav>
          )}
        </aside>

        <section className="content">
          {busy && <div className="loading-bar" aria-label="読み込み中" />}
          {!projectDir && (
            <div className="empty-state">
              <div className="empty-illustration" aria-hidden="true"><span /></div>
              <p className="eyebrow">WELCOME TO SPROUT</p>
              <h2>制作データの現在地を、静かに残す。</h2>
              <p>
                フォルダを選ぶと、追跡中のファイルと変更状況を確認できます。
                データはローカルから外へ送信されません。
              </p>
              <button className="button primary large" onClick={() => void chooseProject()}>
                プロジェクトを選択
              </button>
            </div>
          )}

          {projectDir && initCandidate && (
            <div className="empty-state compact">
              <p className="eyebrow">NOT INITIALIZED</p>
              <h2>このフォルダはまだSproutプロジェクトではありません</h2>
              <p className="path-label">{initCandidate}</p>
              <p>.sprout管理情報を作成します。既存ファイルの内容は変更しません。</p>
              <div className="action-row">
                <button className="button primary" onClick={() => void initializeProject()} disabled={busy}>
                  このフォルダを初期化
                </button>
                <button className="button secondary" onClick={() => void chooseProject()}>
                  別のフォルダを選ぶ
                </button>
              </div>
            </div>
          )}

          {projectDir && status && (
            <>
              <div className="project-heading">
                <div>
                  <p className="eyebrow">CURRENT PROJECT</p>
                  <h2>{projectName(projectDir)}</h2>
                  <p className="path-label">{projectDir}</p>
                </div>
                <button className="button secondary" onClick={() => void openProject(projectDir)} disabled={busy}>
                  更新
                </button>
              </div>

              <div className="summary-grid">
                <article><span>ブランチ</span><strong>{status.branch}</strong></article>
                <article><span>変更</span><strong>{status.changes.length}</strong></article>
                <article><span>追跡中</span><strong>{trackedCount}</strong></article>
                <article><span>未追跡</span><strong>{untrackedCount}</strong></article>
              </div>

              <section className="changes-card">
                <div className="card-heading">
                  <div>
                    <p className="eyebrow">WORKING TREE</p>
                    <h3>現在の変更</h3>
                  </div>
                  <span>{status.changes.length}件</span>
                </div>
                {status.changes.length === 0 ? (
                  <div className="clean-state"><span>✓</span>作業ツリーはクリーンです</div>
                ) : (
                  <div className="change-list">
                    {status.changes.map((change) => (
                      <div className="change-row" key={`${change.state}:${change.path}`}>
                        <span className={`state-badge ${change.state}`}>
                          {stateLabels[change.state] ?? change.state}
                        </span>
                        <span>{change.path}</span>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
