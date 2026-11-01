import { useMemo, useState } from "react";
import type { CommitFile } from "../lib/sprout";

interface Props {
  files: CommitFile[];
  busy: boolean;
  onExport: (paths: string[]) => void;
  onRestore: (paths: string[]) => void;
}
interface Folder { path: string; folders: Map<string, Folder>; files: CommitFile[]; paths: string[] }
const folder = (path: string): Folder => ({ path, folders: new Map(), files: [], paths: [] });
const matchesPath = (path: string, query: string) => path.normalize("NFC").toLocaleLowerCase().includes(query.normalize("NFC").toLocaleLowerCase());

/** Search affects bulk selection only; previously selected hidden files stay selected. */
export default function SnapshotFiles({ files, busy, onExport, onRestore }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<string[]>([]);
  const visible = useMemo(() => files.filter((file) => matchesPath(file.path, query.trim())), [files, query]);
  const root = useMemo(() => {
    const tree = folder("");
    for (const file of visible) {
      let current = tree;
      const parts = file.path.split("/");
      current.paths.push(file.path);
      for (const part of parts.slice(0, -1)) {
        const path = current.path + part + "/";
        if (!current.folders.has(part)) current.folders.set(part, folder(path));
        current = current.folders.get(part)!;
        current.paths.push(file.path);
      }
      current.files.push(file);
    }
    return tree;
  }, [visible]);
  function toggle(paths: string[], checked: boolean) {
    setSelected((current) => checked ? [...new Set([...current, ...paths])] : current.filter((path) => !paths.includes(path)));
  }
  const paths = files.map((file) => file.path).filter((path) => selected.includes(path));
  const hiddenSelected = paths.filter((path) => !root.paths.includes(path)).length;
  function checkbox(children: string[], label: string) {
    const count = children.filter((path) => paths.includes(path)).length;
    return <label className="snapshot-file"><input type="checkbox" checked={children.length > 0 && count === children.length} ref={(node) => { if (node) node.indeterminate = count > 0 && count < children.length; }} disabled={busy || children.length === 0} onChange={(event) => toggle(children, event.target.checked)} />{label}</label>;
  }
  function renderFolder(node: Folder) {
    return <ul className="snapshot-file-list">
      {[...node.folders.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([name, child]) => {
        const open = Boolean(query.trim()) || expanded.includes(child.path);
        return <li key={child.path}>
          <div className="snapshot-folder">
            <button className="text-button" aria-label={`${child.path}を${open ? "折りたたむ" : "展開"}`} aria-expanded={open} disabled={Boolean(query.trim())} onClick={() => setExpanded((current) => open ? current.filter((path) => path !== child.path) : [...current, child.path])}>{open ? "▾" : "▸"} {name}/</button>
            {checkbox(child.paths, `${child.path} 配下を選択`)}
          </div>
          {open && renderFolder(child)}
        </li>;
      })}
      {node.files.map((file) => <li key={file.path}>
        <label className="snapshot-file"><input type="checkbox" checked={paths.includes(file.path)} disabled={busy} onChange={(event) => toggle([file.path], event.target.checked)} /><span>{file.path}<small>{file.size.toLocaleString()} B</small></span></label>
        {file.file_id && <details className="file-identity"><summary>{file.path}の素材ID</summary><p className="mono">{file.file_id}</p></details>}
      </li>)}
    </ul>;
  }
  return <section className="snapshot-files" aria-label="保存済みファイル">
    <h4>保存済みファイル（{files.length}件）</h4>
    <p className="panel-copy">必要なファイルを選んで取り出すか、作業フォルダの同じパスへ戻せます。</p>
    {files.length === 0 ? <p className="muted">保存済みファイルはありません。</p> : <>
      <label className="field">保存済みファイルを検索<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="パス名で絞り込み" /></label>
      {query.trim() && <p className="field-hint">{visible.length}件が一致。全選択・フォルダ選択は検索結果だけが対象です。検索中は一致するフォルダを展開します。</p>}
      {checkbox(root.paths, query.trim() ? "検索結果をすべて選択" : "すべて選択")}
      {visible.length ? renderFolder(root) : <p className="muted">一致するファイルはありません。</p>}
      <div className="snapshot-selection">
        <p className="panel-copy" role="status">{paths.length}件を選択中{hiddenSelected > 0 ? `（検索結果の外に${hiddenSelected}件）` : ""}</p>
        <div className="panel-actions"><button className="button secondary" disabled={busy || paths.length === 0} onClick={() => onExport(paths)}>選択したファイルを取り出す</button><button className="button secondary" disabled={busy || paths.length === 0} onClick={() => onRestore(paths)}>選択したファイルだけ戻す</button></div>
      </div>
    </>}
  </section>;
}
