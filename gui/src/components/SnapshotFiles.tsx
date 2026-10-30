import { useState } from "react";
import type { CommitFile } from "../lib/sprout";

interface Props {
  files: CommitFile[];
  busy: boolean;
  onExport: (paths: string[]) => void;
  onRestore: (paths: string[]) => void;
}

/** Select explicit saved files, including whole directory subtrees. */
export default function SnapshotFiles({ files, busy, onExport, onRestore }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const directories = [...new Set(files.flatMap(({ path }) => {
    const parts = path.split("/");
    return parts.slice(0, -1).map((_, index) => parts.slice(0, index + 1).join("/") + "/");
  }))].sort();
  function toggle(paths: string[], checked: boolean) {
    setSelected((current) => checked
      ? [...new Set([...current, ...paths])]
      : current.filter((path) => !paths.includes(path)));
  }
  const paths = files.map((file) => file.path).filter((path) => selected.includes(path));
  return <section className="snapshot-files" aria-label="保存済みファイル">
    <h4>保存済みファイル（{files.length}件）</h4>
    <p className="panel-copy">必要なファイルを選んで取り出すか、作業フォルダの同じパスへ戻せます。</p>
    {files.length === 0 ? <p className="muted">保存済みファイルはありません。</p> : <>
      <label className="snapshot-file"><input type="checkbox" checked={paths.length === files.length} disabled={busy} onChange={(event) => toggle(files.map((file) => file.path), event.target.checked)} />すべて選択</label>
      {directories.map((directory) => {
        const children = files.filter((file) => file.path.startsWith(directory)).map((file) => file.path);
        return <label className="snapshot-file" key={directory}><input type="checkbox" checked={children.every((path) => selected.includes(path))} disabled={busy} onChange={(event) => toggle(children, event.target.checked)} />{directory} 配下を選択</label>;
      })}
      <ul className="snapshot-file-list">{files.map((file) => <li key={file.path}><label className="snapshot-file"><input type="checkbox" checked={selected.includes(file.path)} disabled={busy} onChange={(event) => toggle([file.path], event.target.checked)} /><span>{file.path}<small>{file.size.toLocaleString()} B</small>{file.file_id && <small>素材ID: {file.file_id}</small>}</span></label></li>)}</ul>
      <p className="panel-copy">{paths.length}件を選択中</p>
      <div className="panel-actions"><button className="button secondary" disabled={busy || paths.length === 0} onClick={() => onExport(paths)}>選択したファイルを取り出す</button><button className="button secondary" disabled={busy || paths.length === 0} onClick={() => onRestore(paths)}>選択したファイルだけ戻す</button></div>
    </>}
  </section>;
}
