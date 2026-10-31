import { useEffect, useId, useRef, useState, type ComponentProps, type RefObject } from "react";
import PreviewPanel, { type PreviewActions } from "./PreviewPanel";
import SnapshotFiles from "./SnapshotFiles";
import CommitAnnotations from "./CommitAnnotations";
import { branchIdentity, branchIdentityLabel, formatBytes, formatLocalTime, type BranchInfo, type CommitAttachment, type CommitDetail, type DeletedBranch, type GraphTag } from "../lib/sprout";

const roleLabels: Record<string, string> = {
  thumbnail: "サムネイル",
  preview: "プレビュー",
};

function attachmentLabel(attachment: CommitAttachment): string {
  return `${roleLabels[attachment.role] ?? attachment.role}: ${attachment.original_name}（${attachment.media_type}・${formatBytes(attachment.size)}）`;
}

/** Bring a section under the sticky links and put the keyboard there. */
function jumpTo(section: RefObject<HTMLDivElement | null>) {
  section.current?.scrollIntoView?.({ block: "start" });
  section.current?.focus({ preventScroll: true });
}

interface CommitPanelProps {
  detail: CommitDetail;
  projectDir: string;
  program: string;
  branches: BranchInfo[];
  deletedBranches?: DeletedBranch[];
  tags: GraphTag[];
  current: boolean;
  unsavedCount: number;
  busy: boolean;
  onGo: (commitId: string) => void;
  onGrow: (commitId: string, branchName: string) => void;
  onSetThumbnail: (commitId: string) => void;
  onUpdateMessage: (commitId: string, message: string) => void;
  onExport: (commitId: string, paths?: string[]) => void;
  onRestoreFiles: (commitId: string, paths: string[]) => void;
  onCompare: (commitId: string) => void;
  onDelete: (commitId: string) => void;
  onClose: () => void;
  previews: PreviewActions;
  annotations: Pick<ComponentProps<typeof CommitAnnotations>, "onSaveNote" | "onAddLabel" | "onRemoveLabel" | "onCreateTag" | "onSetTagComment" | "onDeleteTag">;
}

export default function CommitPanel({
  detail,
  projectDir,
  program,
  branches,
  deletedBranches = [],
  tags,
  current,
  unsavedCount,
  busy,
  onGo,
  onGrow,
  onSetThumbnail,
  onUpdateMessage,
  onExport,
  onRestoreFiles,
  onCompare,
  onDelete,
  onClose,
  annotations,
  previews,
}: CommitPanelProps) {
  const [editingMessage, setEditingMessage] = useState(false);
  const [messageDraft, setMessageDraft] = useState(detail.message);
  const [growing, setGrowing] = useState(false);
  const [branchName, setBranchName] = useState("");
  const tips = branches.filter((branch) => branch.commit_id === detail.id);
  const commitTags = tags.filter((tag) => tag.commit_id === detail.id);
  const deletedBranch = deletedBranches.find((branch) => branch.id === detail.branch_id);
  const annotationSection = useRef<HTMLDivElement>(null);
  const previewSection = useRef<HTMLDivElement>(null);
  const fileSection = useRef<HTMLDivElement>(null);
  const menuRoot = useRef<HTMLDivElement>(null);
  const menuTrigger = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const menuContext = `${projectDir}:${detail.id}`;
  const [menuTarget, setMenuTarget] = useState<string | null>(null);
  const menuOpen = menuTarget === menuContext && !busy;

  function closeMenu(restoreFocus = false) {
    setMenuTarget(null);
    if (restoreFocus) menuTrigger.current?.focus();
  }

  useEffect(() => { setMenuTarget(null); }, [projectDir, detail.id, busy]);

  useEffect(() => {
    if (!menuOpen) return;
    menuRoot.current?.querySelector<HTMLButtonElement>('[role="menuitem"]:not(:disabled)')?.focus();
    const outside = (event: PointerEvent) => {
      if (!menuRoot.current?.contains(event.target as Node)) setMenuTarget(null);
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [menuOpen]);

  useEffect(() => {
    setEditingMessage(false);
    setMessageDraft(detail.message);
    setGrowing(false);
    setBranchName("");
  }, [detail.id, detail.message]);

  return (
    <section className="panel-section commit-panel" aria-label="選択中の葉">
      <div className="panel-heading">
        <p className="eyebrow">{current ? "いまここ" : "葉"}</p>
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
            メッセージ
            <textarea aria-label="メッセージを編集" value={messageDraft} onChange={(event) => setMessageDraft(event.currentTarget.value)} disabled={busy} />
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
      <div className="panel-actions commit-actions">
        <button className="button primary span-all" onClick={() => onGo(detail.id)} disabled={busy || current}>
          {current ? "この葉にいます" : "ここへ移動"}
        </button>
        {!current && unsavedCount > 0 && (
          <p className="panel-copy span-all">{`移動すると、未保存の変更 ${unsavedCount}件は今の葉につぼみとして残ります。`}</p>
        )}
        {growing ? (
          <form
            className="grow-form span-all"
            onSubmit={(event) => {
              event.preventDefault();
              if (branchName.trim()) onGrow(detail.id, branchName.trim());
            }}
          >
            <label className="field">
              新しいブランチの名前
              <input value={branchName} onChange={(event) => setBranchName(event.currentTarget.value)} placeholder="例: rethink" disabled={busy} />
            </label>
            <div className="action-row">
              <button className="button primary" type="submit" disabled={busy || !branchName.trim()}>ブランチを作って移動</button>
              <button className="button secondary" type="button" onClick={() => setGrowing(false)} disabled={busy}>キャンセル</button>
            </div>
          </form>
        ) : (
          <button className="button secondary" onClick={() => setGrowing(true)} disabled={busy} title="この葉から新しいブランチを作って移動します">ブランチを作る</button>
        )}
        <button className="button secondary" onClick={() => onCompare(detail.id)} disabled={busy}>比較元にする</button>
        <div
          className="leaf-actions span-all"
          ref={menuRoot}
          onBlur={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) closeMenu();
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" && menuOpen) {
              event.preventDefault();
              event.stopPropagation();
              closeMenu(true);
            } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
              event.preventDefault();
              if (!menuOpen) { if (!busy) setMenuTarget(menuContext); return; }
              const items = Array.from(menuRoot.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)') ?? []);
              const index = items.indexOf(document.activeElement as HTMLButtonElement);
              const next = event.key === "Home" ? 0 : event.key === "End" ? items.length - 1 : (index + (event.key === "ArrowUp" ? -1 : 1) + items.length) % items.length;
              items[next]?.focus();
            }
          }}
        >
          <button className="button secondary" ref={menuTrigger} aria-haspopup="menu" aria-expanded={menuOpen} aria-controls={menuOpen ? menuId : undefined} disabled={busy} onClick={() => menuOpen ? closeMenu() : setMenuTarget(menuContext)}>その他の操作 <span aria-hidden="true">▾</span></button>
          {menuOpen && (
            <div className="leaf-actions-menu" id={menuId} role="menu" aria-label="葉の補助操作">
              <button className="button secondary" role="menuitem" onClick={() => { closeMenu(true); onSetThumbnail(detail.id); }} title="Ctrl+Vでクリップボードの画像も登録できます">
                {detail.thumbnail ? "サムネイルを変更" : "サムネイルを登録"}
              </button>
              <button className="button secondary" role="menuitem" onClick={() => { closeMenu(true); onExport(detail.id); }}>ファイルを取り出す</button>
              <button
                className="button danger"
                role="menuitem"
                onClick={() => { closeMenu(true); onDelete(detail.id); }}
                disabled={commitTags.length > 0}
                aria-describedby={commitTags.length > 0 ? `${menuId}-delete-reason` : undefined}
                title={commitTags.length > 0 ? "タグ付きの葉は削除できません。先にタグを外してください。" : "この葉だけを削除し、先端にしているブランチ・いまここ・子の葉は親へ移します"}
              >この葉を削除</button>
              {commitTags.length > 0 && <p id={`${menuId}-delete-reason`} className="field-hint">タグ付きの葉は削除できません。先にタグを外してください。</p>}
            </div>
          )}
        </div>
      </div>
      <nav className="section-nav" aria-label="葉の詳細の移動先">
        <button type="button" onClick={() => jumpTo(annotationSection)}>メモ・ラベル・タグ</button>
        <button type="button" onClick={() => jumpTo(previewSection)}>プレビュー</button>
        <button type="button" onClick={() => jumpTo(fileSection)}>保存済みファイル</button>
      </nav>
      <dl className="detail-list">
        <div><dt>日時</dt><dd>{new Date(detail.created_at).toLocaleString("ja-JP")}</dd></div>
        <div><dt>ブランチ</dt><dd>{branchIdentityLabel(branchIdentity(detail.branch_id, detail.branch_name, branches))}</dd></div>
        {deletedBranch && <div><dt>ブランチの削除</dt><dd>{formatLocalTime(deletedBranch.deleted_at)}</dd></div>}
        {tips.length > 0 && <div><dt>先端のブランチ</dt><dd>{tips.map((branch) => branch.name).join(", ")}</dd></div>}
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
      <div className="section-target" ref={annotationSection} tabIndex={-1}>
        <CommitAnnotations detail={detail} tags={commitTags} busy={busy} {...annotations} />
      </div>
      <div className="section-target" ref={previewSection} tabIndex={-1}>
        <PreviewPanel key={`${projectDir}:${detail.id}`} projectDir={projectDir} program={program} commitId={detail.id} attachments={detail.attachments} busy={busy} actions={previews} />
      </div>
      <div className="section-target" ref={fileSection} tabIndex={-1}>
        <SnapshotFiles key={detail.id} files={detail.files} busy={busy} onExport={(paths) => onExport(detail.id, paths)} onRestore={(paths) => onRestoreFiles(detail.id, paths)} />
      </div>
    </section>
  );
}
