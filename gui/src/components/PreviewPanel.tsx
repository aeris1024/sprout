import type { ClipboardEvent } from "react";
import type { CommitAttachment } from "../lib/sprout";

export interface PreviewActions {
  add: () => void;
  paste: (files: File[]) => void;
  pastePaths: () => void;
  replace: (id: string) => void;
  remove: (id: string) => void;
  export: (id: string, name: string) => void;
  order: (ids: string[]) => void;
}
export default function PreviewPanel({ attachments, busy, actions }: { attachments: CommitAttachment[]; busy: boolean; actions: PreviewActions }) {
  const previews = attachments.filter((item) => item.role === "preview").sort((a, b) => a.position - b.position);
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
    <button className="button secondary" disabled={busy} onClick={actions.add}>プレビューを追加</button>
    <div className="preview-paste" role="group" aria-label="プレビュー貼り付け領域" tabIndex={0} onPaste={paste}>ここを選んで Ctrl+V：画像・ファイルをプレビューに追加（この領域の外では画像をサムネイルに使用）</div>
    {!previews.length && <p className="muted">プレビューはありません。</p>}
    <ol className="preview-list">{previews.map((item, index) => <li key={item.id}>
      <p className="preview-name">{item.original_name}</p><p className="panel-copy">{item.media_type} · {item.size.toLocaleString()} B</p>
      <div className="action-row">
        <button disabled={busy} onClick={() => actions.replace(item.id)} aria-label={`${item.original_name}を置き換え`}>置き換え</button>
        <button disabled={busy} onClick={() => actions.export(item.id, item.original_name)} aria-label={`${item.original_name}を取り出す`}>取り出す</button>
        <button disabled={busy} onClick={() => actions.remove(item.id)} aria-label={`${item.original_name}を削除`}>削除</button>
        <button disabled={busy || index === 0} onClick={() => move(index, -1)} aria-label={`${item.original_name}を上へ`}>↑</button>
        <button disabled={busy || index === previews.length - 1} onClick={() => move(index, 1)} aria-label={`${item.original_name}を下へ`}>↓</button>
      </div>
    </li>)}</ol>
  </section>;
}
