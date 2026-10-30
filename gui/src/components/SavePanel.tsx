import type { StatusChange } from "../lib/sprout";

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
  renamed: "改名",
};

/** Renamed files have no one-step revert: undoing a rename touches two paths. */
const revertLabels: Record<string, string> = {
  modified: "元に戻す",
  deleted: "元に戻す",
  added: "追跡から外す",
};

interface SavePanelProps {
  changes: StatusChange[];
  growsBranch: boolean;
  message: string;
  thumbnailPath: string;
  thumbnailPasted: boolean;
  busy: boolean;
  onMessageChange: (value: string) => void;
  onChooseThumbnail: () => void;
  onClearThumbnail: () => void;
  onSave: () => void;
  onKeepAsBud: () => void;
  onRevert: (change: StatusChange) => void;
}

export default function SavePanel({
  changes,
  growsBranch,
  message,
  thumbnailPath,
  thumbnailPasted,
  busy,
  onMessageChange,
  onChooseThumbnail,
  onClearThumbnail,
  onSave,
  onKeepAsBud,
  onRevert,
}: SavePanelProps) {
  return (
    <section className="panel-section" aria-label="未保存の変更">
      <p className="eyebrow">未保存の芽</p>
      <h3>{changes.length === 0 ? "変更はありません" : `未保存の変更 ${changes.length}件`}</h3>
      {changes.length === 0 ? (
        <div className="clean-state">作業フォルダは保存済みの状態です</div>
      ) : (
        <div className="change-list">
          {changes.map((change) => (
            <div className="change-row" key={`${change.state}:${change.path}`}>
              <span className={`state-badge ${change.state}`}>{stateLabels[change.state] ?? change.state}</span>
              <span>{change.previous_path ? `${change.previous_path} → ${change.path}` : change.path}</span>
              {revertLabels[change.state] && (
                <button className="text-button" onClick={() => onRevert(change)} disabled={busy} aria-label={`${change.path}を${revertLabels[change.state]}`}>
                  {revertLabels[change.state]}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      <label className="field">
        メッセージ
        <textarea
          value={message}
          onChange={(event) => onMessageChange(event.currentTarget.value)}
          placeholder="このスナップショットで行ったこと"
          disabled={busy}
        />
      </label>
      <label className="field">
        サムネイル（任意）
        <div className="path-picker">
          <input
            value={thumbnailPasted ? "貼り付けた画像" : thumbnailPath}
            readOnly
            placeholder="PNG・JPEG・WebP（2 MiB以下）。Ctrl+Vで画像を貼り付け"
          />
          <button className="button secondary" onClick={onChooseThumbnail} disabled={busy}>
            選択
          </button>
          {thumbnailPath && (
            <button className="text-button" onClick={onClearThumbnail} disabled={busy}>
              解除
            </button>
          )}
        </div>
      </label>
      {growsBranch && changes.length > 0 && (
        <p className="panel-copy grow-note">途中の芽から保存するため、新しい枝が自動で作られます。</p>
      )}
      <button className="button primary wide" onClick={onSave} disabled={busy || !message.trim()}>
        保存して葉にする
      </button>
      <button className="button secondary wide" onClick={onKeepAsBud} disabled={busy || changes.length === 0}>
        つぼみとして残す
      </button>
      <p className="panel-copy">保存せずに今の変更を取っておきます。作業ファイルは変わりません。</p>
    </section>
  );
}
