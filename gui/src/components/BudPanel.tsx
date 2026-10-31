import { useEffect, useState } from "react";
import { branchIdentity, branchIdentityLabel, formatLocalTime, type BranchInfo, type Bud, type DeletedBranch } from "../lib/sprout";

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
  deletedBranches?: DeletedBranch[];
  busy: boolean;
  onRestore: (budId: string) => void;
  onDrop: (budId: string) => void;
  /** Resolves true when saved, so a refused name stays in the input. */
  onRename?: (budId: string, name: string) => Promise<boolean>;
  onClose: () => void;
}

export default function BudPanel({ bud, baseMessage, branches, deletedBranches = [], busy, onRestore, onDrop, onRename, onClose }: BudPanelProps) {
  const branch = branchIdentity(bud.branch_id, bud.branch_name, branches);
  const deletedBranch = deletedBranches.find((item) => item.id === bud.branch_id);
  const summary = baseMessage === null ? `最初の保存前の変更 ${bud.changes.length}件` : `「${baseMessage}」の上の変更 ${bud.changes.length}件`;
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(bud.name ?? "");

  useEffect(() => {
    setRenaming(false);
    setNameDraft(bud.name ?? "");
  }, [bud.id, bud.name]);

  return (
    <section className="panel-section" aria-label="つぼみ">
      <div className="panel-heading">
        <p className="eyebrow">つぼみ</p>
        <button className="icon-button" onClick={onClose} aria-label="詳細を閉じる">×</button>
      </div>
      {bud.name ? <h3>{bud.name}</h3> : <h3>{summary}</h3>}
      {bud.name && <p className="panel-copy">{summary}</p>}
      {onRename && (renaming ? (
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onRename(bud.id, nameDraft).then((saved) => saved && setRenaming(false));
          }}
        >
          <input aria-label="つぼみの名前" value={nameDraft} maxLength={256} onChange={(event) => setNameDraft(event.currentTarget.value)} disabled={busy} />
          <button className="button primary small" type="submit" disabled={busy}>保存</button>
          <button className="button secondary small" type="button" onClick={() => { setNameDraft(bud.name ?? ""); setRenaming(false); }} disabled={busy}>キャンセル</button>
        </form>
      ) : (
        <button className="text-button" onClick={() => setRenaming(true)} disabled={busy}>{bud.name ? "名前を編集" : "名前を付ける"}</button>
      ))}
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
      {branch.currentName === null && <p className="panel-copy">{`退避したブランチは${deletedBranch ? `${formatLocalTime(deletedBranch.deleted_at)}に` : ""}削除済みのため、戻しても今のブランチのままです。`}</p>}
    </section>
  );
}
