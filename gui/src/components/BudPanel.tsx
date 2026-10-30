import { branchIdentity, branchIdentityLabel, type BranchInfo, type Bud } from "../lib/sprout";

const stateLabels: Record<string, string> = {
  added: "追加",
  modified: "変更",
  deleted: "削除",
  renamed: "改名",
};

interface BudPanelProps {
  bud: Bud;
  /** Message of the snapshot the bud was kept on, or null when it was kept before the first commit. */
  baseMessage: string | null;
  branches: BranchInfo[];
  busy: boolean;
  onRestore: (budId: string) => void;
  onDrop: (budId: string) => void;
  onClose: () => void;
}

export default function BudPanel({ bud, baseMessage, branches, busy, onRestore, onDrop, onClose }: BudPanelProps) {
  const branch = branchIdentity(bud.branch_id, bud.branch_name, branches);
  return (
    <section className="panel-section" aria-label="つぼみ">
      <div className="panel-heading">
        <p className="eyebrow">BUD</p>
        <button className="icon-button" onClick={onClose} aria-label="詳細を閉じる">×</button>
      </div>
      <h3>{baseMessage === null ? `最初の保存前の変更 ${bud.changes.length}件` : `「${baseMessage}」の上の変更 ${bud.changes.length}件`}</h3>
      <p className="panel-copy">{`退避: ${new Date(bud.created_at).toLocaleString("ja-JP")}・${branchIdentityLabel(branch)}`}</p>
      <div className="change-list">
        {bud.changes.map((change) => (
          <div className="change-row" key={`${change.state}:${change.path}`}>
            <span className={`state-badge ${change.state}`}>{stateLabels[change.state] ?? change.state}</span>
            <span>{change.previous_path ? `${change.previous_path} → ${change.path}` : change.path}</span>
          </div>
        ))}
      </div>
      <div className="panel-actions">
        <button className="button primary" onClick={() => onRestore(bud.id)} disabled={busy}>このつぼみに戻る</button>
        <button className="button danger" onClick={() => onDrop(bud.id)} disabled={busy}>つぼみを捨てる</button>
      </div>
      <p className="panel-copy">戻すと、今の未保存の変更は新しいつぼみとして残ります。</p>
      {branch.currentName === null && <p className="panel-copy">退避したブランチは削除済みのため、戻しても今のブランチのままです。</p>}
    </section>
  );
}
