import type { StatusChange } from "../lib/sprout";

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
};

interface SavePanelProps {
  changes: StatusChange[];
  message: string;
  thumbnailPath: string;
  busy: boolean;
  onMessageChange: (value: string) => void;
  onChooseThumbnail: () => void;
  onClearThumbnail: () => void;
  onSave: () => void;
}

export default function SavePanel({
  changes,
  message,
  thumbnailPath,
  busy,
  onMessageChange,
  onChooseThumbnail,
  onClearThumbnail,
  onSave,
}: SavePanelProps) {
  return (
    <section className="panel-section" aria-label="未保存の変更">
      <p className="eyebrow">UNSAVED</p>
      <h3>{changes.length === 0 ? "変更はありません" : `未保存の変更 ${changes.length}件`}</h3>
      {changes.length === 0 ? (
        <div className="clean-state">作業フォルダは保存済みの状態です</div>
      ) : (
        <div className="change-list">
          {changes.map((change) => (
            <div className="change-row" key={`${change.state}:${change.path}`}>
              <span className={`state-badge ${change.state}`}>{stateLabels[change.state] ?? change.state}</span>
              <span>{change.path}</span>
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
          <input value={thumbnailPath} readOnly placeholder="PNG・JPEG・WebP（2 MiB以下）" />
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
      <button className="button primary wide" onClick={onSave} disabled={busy || !message.trim()}>
        保存して葉にする
      </button>
    </section>
  );
}
