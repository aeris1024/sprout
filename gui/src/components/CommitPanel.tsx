import { useEffect, useState } from "react";
import type { BranchInfo, CommitDetail, GraphTag } from "../lib/sprout";

interface CommitPanelProps {
  detail: CommitDetail;
  branches: BranchInfo[];
  tags: GraphTag[];
  current: boolean;
  busy: boolean;
  onRestore: (commitId: string) => void;
  onSwitch: (branchName: string) => void;
  onSetThumbnail: (commitId: string) => void;
  onUpdateMessage: (commitId: string, message: string) => void;
  onClose: () => void;
}

export default function CommitPanel({
  detail,
  branches,
  tags,
  current,
  busy,
  onRestore,
  onSwitch,
  onSetThumbnail,
  onUpdateMessage,
  onClose,
}: CommitPanelProps) {
  const [editingMessage, setEditingMessage] = useState(false);
  const [messageDraft, setMessageDraft] = useState(detail.message);
  const tips = branches.filter((branch) => branch.commit_id === detail.id);
  const commitTags = tags.filter((tag) => tag.commit_id === detail.id).map((tag) => tag.name);

  useEffect(() => {
    setEditingMessage(false);
    setMessageDraft(detail.message);
  }, [detail.id, detail.message]);

  return (
    <section className="panel-section" aria-label="選択中のスナップショット">
      <div className="panel-heading">
        <p className="eyebrow">{current ? "いまここ" : "SNAPSHOT"}</p>
        <button className="icon-button" onClick={onClose} aria-label="詳細を閉じる">×</button>
      </div>
      {editingMessage ? (
        <form
          className="message-editor"
          onSubmit={(event) => {
            event.preventDefault();
            if (messageDraft.trim()) onUpdateMessage(detail.id, messageDraft);
          }}
        >
          <label className="field">
            コミットメッセージ
            <textarea aria-label="コミットメッセージを編集" value={messageDraft} onChange={(event) => setMessageDraft(event.currentTarget.value)} disabled={busy} />
          </label>
          <div className="action-row">
            <button className="button primary" type="submit" disabled={busy || !messageDraft.trim()}>保存</button>
            <button className="button secondary" type="button" onClick={() => { setMessageDraft(detail.message); setEditingMessage(false); }} disabled={busy}>キャンセル</button>
          </div>
        </form>
      ) : (
        <div className="message-heading">
          <h3>{detail.message}</h3>
          <button className="text-button" onClick={() => setEditingMessage(true)} disabled={busy}>メッセージを編集</button>
        </div>
      )}
      <dl className="detail-list">
        <div><dt>日時</dt><dd>{new Date(detail.created_at).toLocaleString("ja-JP")}</dd></div>
        <div><dt>作成ブランチ</dt><dd>{detail.branch_name}</dd></div>
        {tips.length > 0 && <div><dt>枝先</dt><dd>{tips.map((branch) => branch.name).join(", ")}</dd></div>}
        {commitTags.length > 0 && <div><dt>タグ</dt><dd>{commitTags.map((tag) => `#${tag}`).join(" ")}</dd></div>}
        <div><dt>ファイル</dt><dd>{detail.files.length}件</dd></div>
        <div><dt>ID</dt><dd className="mono">{detail.id.slice(0, 12)}</dd></div>
      </dl>
      <div className="panel-actions">
        <button className="button primary" onClick={() => onRestore(detail.id)} disabled={busy}>このコミットを復元</button>
        <button className="button secondary" onClick={() => onSetThumbnail(detail.id)} disabled={busy}>
          {detail.thumbnail ? "サムネイルを変更" : "サムネイルを登録"}
        </button>
        {tips.filter((branch) => !branch.current).map((branch) => (
          <button className="button secondary" onClick={() => onSwitch(branch.name)} disabled={busy} key={branch.name}>{branch.name}へ切り替え</button>
        ))}
      </div>
    </section>
  );
}
