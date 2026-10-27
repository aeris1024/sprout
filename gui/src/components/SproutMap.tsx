import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { MAP, lanePath, layoutSproutMap, type MapLeaf } from "../lib/sproutMap";
import { loadThumbnailDataUrl, thumbnailCacheKey } from "../lib/thumbnails";
import type { CommitAttachment, CommitGraph } from "../lib/sprout";

const STATIC_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5];

interface LeafImageProps {
  leaf: MapLeaf;
  attachment: CommitAttachment;
  projectDir: string;
  sproutProgram: string;
}

function LeafImage({ leaf, attachment, projectDir, sproutProgram }: LeafImageProps) {
  const anchor = useRef<SVGRectElement>(null);
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
        .then((value) => active && setSource(value))
        .catch(() => active && setFailed(true));
    };
    if (typeof IntersectionObserver === "undefined" || !anchor.current) {
      load();
    } else {
      // Load leaves near the visible part of the map first.
      observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            observer?.disconnect();
            load();
          }
        },
        { rootMargin: "320px" },
      );
      observer.observe(anchor.current);
    }
    return () => {
      active = false;
      observer?.disconnect();
    };
  }, [key, projectDir, sproutProgram]);

  const top = leaf.y - MAP.leafHeight / 2;
  return (
    <>
      <rect ref={anchor} className="leaf-box" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight} />
      {source ? (
        <image
          href={source}
          x={leaf.leafX}
          y={top}
          width={MAP.leafWidth}
          height={MAP.leafHeight}
          preserveAspectRatio="xMidYMid slice"
          className="leaf-image"
          role="img"
          aria-label={`${leaf.commit.message}のサムネイル`}
        />
      ) : (
        <text className="leaf-placeholder" x={leaf.leafX + MAP.leafWidth / 2} y={leaf.y + 4} textAnchor="middle">
          {failed ? "画像エラー" : "読込中"}
        </text>
      )}
    </>
  );
}

export type MapSelection = { kind: "commit" | "bud"; id: string } | { kind: "unsaved" } | null;

interface SproutMapProps {
  graph: CommitGraph;
  selection: MapSelection;
  unsavedCount: number;
  projectDir: string;
  sproutProgram: string;
  onSelect: (commitId: string) => void;
  onSelectBud: (budId: string) => void;
  onSelectUnsaved: () => void;
}

const BUD_WIDTH = 84;

export default function SproutMap({
  graph,
  selection,
  unsavedCount,
  projectDir,
  sproutProgram,
  onSelect,
  onSelectBud,
  onSelectUnsaved,
}: SproutMapProps) {
  const selectedId = selection?.kind === "commit" ? selection.id : null;
  const layout = useMemo(() => layoutSproutMap(graph), [graph]);
  const [zoomIndex, setZoomIndex] = useState(ZOOM_STEPS.indexOf(1));
  const zoom = ZOOM_STEPS[zoomIndex];
  const scroller = useRef<HTMLDivElement>(null);
  const currentLeaf = layout.leaves.find((leaf) => leaf.commit.id === layout.currentId);

  useEffect(() => {
    const element = scroller.current;
    const target = currentLeaf ?? layout.leaves[layout.leaves.length - 1];
    if (!element || !target || typeof element.scrollTo !== "function") return undefined;
    // Center the current leaf once the scroll area has a size; hidden windows report zero.
    const center = () => {
      if (element.clientHeight === 0) return false;
      const offsetX = Math.max(0, (element.clientWidth - layout.width * zoom) / 2);
      element.scrollTo({
        top: target.y * zoom - element.clientHeight / 2,
        left: target.x * zoom + offsetX - element.clientWidth / 2,
      });
      return true;
    };
    const frame = requestAnimationFrame(center);
    if (typeof ResizeObserver === "undefined") return () => cancelAnimationFrame(frame);
    const observer = new ResizeObserver(() => {
      if (center()) observer.disconnect();
    });
    observer.observe(element);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [projectDir, layout.currentId, layout.leaves.length, zoom]);

  if (layout.leaves.length === 0) {
    return (
      <div className="map-empty">
        <p className="eyebrow">NO SNAPSHOTS YET</p>
        <p>最初の保存をすると、ここに芽が出ます。</p>
      </div>
    );
  }

  function onKey(event: KeyboardEvent<SVGGElement>, action: () => void) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      action();
    }
  }

  return (
    <div className="sprout-map">
      <div className="map-toolbar" aria-label="表示倍率">
        <button className="icon-button" onClick={() => setZoomIndex(Math.max(0, zoomIndex - 1))} disabled={zoomIndex === 0} aria-label="縮小">−</button>
        <span>{Math.round(zoom * 100)}%</span>
        <button className="icon-button" onClick={() => setZoomIndex(Math.min(ZOOM_STEPS.length - 1, zoomIndex + 1))} disabled={zoomIndex === ZOOM_STEPS.length - 1} aria-label="拡大">＋</button>
      </div>
      <div className="map-scroll" ref={scroller}>
        <svg
          className="map-canvas"
          width={layout.width * zoom}
          height={layout.height * zoom}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="group"
          aria-label="芽のマップ"
        >
          <line className="ground" x1={24} x2={layout.width - 24} y1={layout.groundY + 8} y2={layout.groundY + 8} />
          <text className="ground-label" x={32} y={layout.groundY + 28}>はじまり</text>
          {layout.lanes.map((lane, index) => (
            <g key={lane.name} className={index === 0 ? "stem main" : "stem"}>
              <path d={lanePath(lane, layout.groundY + 8)} />
              {!lane.live && (
                <text className="lane-label" x={lane.x} y={lane.topY - MAP.row + 12} textAnchor="middle">
                  {`削除済みブランチ由来: ${lane.name}`}
                </text>
              )}
            </g>
          ))}
          {layout.labels.map((label) => (
            <g key={`${label.x}:${label.y}`} className={label.current ? "branch-label current" : "branch-label"}>
              <line x1={label.x} x2={label.x} y1={label.y + 8} y2={label.y + MAP.row - 8} />
              <text x={label.x} y={label.y} textAnchor="middle">
                {label.names.join(", ")}
                {label.current ? "（現在のブランチ）" : ""}
              </text>
            </g>
          ))}
          {layout.leaves.map((leaf) => {
            const here = leaf.commit.id === layout.currentId;
            const selected = leaf.commit.id === selectedId;
            const thumbnail = leaf.commit.attachments.find(
              (attachment) => attachment.role === "thumbnail" && STATIC_IMAGE_TYPES.has(attachment.media_type),
            );
            const top = leaf.y - MAP.leafHeight / 2;
            return (
              <g
                key={leaf.commit.id}
                className={`leaf${here ? " here" : ""}${selected ? " selected" : ""}`}
                role="button"
                tabIndex={0}
                aria-label={leaf.commit.message}
                aria-pressed={selected}
                onClick={() => onSelect(leaf.commit.id)}
                onKeyDown={(event) => onKey(event, () => onSelect(leaf.commit.id))}
              >
                <path className="leaf-stalk" d={`M${leaf.x} ${leaf.y} H${leaf.side < 0 ? leaf.leafX + MAP.leafWidth : leaf.leafX}`} />
                <circle className="node" cx={leaf.x} cy={leaf.y} r={here ? 7 : 5} />
                {thumbnail ? (
                  <LeafImage leaf={leaf} attachment={thumbnail} projectDir={projectDir} sproutProgram={sproutProgram} />
                ) : (
                  <>
                    <rect className="leaf-box empty" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight} />
                    <text className="leaf-placeholder" x={leaf.leafX + MAP.leafWidth / 2} y={leaf.y + 4} textAnchor="middle">画像なし</text>
                  </>
                )}
                <rect className="leaf-frame" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight} />
                <text className="leaf-message" x={leaf.leafX} y={top + MAP.leafHeight + 15}>
                  {leaf.commit.message.length > 14 ? `${leaf.commit.message.slice(0, 14)}…` : leaf.commit.message}
                </text>
                {leaf.tags.map((tag, index) => (
                  <g key={tag} className="tag-chip">
                    <rect x={leaf.leafX + 6} y={top + 6 + index * 22} width={Math.min(MAP.leafWidth - 12, 16 + tag.length * 8)} height={18} />
                    <text x={leaf.leafX + 12} y={top + 19 + index * 22}>{`#${tag}`}</text>
                  </g>
                ))}
                {here && (
                  <text className="here-label" x={leaf.side < 0 ? leaf.leafX : leaf.leafX + MAP.leafWidth} y={top - 8} textAnchor={leaf.side < 0 ? "start" : "end"}>
                    いまここ
                  </text>
                )}
              </g>
            );
          })}
          {layout.leaves.flatMap((leaf) =>
            leaf.buds.map((bud, index) => {
              const x = leaf.side < 0 ? leaf.leafX + MAP.leafWidth - BUD_WIDTH : leaf.leafX;
              const y = leaf.y + MAP.leafHeight / 2 + 24 + index * 28;
              const selected = selection?.kind === "bud" && selection.id === bud.id;
              return (
                <g
                  key={bud.id}
                  className={`bud${selected ? " selected" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`つぼみ（${bud.changes.length}件の変更）`}
                  aria-pressed={selected}
                  onClick={() => onSelectBud(bud.id)}
                  onKeyDown={(event) => onKey(event, () => onSelectBud(bud.id))}
                >
                  <rect x={x} y={y} width={BUD_WIDTH} height={22} />
                  <text x={x + BUD_WIDTH / 2} y={y + 15} textAnchor="middle">{`つぼみ ${bud.changes.length}`}</text>
                </g>
              );
            }),
          )}
          {currentLeaf && unsavedCount > 0 && (
            <g
              className={`unsaved-bud${selection?.kind === "unsaved" ? " selected" : ""}`}
              role="button"
              tabIndex={0}
              aria-label="未保存の芽"
              aria-pressed={selection?.kind === "unsaved"}
              onClick={onSelectUnsaved}
              onKeyDown={(event) => onKey(event, onSelectUnsaved)}
            >
              <rect x={currentLeaf.leafX + 10} y={currentLeaf.y - MAP.leafHeight / 2 - 52} width={MAP.leafWidth - 20} height={28} />
              <text x={currentLeaf.leafX + MAP.leafWidth / 2} y={currentLeaf.y - MAP.leafHeight / 2 - 33} textAnchor="middle">
                {`未保存の芽 ${unsavedCount}`}
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}
