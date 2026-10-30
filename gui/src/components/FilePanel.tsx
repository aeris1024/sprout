interface FilePanelProps {
  tracked: string[];
  untracked: string[];
  busy: boolean;
  onAddFiles: () => void;
  onAddFolder: () => void;
  onTrack: (path: string) => void;
  onUntrack: (path: string) => void;
  cover?: { file_id: string; path: string | null };
  onSetCover?: (path: string) => void;
  onClearCover?: () => void;
  onApplyCover?: () => void;
  onClose: () => void;
}

export default function FilePanel({
  tracked,
  untracked,
  busy,
  onAddFiles,
  onAddFolder,
  onTrack,
  onUntrack,
  cover,
  onSetCover,
  onClearCover,
  onApplyCover,
  onClose,
}: FilePanelProps) {
  return (
    <section className="panel-section" aria-label="追跡ファイル">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">FILES</p>
          <h3>追跡ファイル</h3>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="ファイルパネルを閉じる">
          ×
        </button>
      </div>
      <p className="panel-copy">ファイルやフォルダをウィンドウへドロップしても追加できます。</p>
      <div className="action-row">
        <button className="button secondary" onClick={onAddFiles} disabled={busy}>
          ファイルを追加
        </button>
        <button className="button secondary" onClick={onAddFolder} disabled={busy}>
          フォルダを追加
        </button>
      </div>
      {onSetCover && (
        <section className="annotation-section" aria-label="代表ファイル">
          <h4>代表ファイル</h4>
          {cover ? (
            <>
              <p className="panel-copy">{cover.path ?? "追跡を解除したファイルが指定されています。別のファイルを選んでください。"}</p>
              <p className="panel-copy">サムネイルを指定せずに保存すると、このファイルから作ります。</p>
              <div className="action-row">
                <button className="button secondary small" onClick={onApplyCover} disabled={busy}>既存の葉へ適用</button>
                <button className="button secondary small" onClick={onClearCover} disabled={busy}>解除</button>
              </div>
            </>
          ) : <p className="panel-copy">追跡中の画像を「代表にする」と、保存のたびにサムネイルを自動で作ります。</p>}
        </section>
      )}
      <h4 className="list-title">追跡中（{tracked.length}件）</h4>
      <div className="file-list">
        {tracked.length === 0 ? (
          <p className="muted">追跡中のファイルはありません。</p>
        ) : (
          tracked.map((path) => (
            <div className="file-row" key={path}>
              <span title={path}>{path}</span>
              {onSetCover && (cover?.path === path
                ? <strong className="file-row-mark">代表</strong>
                : <button onClick={() => onSetCover(path)} disabled={busy} aria-label={`${path}を代表にする`}>代表にする</button>)}
              <button onClick={() => onUntrack(path)} disabled={busy}>
                追跡解除
              </button>
            </div>
          ))
        )}
      </div>
      <h4 className="list-title">未追跡（{untracked.length}件）</h4>
      <div className="file-list">
        {untracked.length === 0 ? (
          <p className="muted">未追跡のファイルはありません。</p>
        ) : (
          untracked.map((path) => (
            <div className="file-row" key={path}>
              <span title={path}>{path}</span>
              <button onClick={() => onTrack(path)} disabled={busy}>
                追跡する
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
