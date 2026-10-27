import type { Bud } from "../lib/sprout";

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
};

interface BudPanelProps {
  bud: Bud;
  baseMessage: string;
  busy: boolean;
  onRestore: (budId: string) => void;
  onDrop: (budId: string) => void;
  onClose: () => void;
}

export default function BudPanel({ bud, baseMessage, busy, onRestore, onDrop, onClose }: BudPanelProps) {
  return (
    <section className="panel-section" aria-label="つぼみ">
      <div className="panel-heading">
        <p className="eyebrow">BUD</p>
        <button className="icon-button" onClick={onClose} aria-label="詳細を閉じる">×</button>
      </div>
      <h3>{`「${baseMessage}」の上の変更 ${bud.changes.length}件`}</h3>
      <p className="panel-copy">{`退避: ${new Date(bud.created_at).toLocaleString("ja-JP")}・${bud.branch_name}`}</p>
      <div className="change-list">
        {bud.changes.map((change) => (
          <div className="change-row" key={`${change.state}:${change.path}`}>
            <span className={`state-badge ${change.state}`}>{stateLabels[change.state] ?? change.state}</span>
            <span>{change.path}</span>
          </div>
        ))}
      </div>
      <div className="panel-actions">
        <button className="button primary" onClick={() => onRestore(bud.id)} disabled={busy}>このつぼみに戻る</button>
        <button className="button danger" onClick={() => onDrop(bud.id)} disabled={busy}>つぼみを捨てる</button>
      </div>
      <p className="panel-copy">戻すと、今の未保存の変更は新しいつぼみとして残ります。</p>
    </section>
  );
}
