import { useEffect, useRef, useState } from "react";
import { formatBytes, normalizeCliError, runSprout, type CommitGraph, type SproutCliError } from "../lib/sprout";

type Difference = { state: string; path: string; old_size: number | null; new_size: number | null; previous_path?: string };
interface Props {
  projectDir: string;
  program: string;
  commits: CommitGraph["commits"];
  source: string;
  target: string;
  busy: boolean;
  onChange: (source: string, target: string) => void;
  onClose: () => void;
  picking?: "source" | "target";
  onPick?: (side: "source" | "target") => void;
}
const labels: Record<string, string> = { added: "追加", modified: "変更", deleted: "削除", renamed: "改名" };

export default function ComparePanel({ projectDir, program, commits, source, target, busy, onChange, onClose, picking = "target", onPick }: Props) {
  const [result, setResult] = useState<Difference[] | null>(null);
  const [error, setError] = useState<SproutCliError | null>(null);
  const [loading, setLoading] = useState(false);
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setResult(null);
    setError(null);
    setLoading(false);
    return () => { generation.current += 1; };
  }, [projectDir, program, source, target]);
  async function compare() {
    const request = ++generation.current;
    setResult(null);
    setError(null);
    setLoading(true);
    try {
      const differences = await runSprout<Difference[]>(projectDir, ["file", "diff", source, target], program);
      if (generation.current === request) setResult(differences);
    } catch (cause) {
      if (generation.current === request) setError(normalizeCliError(cause));
    } finally {
      if (generation.current === request) setLoading(false);
    }
  }
  const valid = commits.some((c) => c.id === source) && commits.some((c) => c.id === target);
  return <section className="panel-section" aria-label="葉の比較">
    <div className="panel-heading"><h3>葉の比較</h3><button className="icon-button" aria-label="比較を閉じる" onClick={onClose}>×</button></div>
    <p className="panel-copy">比較元 → 比較先のファイルの変化を表示します。マップで選び直す側を指定してから、葉を選んでください。</p>
    {onPick && <fieldset className="compare-picker"><legend>マップで選び直す側</legend>{(["source", "target"] as const).map((side) => <label key={side}><input type="radio" name="compare-picking" checked={picking === side} disabled={busy} onChange={() => onPick(side)} />{side === "source" ? "比較元をマップで選ぶ" : "比較先をマップで選ぶ"}</label>)}</fieldset>}
    {(["比較元", "比較先"] as const).map((label, index) => <label className="field" key={label}>{label}
      <select aria-label={label} value={index === 0 ? source : target} disabled={busy || loading} onChange={(event) => onChange(index === 0 ? event.target.value : source, index === 1 ? event.target.value : target)}>
        <option value="">葉を選択</option>
        {commits.map((commit) => <option key={commit.id} value={commit.id}>{commit.id.slice(0, 12)} — {commit.message}</option>)}
      </select>
    </label>)}
    <button className="button secondary" disabled={busy || loading || !source || !target} onClick={() => onChange(target, source)}>比較元と比較先を入れ替える</button>
    <button className="button primary" disabled={busy || loading || !valid} onClick={() => void compare()}>{loading ? "比較中…" : "比較する"}</button>
    {error && <div role="alert"><p>{error.message}</p>{typeof error.details.path === "string" && <p>{error.details.path}</p>}</div>}
    {result && (result.length === 0 ? <p role="status">差分はありません</p> : <ul className="file-list" aria-label="ファイル差分">{result.map((entry) => <li className="file-row" key={entry.path}><span>{labels[entry.state] ?? entry.state}</span><span>{entry.previous_path ? `${entry.previous_path} → ${entry.path}` : entry.path}</span><small>{entry.old_size === null ? "—" : formatBytes(entry.old_size)} → {entry.new_size === null ? "—" : formatBytes(entry.new_size)}</small></li>)}</ul>)}
  </section>;
}
