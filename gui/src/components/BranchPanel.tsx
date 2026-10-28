import { useEffect, useState } from "react";
import type { BranchInfo, GraphCommit } from "../lib/sprout";

interface BranchPanelProps {
  branch: BranchInfo;
  /** Snapshot at the branch tip, or undefined before the branch's first commit. */
  tip: GraphCommit | undefined;
  busy: boolean;
  /** Resolve true when saved, so drafts survive a refused edit. */
  onRename: (branchId: string, name: string) => Promise<boolean>;
  onSetComment: (branchId: string, comment: string) => Promise<boolean>;
  onDelete: (branchId: string) => void;
  onOpenTip: (commitId: string) => void;
  onClose: () => void;
}

export default function BranchPanel({ branch, tip, busy, onRename, onSetComment, onDelete, onOpenTip, onClose }: BranchPanelProps) {
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(branch.name);
  const [editingComment, setEditingComment] = useState(false);
  const [commentDraft, setCommentDraft] = useState(branch.comment);

  // Keyed by ID: a rename keeps the panel on the same branch.
  useEffect(() => {
    setRenaming(false);
    setNameDraft(branch.name);
    setEditingComment(false);
    setCommentDraft(branch.comment);
  }, [branch.id, branch.name, branch.comment]);

  return (
    <section className="panel-section" aria-label="選択中のブランチ">
      <div className="panel-heading">
        <p className="eyebrow">{branch.current ? "現在のブランチ" : "BRANCH"}</p>
        <button className="icon-button" onClick={onClose} aria-label="詳細を閉じる">×</button>
      </div>

      {renaming ? (
        <form
          className="grow-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (nameDraft.trim()) void onRename(branch.id, nameDraft.trim()).then((saved) => saved && setRenaming(false));
          }}
        >
          <label className="field">
            新しい名前
            <input value={nameDraft} onChange={(event) => setNameDraft(event.currentTarget.value)} disabled={busy} />
          </label>
          <div className="action-row">
            <button className="button primary" type="submit" disabled={busy || !nameDraft.trim() || nameDraft.trim() === branch.name}>名前を変更</button>
            <button className="button secondary" type="button" onClick={() => { setNameDraft(branch.name); setRenaming(false); }} disabled={busy}>キャンセル</button>
          </div>
        </form>
      ) : (
        <div className="message-heading">
          <h3>{branch.name}</h3>
          <button className="text-button" onClick={() => setRenaming(true)} disabled={busy}>名前を変更</button>
        </div>
      )}

      <dl className="detail-list">
        <div>
          <dt>枝先</dt>
          <dd>
            {tip ? (
              <button className="text-button inline" onClick={() => onOpenTip(tip.id)} disabled={busy}>{`${tip.message}（${tip.id.slice(0, 12)}）`}</button>
            ) : "まだ保存がありません"}
          </dd>
        </div>
        <div><dt>ID</dt><dd className="mono">{branch.id.slice(0, 12)}</dd></div>
      </dl>

      <section className="annotation-section" aria-label="ブランチのコメント">
        <div className="annotation-heading">
          <h4>コメント</h4>
          {!editingComment && <button className="text-button" onClick={() => setEditingComment(true)} disabled={busy}>{branch.comment ? "コメントを編集" : "コメントを書く"}</button>}
        </div>
        {editingComment ? (
          <form
            className="inline-form"
            onSubmit={(event) => {
              event.preventDefault();
              void onSetComment(branch.id, commentDraft).then((saved) => saved && setEditingComment(false));
            }}
          >
            <input aria-label="ブランチのコメントを編集" value={commentDraft} onChange={(event) => setCommentDraft(event.currentTarget.value)} disabled={busy} />
            <button className="button primary small" type="submit" disabled={busy}>保存</button>
            <button className="button secondary small" type="button" onClick={() => { setCommentDraft(branch.comment); setEditingComment(false); }} disabled={busy}>キャンセル</button>
          </form>
        ) : branch.comment ? (
          <p className="note-text">{branch.comment}</p>
        ) : (
          <p className="muted">コメントはありません</p>
        )}
      </section>

      <div className="panel-actions">
        <button className="button danger" onClick={() => onDelete(branch.id)} disabled={busy || branch.current}>ブランチを削除</button>
      </div>
      {branch.current && <p className="panel-copy">現在のブランチは削除できません。別のブランチへ移動してから削除してください。</p>}
    </section>
  );
}
