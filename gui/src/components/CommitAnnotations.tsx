import { useEffect, useState } from "react";
import type { CommitDetail, GraphTag } from "../lib/sprout";

/** Resolves true when the edit was saved, so drafts survive a refused edit. */
type Edit = Promise<boolean>;

interface CommitAnnotationsProps {
  detail: CommitDetail;
  tags: GraphTag[];
  busy: boolean;
  onSaveNote: (commitId: string, note: string) => Edit;
  onAddLabel: (commitId: string, label: string) => Edit;
  onRemoveLabel: (commitId: string, label: string) => Edit;
  onCreateTag: (commitId: string, name: string, comment: string) => Edit;
  onSetTagComment: (name: string, comment: string) => Edit;
  onDeleteTag: (name: string) => void;
}

function TagRow({ tag, busy, onSetTagComment, onDeleteTag }: { tag: GraphTag; busy: boolean; onSetTagComment: (name: string, comment: string) => Edit; onDeleteTag: (name: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(tag.comment);

  useEffect(() => {
    setEditing(false);
    setDraft(tag.comment);
  }, [tag.name, tag.comment]);

  return (
    <li className="tag-row">
      <span className="tag-name">{`#${tag.name}`}</span>
      {editing ? (
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            void onSetTagComment(tag.name, draft).then((saved) => saved && setEditing(false));
          }}
        >
          <input aria-label={`タグ「${tag.name}」のコメント`} value={draft} onChange={(event) => setDraft(event.currentTarget.value)} disabled={busy} />
          <button className="button primary small" type="submit" disabled={busy}>保存</button>
          <button className="button secondary small" type="button" onClick={() => { setDraft(tag.comment); setEditing(false); }} disabled={busy}>キャンセル</button>
        </form>
      ) : (
        <>
          <span className="tag-comment">{tag.comment || "コメントなし"}</span>
          <button className="text-button" onClick={() => setEditing(true)} disabled={busy} aria-label={`タグ「${tag.name}」のコメントを編集`}>編集</button>
          <button className="text-button danger" onClick={() => onDeleteTag(tag.name)} disabled={busy} aria-label={`タグ「${tag.name}」を削除`}>削除</button>
        </>
      )}
    </li>
  );
}

export default function CommitAnnotations({ detail, tags, busy, onSaveNote, onAddLabel, onRemoveLabel, onCreateTag, onSetTagComment, onDeleteTag }: CommitAnnotationsProps) {
  const [editingNote, setEditingNote] = useState(false);
  const [noteDraft, setNoteDraft] = useState(detail.note ?? "");
  const [labelDraft, setLabelDraft] = useState("");
  const [tagName, setTagName] = useState("");
  const [tagComment, setTagComment] = useState("");

  useEffect(() => {
    setEditingNote(false);
    setNoteDraft(detail.note ?? "");
    setLabelDraft("");
    setTagName("");
    setTagComment("");
  }, [detail.id]);

  useEffect(() => {
    if (!editingNote) setNoteDraft(detail.note ?? "");
  }, [detail.note]);

  return (
    <>
      <section className="annotation-section" aria-label="メモ">
        <div className="annotation-heading">
          <h4>メモ</h4>
          {!editingNote && <button className="text-button" onClick={() => setEditingNote(true)} disabled={busy}>{detail.note ? "メモを編集" : "メモを書く"}</button>}
        </div>
        {editingNote ? (
          <form
            className="message-editor"
            onSubmit={(event) => {
              event.preventDefault();
              void onSaveNote(detail.id, noteDraft).then((saved) => saved && setEditingNote(false));
            }}
          >
            <textarea aria-label="メモを編集" value={noteDraft} onChange={(event) => setNoteDraft(event.currentTarget.value)} disabled={busy} />
            <p className="field-hint">空にして保存するとメモをゴミ箱へ移します（20,000文字まで）。</p>
            <div className="action-row">
              <button className="button primary" type="submit" disabled={busy}>保存</button>
              <button className="button secondary" type="button" onClick={() => { setNoteDraft(detail.note ?? ""); setEditingNote(false); }} disabled={busy}>キャンセル</button>
            </div>
          </form>
        ) : detail.note ? (
          <p className="note-text">{detail.note}</p>
        ) : (
          <p className="muted">メモはありません</p>
        )}
      </section>

      <section className="annotation-section" aria-label="ラベル">
        <h4>ラベル</h4>
        {detail.labels.length > 0 ? (
          <ul className="label-list">
            {detail.labels.map((label) => (
              <li key={label} className="label-chip">
                <span>{label}</span>
                <button onClick={() => void onRemoveLabel(detail.id, label)} disabled={busy} aria-label={`ラベル「${label}」を外す`}>×</button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">ラベルはありません</p>
        )}
        <form
          className="inline-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (labelDraft.trim()) void onAddLabel(detail.id, labelDraft).then((saved) => saved && setLabelDraft(""));
          }}
        >
          <input aria-label="追加するラベル" placeholder="例: 承認済み" value={labelDraft} onChange={(event) => setLabelDraft(event.currentTarget.value)} disabled={busy} />
          <button className="button secondary small" type="submit" disabled={busy || !labelDraft.trim()}>追加</button>
        </form>
      </section>

      <section className="annotation-section" aria-label="タグ">
        <h4>タグ</h4>
        {tags.length > 0 ? (
          <ul className="tag-list">
            {tags.map((tag) => <TagRow key={tag.name} tag={tag} busy={busy} onSetTagComment={onSetTagComment} onDeleteTag={onDeleteTag} />)}
          </ul>
        ) : (
          <p className="muted">タグはありません</p>
        )}
        <form
          className="tag-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!tagName.trim()) return;
            void onCreateTag(detail.id, tagName.trim(), tagComment).then((saved) => {
              if (!saved) return;
              setTagName("");
              setTagComment("");
            });
          }}
        >
          <input aria-label="新しいタグの名前" placeholder="タグ名（例: 提出版）" value={tagName} onChange={(event) => setTagName(event.currentTarget.value)} disabled={busy} />
          <input aria-label="新しいタグのコメント" placeholder="コメント（任意）" value={tagComment} onChange={(event) => setTagComment(event.currentTarget.value)} disabled={busy} />
          <button className="button secondary small" type="submit" disabled={busy || !tagName.trim()}>タグを付ける</button>
        </form>
      </section>
    </>
  );
}
