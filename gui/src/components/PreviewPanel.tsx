import { useState, type ClipboardEvent } from "react";
import PreviewImage from "./PreviewImage";
import type { CommitAttachment, CommitFile } from "../lib/sprout";

export interface PreviewMetadata { display_name: string; description: string; is_primary: boolean; file_ids: string[]; }
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
export default function PreviewPanel({ attachments, busy, actions, projectDir, program, commitId, files = [] }: { files?: CommitFile[]; attachments: CommitAttachment[]; busy: boolean; actions: PreviewActions; projectDir: string; program: string; commitId: string }) {
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
    <button className="button secondary" disabled={busy} onClick={actions.add}>プレビューを追加</button>
    <div className="preview-paste" role="group" aria-label="プレビュー貼り付け領域" tabIndex={0} onPaste={paste}>ここを選んで Ctrl+V：画像・ファイルをプレビューに追加（この領域の外では画像をサムネイルに使用）</div>
    {!previews.length && <p className="muted">プレビューはありません。</p>}
    {image && <PreviewImage key={imageKey(image)} projectDir={projectDir} program={program} attachment={image} onClose={() => setSelected(null)} />}
    <ol className="preview-list">{previews.map((item, index) => <li key={item.id}>
      <p className="preview-name">{item.display_name || item.original_name} {item.is_primary && <strong>代表</strong>}</p>{item.description && <p className="panel-copy" style={{ whiteSpace: "pre-wrap" }}>{item.description}</p>}<p className="panel-copy">{item.media_type} · {item.size.toLocaleString()} B</p>
      {Boolean(item.file_ids?.length) && <p className="panel-copy">対象素材: {item.file_ids!.map((id) => files.find((file) => file.file_id === id)?.path ?? id).join(", ")}</p>}
      {actions.metadata && <MetadataEditor key={`${item.id}:${item.updated_at}:${item.is_primary}`} item={item} files={files} busy={busy} onSave={actions.metadata} />}
      <div className="action-row">
        {(item.media_type.startsWith("image/") || /\.(png|jpe?g|webp|bmp)$/i.test(item.original_name)) && <button disabled={busy} aria-pressed={imageKey(item) === selected} onClick={() => setSelected(imageKey(item))} aria-label={`${item.original_name}を表示`}>画像を表示</button>}
        <button disabled={busy} onClick={() => actions.replace(item.id)} aria-label={`${item.original_name}を置き換え`}>置き換え</button>
        <button disabled={busy} onClick={() => actions.export(item.id, item.original_name)} aria-label={`${item.original_name}を取り出す`}>取り出す</button>
        <button disabled={busy} onClick={() => actions.remove(item.id)} aria-label={`${item.original_name}を削除`}>削除</button>
        <button disabled={busy || index === 0} onClick={() => move(index, -1)} aria-label={`${item.original_name}を上へ`}>↑</button>
        <button disabled={busy || index === previews.length - 1} onClick={() => move(index, 1)} aria-label={`${item.original_name}を下へ`}>↓</button>
      </div>
    </li>)}</ol>
  </section>;
}


function MetadataEditor({ item, files, busy, onSave }: { item: CommitAttachment; files: CommitFile[]; busy: boolean; onSave: (id: string, data: PreviewMetadata) => void }) {
  const [name, setName] = useState(item.display_name ?? "");
  const [description, setDescription] = useState(item.description ?? "");
  const [primary, setPrimary] = useState(item.is_primary ?? false);
  const [ids, setIds] = useState(item.file_ids ?? []);
  return <details><summary>表示名・説明・対象素材を編集</summary>
    <form aria-label={`${item.original_name}のメタ情報`} onSubmit={(event) => {
      event.preventDefault(); onSave(item.id, { display_name: name, description, is_primary: primary, file_ids: ids });
    }}>
      <p className="panel-copy">添付ID: {item.id} ／ 元のファイル名: {item.original_name}</p>
      <label className="field">表示名<input value={name} disabled={busy} onChange={(event) => setName(event.currentTarget.value)} /></label>
      <label className="field">説明<textarea value={description} disabled={busy} onChange={(event) => setDescription(event.currentTarget.value)} /></label>
      <label><input type="checkbox" checked={primary} disabled={busy} onChange={(event) => setPrimary(event.currentTarget.checked)} />このコミットの代表プレビュー</label>
      <fieldset disabled={busy}><legend>対象素材（複数選択可）</legend>
        {files.filter((file) => file.file_id).map((file) => <label className="snapshot-file" key={file.file_id}>
          <input type="checkbox" checked={ids.includes(file.file_id!)} onChange={(event) => { const checked = event.currentTarget.checked; setIds((current) => checked ? [...current, file.file_id!] : current.filter((id) => id !== file.file_id)); }} />{file.path}
        </label>)}
        {!files.some((file) => file.file_id) && <p className="muted">関連付けできる素材はありません。</p>}
      </fieldset>
      <button disabled={busy} type="submit">メタ情報を保存</button>
    </form>
  </details>;
}
