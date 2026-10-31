import { formatLocalTime, type TrashItem } from "../lib/sprout";

const kinds: Record<string, string> = {
  commit: "葉の削除", preview_delete: "プレビューの削除", preview_replace: "プレビューの置き換え前",
  bud_delete: "捨てたつぼみ", discard: "破棄した未保存の変更",
  note_delete: "メモの削除", tag_delete: "タグの削除", branch_delete: "ブランチの削除",
};
const recordNames: Record<string, string> = {
  commits: "葉", commit_files: "保存ファイル", commit_attachments: "添付",
  commit_notes: "メモ", commit_labels: "ラベル", tags: "タグ", branches: "ブランチ",
  repository_state: "現在位置", buds: "つぼみ", bud_files: "つぼみのファイル",
};
const fieldNames: Record<string, string> = {
  message: "メッセージ", path: "パス", original_name: "元のファイル名", media_type: "形式",
  size: "サイズ（B）", position: "表示順", note: "メモ", label: "ラベル",
  name: "名前", comment: "説明", created_at: "作成日時", updated_at: "更新日時",
  parent_id: "親の葉", commit_id: "葉", current_commit_id: "現在の葉", base_commit_id: "起点の葉",
};

function fieldValue(key: string, value: unknown): string {
  if (value == null) return "なし";
  if (key === "position") return String(Number(value) + 1);
  if (key.endsWith("_at")) return formatLocalTime(String(value));
  if (key.endsWith("_id")) return String(value).slice(0, 12);
  return String(value);
}

export default function TrashPanel({ items, busy, onInspect, onRestore, onPurge, onClose }: {
  items: TrashItem[]; busy: boolean;
  onRestore: (item: TrashItem) => void; onPurge: (item: TrashItem) => void; onClose: () => void;
  onInspect: (item: TrashItem) => void;
}) {
  return <section className="panel-section" aria-label="ゴミ箱">
    <div className="panel-heading"><h3>ゴミ箱</h3><button className="icon-button" onClick={onClose} aria-label="ゴミ箱を閉じる" disabled={busy}>×</button></div>
    <p className="panel-copy">完全削除するまで保持します。復旧先の参照やプレビューが変更済みの場合は復旧できません。作業ファイルは変更しません。捨てたつぼみと破棄した未保存の変更は、つぼみとして戻ります。完全削除すると、他の過去版を順に戻す経路も失われる場合があります。</p>
    {items.length === 0 && <p className="muted">ゴミ箱は空です。</p>}
    {items.map((item) => <article className="trash-item" key={item.id}>
      <h4>{item.title}</h4><p className="trash-kind">{kinds[item.kind] ?? item.kind}</p>
      <p className="panel-copy">ゴミ箱へ移動: {formatLocalTime(item.created_at)}</p>
      <p className="panel-copy">保持容量 {item.protected_bytes.toLocaleString()} B ／ 完全削除後の回収可能容量 {item.reclaimable_bytes.toLocaleString()} B</p>
      <details className="panel-details">
        <summary>内部ID</summary>
        <p className="panel-copy mono">対象: {item.target_id}<br />復旧ID: {item.id}</p>
      </details>
      <div className="action-row">
        <button className="button secondary small" disabled={busy} onClick={() => onInspect(item)} aria-label={`${item.title}の復旧内容を確認`}>復旧内容を確認</button>
        <button className="button secondary small" disabled={busy} onClick={() => onRestore(item)} aria-label={`${item.title}を復旧`}>復旧</button>
        <button className="button destructive small" disabled={busy} onClick={() => onPurge(item)} aria-label={`${item.title}を完全削除`}>完全削除</button>
      </div>
      {item.changes && <dl>{item.changes.map((change, index) => <div key={index}>
        <dt>{recordNames[change.table] ?? "復旧対象"}</dt>
        <dd>{Object.entries(change.before).filter(([key]) => key in fieldNames).map(([key, value]) =>
          <p key={key} className="panel-copy">{fieldNames[key]}: {fieldValue(key, value)}</p>)}</dd>
      </div>)}</dl>}
    </article>)}
  </section>;
}
