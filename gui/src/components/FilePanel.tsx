import { useState } from "react";
import { isThumbnailSourcePath } from "../lib/sprout";

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
  sourceExtensions?: string[];
  coverMessage?: string;
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
  sourceExtensions,
  coverMessage,
  onClose,
}: FilePanelProps) {
  const [query, setQuery] = useState("");
  const matches = (path: string) => path.normalize("NFC").toLocaleLowerCase().includes(query.trim().normalize("NFC").toLocaleLowerCase());
  const visibleTracked = tracked.filter(matches);
  const visibleUntracked = untracked.filter(matches);
  return (
    <section className="panel-section" aria-label="追跡ファイル">
      <div className="panel-heading">
        <div>
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
        <section className="annotation-section" aria-label="サムネイル自動生成元">
          <h4>サムネイル自動生成元</h4>
          {cover ? (
            <>
              <p className="panel-copy">{cover.path ?? "追跡を解除したファイルが指定されています。別のファイルを選んでください。"}</p>
              {cover.path && !isThumbnailSourcePath(cover.path, sourceExtensions) && <p className="panel-copy">現在の生成元は対応する画像の拡張子ではありません。別の画像を指定するか解除してください。</p>}
              <p className="panel-copy">サムネイルを指定せずに次の葉を保存すると、このファイルから作ります。登録済みのサムネイルは変更しません。</p>
              {coverMessage && <p className="panel-copy">{coverMessage}</p>}
              <div className="action-row">
                <button className="button secondary small" onClick={onApplyCover} disabled={busy}>既存の葉へ適用</button>
                <button className="button secondary small" onClick={onClearCover} disabled={busy}>解除</button>
              </div>
            </>
          ) : <p className="panel-copy">追跡中の画像を自動生成元に設定すると、保存のたびにサムネイルを自動で作ります。</p>}
        </section>
      )}
      <h4 className="list-title">追跡中（{tracked.length}件）</h4>
      <label className="field">ファイルを検索<input type="search" placeholder="パス名で絞り込み" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      {query.trim() && <p role="status" className="field-hint">追跡中 {visibleTracked.length}件・未追跡 {visibleUntracked.length}件が一致</p>}
      <div className="file-list">
        {tracked.length === 0 ? (
          <p className="muted">追跡中のファイルはありません。</p>
        ) : (
          visibleTracked.map((path) => (
            <div className="file-row" key={path}>
              <span title={path}>{path}</span>
              {onSetCover && (cover?.path === path
                ? <strong className="file-row-mark">生成元</strong>
                : isThumbnailSourcePath(path, sourceExtensions) && <button onClick={() => onSetCover(path)} disabled={busy} aria-label={`${path}をサムネイル自動生成元に設定`}>自動生成元に設定</button>)}
              <button onClick={() => onUntrack(path)} disabled={busy}>
                追跡解除
              </button>
            </div>
          ))
        )}
      </div>
      {tracked.length > 0 && visibleTracked.length === 0 && <p className="muted">一致する追跡ファイルはありません。</p>}
      <h4 className="list-title">未追跡（{untracked.length}件）</h4>
      <div className="file-list">
        {untracked.length === 0 ? (
          <p className="muted">未追跡のファイルはありません。</p>
        ) : (
          visibleUntracked.map((path) => (
            <div className="file-row" key={path}>
              <span title={path}>{path}</span>
              <button onClick={() => onTrack(path)} disabled={busy}>
                追跡する
              </button>
            </div>
          ))
        )}
      </div>
      {untracked.length > 0 && visibleUntracked.length === 0 && <p className="muted">一致する未追跡ファイルはありません。</p>}
    </section>
  );
}
