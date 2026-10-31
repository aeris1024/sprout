import { useState, type ClipboardEvent } from "react";
import PreviewImage from "./PreviewImage";
import type { CommitAttachment } from "../lib/sprout";

export interface PreviewMetadata { display_name: string; description: string; }
export interface PreviewActions {
  metadata?: (id: string, data: PreviewMetadata) => void;
  add: () => void;
  paste: (files: File[]) => void;
  pastePaths: () => void;
  replace: (id: string) => void;
  remove: (id: string) => void;
  export: (id: string, name: string) => void;
  order: (ids: string[]) => void;
}
export default function PreviewPanel({ attachments, busy, actions, projectDir, program, commitId }: { attachments: CommitAttachment[]; busy: boolean; actions: PreviewActions; projectDir: string; program: string; commitId: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  const previews = attachments.filter((item) => item.role === "preview").sort((a, b) => a.position - b.position);
  const context = `${projectDir}\0${commitId}\0${program}`;
  const imageKey = (item: CommitAttachment) => `${context}\0${item.id}\0${item.object_hash}`;
  const image = previews.find((item) => imageKey(item) === selected);
  function paste(event: ClipboardEvent) {
    const files = Array.from(event.clipboardData.files ?? []);
    if (!files.length) { if (!busy) actions.pastePaths(); return; }
    event.preventDefault();
    event.stopPropagation();
    if (!busy) actions.paste(files);
  }
  function move(index: number, offset: number) {
    const ids = previews.map((item) => item.id);
    [ids[index], ids[index + offset]] = [ids[index + offset], ids[index]];
    actions.order(ids);
  }
  return <section className="preview-panel" aria-label="プレビュー管理">
    <h4>プレビュー（{previews.length}件）</h4>
    <p className="panel-copy">形式を問わず添付できます。葉の詳細を開いた状態でファイルをドロップすると、プレビューに追加します。</p>
    <p className="panel-copy">削除したプレビューや置き換え前の版はゴミ箱に残ります。添付一覧が変更される前なら復旧できます。</p>
    <button className="button secondary preview-add" disabled={busy} onClick={actions.add}>プレビューを追加</button>
    <div className="preview-paste" role="group" aria-label="プレビュー貼り付け領域" tabIndex={0} onPaste={paste}>ここを選んで Ctrl+V：画像・ファイルをプレビューに追加（この領域の外では画像をサムネイルに使用）</div>
    {!previews.length && <p className="muted">プレビューはありません。</p>}
    {image && <PreviewImage key={imageKey(image)} projectDir={projectDir} program={program} attachment={image} onClose={() => setSelected(null)} />}
    <ol className="preview-list">{previews.map((item, index) => <li key={item.id}>
      <div className="preview-head">
        <p className="preview-name">{item.display_name || item.original_name}</p>
        <div className="preview-order">
          <button className="icon-button small" disabled={busy || index === 0} onClick={() => move(index, -1)} aria-label={`${item.original_name}を上へ`}>↑</button>
          <button className="icon-button small" disabled={busy || index === previews.length - 1} onClick={() => move(index, 1)} aria-label={`${item.original_name}を下へ`}>↓</button>
        </div>
      </div>
      {item.description && <p className="panel-copy" style={{ whiteSpace: "pre-wrap" }}>{item.description}</p>}<p className="panel-copy">{item.media_type} · {item.size.toLocaleString()} B</p>
      {actions.metadata && <MetadataEditor key={`${item.id}:${item.updated_at}`} item={item} busy={busy} onSave={actions.metadata} />}
      <div className="action-row">
        {(item.media_type.startsWith("image/") || /\.(png|jpe?g|webp|bmp)$/i.test(item.original_name)) && <button className={`button secondary small${imageKey(item) === selected ? " pressed" : ""}`} disabled={busy} aria-pressed={imageKey(item) === selected} onClick={() => setSelected(imageKey(item))} aria-label={`${item.original_name}を表示`}>画像を表示</button>}
        <button className="button secondary small" disabled={busy} onClick={() => actions.replace(item.id)} aria-label={`${item.original_name}を置き換え`}>置き換え</button>
        <button className="button secondary small" disabled={busy} onClick={() => actions.export(item.id, item.original_name)} aria-label={`${item.original_name}を取り出す`}>取り出す</button>
        <button className="button danger small" disabled={busy} onClick={() => actions.remove(item.id)} aria-label={`${item.original_name}を削除`}>削除</button>
      </div>
    </li>)}</ol>
  </section>;
}


function MetadataEditor({ item, busy, onSave }: { item: CommitAttachment; busy: boolean; onSave: (id: string, data: PreviewMetadata) => void }) {
  const [name, setName] = useState(item.display_name ?? "");
  const [description, setDescription] = useState(item.description ?? "");
  return <details className="panel-details"><summary>表示名・説明を編集</summary>
    <form className="preview-metadata" aria-label={`${item.original_name}のメタ情報`} onSubmit={(event) => {
      event.preventDefault(); onSave(item.id, { display_name: name, description });
    }}>
      <p className="panel-copy">添付ID: {item.id} ／ 元のファイル名: {item.original_name}</p>
      <label className="field">表示名<input value={name} disabled={busy} onChange={(event) => setName(event.currentTarget.value)} /></label>
      <label className="field">説明<textarea value={description} disabled={busy} onChange={(event) => setDescription(event.currentTarget.value)} /></label>
      <button className="button secondary small" disabled={busy} type="submit">メタ情報を保存</button>
    </form>
  </details>;
}
