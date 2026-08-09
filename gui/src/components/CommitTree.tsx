import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { flattenCommitGraph } from "../lib/graph";
import { loadThumbnailDataUrl, thumbnailCacheKey } from "../lib/thumbnails";
import type { CommitAttachment, CommitDetail, CommitGraph } from "../lib/sprout";

const INITIAL_NODE_LIMIT = 80;
const STATIC_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);

interface ThumbnailProps {
  attachment: CommitAttachment;
  message: string;
  projectDir: string;
  sproutProgram: string;
}

function CommitThumbnailImage({ attachment, message, projectDir, sproutProgram }: ThumbnailProps) {
  const container = useRef<HTMLDivElement>(null);
  const [source, setSource] = useState("");
  const [failed, setFailed] = useState(false);
  const key = thumbnailCacheKey(projectDir, attachment);

  useEffect(() => {
    setSource("");
    setFailed(false);
    let active = true;
    let observer: IntersectionObserver | undefined;
    const load = () => {
      void loadThumbnailDataUrl(projectDir, attachment, sproutProgram)
        .then((value) => {
          if (active) setSource(value);
        })
        .catch(() => {
          if (active) setFailed(true);
        });
    };
    if (typeof IntersectionObserver === "undefined" || !container.current) {
      load();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            observer?.disconnect();
            load();
          }
        },
        { rootMargin: "240px" },
      );
      observer.observe(container.current);
    }
    return () => {
      active = false;
      observer?.disconnect();
    };
  }, [key, projectDir, sproutProgram]);

  return (
    <div className="tree-thumbnail" ref={container}>
      {source ? <img src={source} alt={`${message}のサムネイル`} /> : <span>{failed ? "画像エラー" : "画像読込中"}</span>}
    </div>
  );
}

interface CommitTreeProps {
  graph: CommitGraph;
  selectedId: string | null;
  detail: CommitDetail | null;
  projectDir: string;
  sproutProgram: string;
  busy: boolean;
  onSelect: (commitId: string) => void;
  onRestore: (commitId: string) => void;
  onSwitch: (branchName: string) => void;
  onSetThumbnail: (commitId: string) => void;
}

export default function CommitTree({
  graph,
  selectedId,
  detail,
  projectDir,
  sproutProgram,
  busy,
  onSelect,
  onRestore,
  onSwitch,
  onSetThumbnail,
}: CommitTreeProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const [nodeLimit, setNodeLimit] = useState(INITIAL_NODE_LIMIT);
  const flattened = useMemo(
    () => flattenCommitGraph(graph, collapsed, nodeLimit),
    [graph, collapsed, nodeLimit],
  );
  const liveBranchNames = useMemo(
    () => new Set(graph.branches.map((branch) => branch.name)),
    [graph.branches],
  );
  const selectedTips = detail
    ? graph.branches.filter((branch) => branch.commit_id === detail.id)
    : [];

  function toggle(commitId: string) {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(commitId)) next.delete(commitId);
      else next.add(commitId);
      return next;
    });
  }

  return (
    <div className="tree-layout">
      <section className="operation-card tree-card">
        <div className="card-heading">
          <div><p className="eyebrow">REPOSITORY TREE</p><h3>コミットツリー</h3></div>
          <span>{graph.commits.length}件</span>
        </div>
        <div className="tree-legend">
          <span><i className="legend-current" />現在の先端</span>
          <span><i className="legend-selected" />選択中</span>
          <span>全ブランチ・削除済みブランチ由来を表示</span>
        </div>
        {flattened.rows.length === 0 ? (
          <p className="muted padded">コミットはまだありません。</p>
        ) : (
          <div className="commit-tree" role="tree" aria-label="全コミットの親子ツリー">
            {flattened.rows.map((row) => {
              const thumbnail = row.commit.attachments.find(
                (attachment) => attachment.role === "thumbnail" && STATIC_IMAGE_TYPES.has(attachment.media_type),
              );
              const selected = selectedId === row.commit.id;
              const deletedOrigin = !liveBranchNames.has(row.commit.branch_name);
              return (
                <div
                  className={`tree-row${row.currentTip ? " current-tip" : ""}${selected ? " selected" : ""}`}
                  key={row.commit.id}
                  role="treeitem"
                  aria-level={row.depth + 1}
                  aria-selected={selected}
                  style={{ "--tree-depth": row.depth } as CSSProperties}
                >
                  <div className="tree-rail" aria-hidden="true" />
                  {row.hasChildren ? (
                    <button className="tree-toggle" onClick={() => toggle(row.commit.id)} aria-label={collapsed.has(row.commit.id) ? "子コミットを展開" : "子コミットを折りたたむ"} disabled={busy}>
                      {collapsed.has(row.commit.id) ? "+" : "−"}
                    </button>
                  ) : <span className="tree-dot" aria-hidden="true" />}
                  <button className="tree-node" onClick={() => onSelect(row.commit.id)} disabled={busy}>
                    {thumbnail ? <CommitThumbnailImage attachment={thumbnail} message={row.commit.message} projectDir={projectDir} sproutProgram={sproutProgram} /> : <div className="tree-thumbnail empty"><span>NO IMAGE</span></div>}
                    <span className="tree-node-copy">
                      <span className="tree-badges">
                        {row.currentTip && <b className="tip-badge current">現在の先端</b>}
                        {row.branchTips.filter((branch) => !branch.current).map((branch) => <b className="tip-badge" key={branch.name}>{branch.name}</b>)}
                        {row.tags.map((tag) => <b className="tag-badge" key={tag.name}>#{tag.name}</b>)}
                        {deletedOrigin && <b className="origin-badge">削除済み: {row.commit.branch_name}</b>}
                      </span>
                      <strong>{row.commit.message}</strong>
                      <small>{row.commit.id.slice(0, 12)} · {new Date(row.commit.created_at).toLocaleString("ja-JP")}</small>
                    </span>
                  </button>
                </div>
              );
            })}
          </div>
        )}
        {flattened.totalVisible > flattened.rows.length && (
          <button className="tree-more" onClick={() => setNodeLimit((value) => value + INITIAL_NODE_LIMIT)} disabled={busy}>
            さらに表示（残り{flattened.totalVisible - flattened.rows.length}件）
          </button>
        )}
      </section>

      <section className="operation-card tree-detail">
        {detail && selectedId === detail.id ? (
          <>
            <p className="eyebrow">SELECTED COMMIT</p>
            <h3>{detail.message}</h3>
            <dl>
              <div><dt>ID</dt><dd>{detail.id}</dd></div>
              <div><dt>作成ブランチ</dt><dd>{detail.branch_name}</dd></div>
              <div><dt>日時</dt><dd>{new Date(detail.created_at).toLocaleString("ja-JP")}</dd></div>
              <div><dt>ファイル</dt><dd>{detail.files.length}件</dd></div>
            </dl>
            <div className="tree-detail-actions">
              <button className="button danger" onClick={() => onRestore(detail.id)} disabled={busy}>このコミットを復元</button>
              <button className="button secondary" onClick={() => onSetThumbnail(detail.id)} disabled={busy}>{detail.thumbnail ? "サムネイルを変更" : "サムネイルを登録"}</button>
              {selectedTips.filter((branch) => !branch.current).map((branch) => (
                <button className="button secondary" onClick={() => onSwitch(branch.name)} disabled={busy} key={branch.name}>{branch.name}へ切り替え</button>
              ))}
            </div>
          </>
        ) : <div className="detail-empty">コミットノードを選択すると詳細と操作を表示します。</div>}
      </section>
    </div>
  );
}
