import { useEffect, useState, type ComponentProps } from "react";
import CommitAnnotations from "./CommitAnnotations";
import { branchIdentity, branchIdentityLabel, type BranchInfo, type CommitAttachment, type CommitDetail, type GraphTag } from "../lib/sprout";

const roleLabels: Record<string, string> = {
  thumbnail: "サムネイル",
  preview: "プレビュー",
};

function formatSize(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`;
  return `${(size / 1024 / 1024).toFixed(1)} MiB`;
}

function attachmentLabel(attachment: CommitAttachment): string {
  return `${roleLabels[attachment.role] ?? attachment.role}: ${attachment.original_name}（${attachment.media_type}・${formatSize(attachment.size)}）`;
}

interface CommitPanelProps {
  detail: CommitDetail;
  branches: BranchInfo[];
  tags: GraphTag[];
  current: boolean;
  unsavedCount: number;
  busy: boolean;
  onGo: (commitId: string) => void;
  onGrow: (commitId: string, branchName: string) => void;
  onSetThumbnail: (commitId: string) => void;
  onUpdateMessage: (commitId: string, message: string) => void;
  onExport: (commitId: string) => void;
  onDelete: (commitId: string) => void;
  onClose: () => void;
  annotations: Pick<ComponentProps<typeof CommitAnnotations>, "onSaveNote" | "onAddLabel" | "onRemoveLabel" | "onCreateTag" | "onSetTagComment" | "onDeleteTag">;
}

export default function CommitPanel({
  detail,
  branches,
  tags,
  current,
  unsavedCount,
  busy,
  onGo,
  onGrow,
  onSetThumbnail,
  onUpdateMessage,
  onExport,
  onDelete,
  onClose,
  annotations,
}: CommitPanelProps) {
  const [editingMessage, setEditingMessage] = useState(false);
  const [messageDraft, setMessageDraft] = useState(detail.message);
  const [growing, setGrowing] = useState(false);
  const [branchName, setBranchName] = useState("");
  const tips = branches.filter((branch) => branch.commit_id === detail.id);
  const commitTags = tags.filter((tag) => tag.commit_id === detail.id);

  useEffect(() => {
    setEditingMessage(false);
    setMessageDraft(detail.message);
    setGrowing(false);
    setBranchName("");
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
        <div><dt>ブランチ</dt><dd>{branchIdentityLabel(branchIdentity(detail.branch_id, detail.branch_name, branches))}</dd></div>
        {tips.length > 0 && <div><dt>枝先</dt><dd>{tips.map((branch) => branch.name).join(", ")}</dd></div>}
        <div>
          <dt>添付</dt>
          <dd>
            {detail.attachments.length === 0 ? "なし" : (
              <ul className="attachment-list" aria-label="添付">
                {detail.attachments.map((attachment) => <li key={attachment.id}>{attachmentLabel(attachment)}</li>)}
              </ul>
            )}
          </dd>
        </div>
        <div><dt>ファイル</dt><dd>{detail.files.length}件</dd></div>
        <div><dt>ID</dt><dd className="mono">{detail.id.slice(0, 12)}</dd></div>
      </dl>
      <div className="panel-actions">
        <button className="button primary" onClick={() => onGo(detail.id)} disabled={busy || current}>
          {current ? "この芽にいます" : "ここへ移動"}
        </button>
        {growing ? (
          <form
            className="grow-form"
            onSubmit={(event) => {
              event.preventDefault();
              if (branchName.trim()) onGrow(detail.id, branchName.trim());
            }}
          >
            <label className="field">
              新しい枝の名前
              <input value={branchName} onChange={(event) => setBranchName(event.currentTarget.value)} placeholder="例: rethink" disabled={busy} />
            </label>
            <div className="action-row">
              <button className="button primary" type="submit" disabled={busy || !branchName.trim()}>枝を作って移動</button>
              <button className="button secondary" type="button" onClick={() => setGrowing(false)} disabled={busy}>キャンセル</button>
            </div>
          </form>
        ) : (
          <button className="button secondary" onClick={() => setGrowing(true)} disabled={busy}>ここから枝を伸ばす</button>
        )}
        <button className="button secondary" onClick={() => onSetThumbnail(detail.id)} disabled={busy} title="Ctrl+Vでクリップボードの画像も登録できます">
          {detail.thumbnail ? "サムネイルを変更" : "サムネイルを登録"}
        </button>
        <button className="button secondary" onClick={() => onExport(detail.id)} disabled={busy}>ファイルを取り出す</button>
        <button
          className="button danger"
          onClick={() => onDelete(detail.id)}
          disabled={busy || commitTags.length > 0}
          title={commitTags.length > 0 ? "タグ付きの葉は削除できません。先にタグを外してください。" : "この葉だけを削除し、枝先・いまここ・子の芽は親へ移します"}
        >
          この葉を削除
        </button>
      </div>
      <CommitAnnotations detail={detail} tags={commitTags} busy={busy} {...annotations} />
      {!current && unsavedCount > 0 && (
        <p className="panel-copy">{`移動すると、未保存の変更 ${unsavedCount}件は今の芽につぼみとして残ります。`}</p>
      )}
    </section>
  );
}
