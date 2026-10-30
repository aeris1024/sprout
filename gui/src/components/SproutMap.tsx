import { useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent as ReactPointerEvent, type WheelEvent as ReactWheelEvent } from "react";
import { BRANCH_LABEL, LABEL_LINE, MAP, badgeWidth, budX, branchLabelText, estimateChipText, laneColor, lanePath, layoutSproutMap, leafCaption, pendingPath, tagChip, type MapLeaf, type TextMeasure } from "../lib/sproutMap";
import { loadThumbnailDataUrl, thumbnailCacheKey } from "../lib/thumbnails";
import { formatLocalTime, type Bud, type CommitAttachment, type CommitGraph } from "../lib/sprout";

/** Measure tag chip text with the page font; falls back to the estimate without a canvas (tests). */
function chipTextMeasure(): TextMeasure {
  let context: CanvasRenderingContext2D | null = null;
  try {
    context = document.createElement("canvas").getContext("2d");
  } catch {
    context = null;
  }
  if (!context) return estimateChipText;
  context.font = `600 11px ${getComputedStyle(document.body).fontFamily}`;
  const ctx = context;
  return (text) => ctx.measureText(text).width;
}

/** Search ignores letter case and Unicode composition, as paths do. */
function searchKey(text: string): string {
  return text.normalize("NFC").toLowerCase();
}

function leafMarks(leaf: MapLeaf): string {
  const marks = [];
  if (leaf.commit.note) marks.push("メモ");
  if (leaf.commit.labels.length) marks.push(`ラベル${leaf.commit.labels.length}`);
  return marks.join("・");
}

function leafDescription(leaf: MapLeaf): string {
  const marks = leafMarks(leaf);
  return [leaf.commit.message, formatLocalTime(leaf.commit.created_at), marks].filter(Boolean).join("\n");
}

const STATIC_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5];
/** Height of the 「未保存 · N件の変更」 band on top of the unsaved leaf. */
const BAND_HEIGHT = 20;

/** Stem and chip colors of a lane, taken from the theme. */
function laneStyle(lane: number): CSSProperties {
  const color = laneColor(lane);
  return { "--lane": `var(--branch-${color})`, "--lane-tag": `var(--tag-${color})` } as CSSProperties;
}

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

  return (
    <>
      <rect ref={anchor} className="leaf-box" x={leaf.leafX} y={leaf.leafY} width={MAP.leafWidth} height={MAP.leafHeight} />
      {source ? (
        <image
          href={source}
          x={leaf.leafX}
          y={leaf.leafY}
          width={MAP.leafWidth}
          height={MAP.leafHeight}
          preserveAspectRatio="xMidYMid slice"
          className="leaf-image"
          role="img"
          aria-label={`${leaf.commit.message}のサムネイル`}
        />
      ) : (
        <text className="leaf-placeholder" x={leaf.x} y={leaf.leafY + MAP.leafHeight / 2 + 4} textAnchor="middle">
          {failed ? "画像エラー" : "読込中"}
        </text>
      )}
    </>
  );
}

/** Short text on a bud; the full name stays available through its label. */
function budCaption(bud: Bud): string {
  if (!bud.name) return `つぼみ ${bud.changes.length}`;
  const characters = [...bud.name];
  return characters.length > 7 ? `${characters.slice(0, 6).join("")}…` : bud.name;
}

function budLabel(bud: Bud): string {
  if (bud.name) return `つぼみ「${bud.name}」（${bud.changes.length}件の変更）`;
  return bud.base_commit_id
    ? `つぼみ（${bud.changes.length}件の変更）`
    : `最初の保存前のつぼみ（${bud.changes.length}件の変更）`;
}

/** A small rounded label such as 「いまここ」 or 「選択中」. */
function Badge({ className, x, y, text, measure }: { className: string; x: number; y: number; text: string; measure: TextMeasure }) {
  const width = badgeWidth(text, measure);
  return (
    <g className={`map-badge ${className}`}>
      <rect x={x} y={y} width={width} height={18} />
      <text x={x + width / 2} y={y + 13} textAnchor="middle">{text}</text>
    </g>
  );
}

export type MapSelection = { kind: "commit" | "bud" | "branch"; id: string } | { kind: "unsaved" } | null;

interface SproutMapProps {
  graph: CommitGraph;
  selection: MapSelection;
  unsavedCount: number;
  projectDir: string;
  sproutProgram: string;
  onSelect: (commitId: string) => void;
  onSelectBud: (budId: string) => void;
  onSelectBranch: (branchId: string) => void;
  onSelectUnsaved: () => void;
}

export default function SproutMap({
  graph,
  selection,
  unsavedCount,
  projectDir,
  sproutProgram,
  onSelect,
  onSelectBud,
  onSelectBranch,
  onSelectUnsaved,
}: SproutMapProps) {
  const selectedId = selection?.kind === "commit" ? selection.id : null;
  const unsaved = unsavedCount > 0;
  const layout = useMemo(() => layoutSproutMap(graph, { unsaved }), [graph, unsaved]);
  const measureChip = useMemo(chipTextMeasure, []);
  const [zoomIndex, setZoomIndex] = useState(ZOOM_STEPS.indexOf(1));
  const zoom = ZOOM_STEPS[zoomIndex];
  const scroller = useRef<HTMLDivElement>(null);
  const currentLeaf = layout.leaves.find((leaf) => leaf.commit.id === layout.currentId);
  const zoomAnchor = useRef<{ x: number; y: number } | null>(null);
  const drag = useRef<{ pointer: number; x: number; y: number; left: number; top: number } | null>(null);
  const [panning, setPanning] = useState(false);
  const [hinted, setHinted] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(-1);
  const searchText = searchKey(query.trim());
  const matches = useMemo(() => searchText
    ? layout.leaves.filter((leaf) => [leaf.commit.message, ...leaf.tags, ...leaf.commit.labels].some((text) => searchKey(text).includes(searchText)))
    : [], [layout.leaves, searchText]);
  const matchIds = useMemo(() => new Set(matches.map((leaf) => leaf.commit.id)), [matches]);
  const hintedLeaf = layout.leaves.find((leaf) => leaf.commit.id === hinted);

  function changeQuery(value: string) {
    setQuery(value);
    setMatchIndex(-1);
  }

  function stepMatch(offset: number) {
    if (!matches.length) return;
    const next = matchIndex < 0
      ? (offset > 0 ? 0 : matches.length - 1)
      : (matchIndex + offset + matches.length) % matches.length;
    setMatchIndex(next);
    centerOn(matches[next]);
    onSelect(matches[next].commit.id);
  }

  /** The canvas is centered vertically when it is shorter than the scroll area. */
  const canvasTop = (element: HTMLElement, scale: number) => Math.max(0, (element.clientHeight - layout.height * scale) / 2);

  function centerOn(target: MapLeaf) {
    const element = scroller.current;
    if (!element || typeof element.scrollTo !== "function") return;
    element.scrollTo({
      top: (target.leafY + MAP.leafHeight / 2) * zoom + canvasTop(element, zoom) - element.clientHeight / 2,
      left: target.x * zoom - element.clientWidth / 2,
    });
  }

  function changeZoom(nextIndex: number) {
    const element = scroller.current;
    if (element) {
      zoomAnchor.current = {
        x: (element.scrollLeft + element.clientWidth / 2) / zoom,
        y: (element.scrollTop + element.clientHeight / 2 - canvasTop(element, zoom)) / zoom,
      };
    }
    setZoomIndex(nextIndex);
  }

  // Keep what was at the middle of the view there once the canvas has its new size.
  useLayoutEffect(() => {
    const element = scroller.current;
    const anchor = zoomAnchor.current;
    zoomAnchor.current = null;
    if (!element || !anchor) return;
    element.scrollLeft = anchor.x * zoom - element.clientWidth / 2;
    element.scrollTop = anchor.y * zoom + canvasTop(element, zoom) - element.clientHeight / 2;
  }, [zoom]);

  function onMapWheel(event: ReactWheelEvent<HTMLDivElement>) {
    const element = event.currentTarget;
    // Only a map that cannot scroll vertically turns the wheel into sideways movement.
    if (event.shiftKey || event.ctrlKey || event.deltaY === 0 || element.scrollHeight > element.clientHeight) return;
    element.scrollLeft += event.deltaY;
  }

  function onMapPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    const element = event.currentTarget;
    if (event.button !== 0 || (event.target as Element).closest?.('[role="button"], button')) return;
    const box = element.getBoundingClientRect();
    // Pressing a scrollbar keeps its own behaviour.
    if (event.clientX - box.left >= element.clientWidth || event.clientY - box.top >= element.clientHeight) return;
    drag.current = { pointer: event.pointerId, x: event.clientX, y: event.clientY, left: element.scrollLeft, top: element.scrollTop };
    element.setPointerCapture?.(event.pointerId);
    setPanning(true);
    event.preventDefault();
  }

  function onMapPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    event.currentTarget.scrollLeft = drag.current.left - (event.clientX - drag.current.x);
    event.currentTarget.scrollTop = drag.current.top - (event.clientY - drag.current.y);
  }

  function onMapPointerEnd() {
    drag.current = null;
    setPanning(false);
  }

  useEffect(() => {
    const element = scroller.current;
    const target = currentLeaf ?? layout.leaves[layout.leaves.length - 1];
    if (!element || !target || typeof element.scrollTo !== "function") return undefined;
    // Center the current leaf once the scroll area has a size; hidden windows report zero.
    const center = () => {
      if (element.clientHeight === 0) return false;
      centerOn(target);
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
  }, [projectDir, layout.currentId, layout.leaves.length]);

  if (layout.leaves.length === 0) {
    return (
      <div className="map-empty">
        <p className="eyebrow">NO SNAPSHOTS YET</p>
        <p>最初の保存をすると、ここに芽が出ます。</p>
        {layout.rootBuds.length > 0 && (
          <div className="root-bud-list" aria-label="最初の保存前のつぼみ">
            {layout.rootBuds.map(({ bud }) => (
              <button
                key={bud.id}
                className={`bud-button${selection?.kind === "bud" && selection.id === bud.id ? " selected" : ""}`}
                aria-label={budLabel(bud)}
                aria-pressed={selection?.kind === "bud" && selection.id === bud.id}
                onClick={() => onSelectBud(bud.id)}
              >
                {budCaption(bud)}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  function onKey(event: KeyboardEvent<SVGGElement>, action: () => void) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      action();
    }
  }

  function budNode(bud: Bud, x: number, y: number) {
    const selected = selection?.kind === "bud" && selection.id === bud.id;
    return (
      <g
        key={bud.id}
        className={`bud${selected ? " selected" : ""}`}
        role="button"
        tabIndex={0}
        aria-label={budLabel(bud)}
        aria-pressed={selected}
        onClick={() => onSelectBud(bud.id)}
        onKeyDown={(event) => onKey(event, () => onSelectBud(bud.id))}
      >
        <title>{budLabel(bud)}</title>
        <rect x={x} y={y} width={MAP.budWidth} height={MAP.budHeight} />
        <text x={x + MAP.budWidth / 2} y={y + 15} textAnchor="middle">{budCaption(bud)}</text>
      </g>
    );
  }

  const pending = layout.pending;
  const unsavedSelected = selection?.kind === "unsaved";
  const groundTop = MAP.top + 24;
  const groundBottom = Math.max(...layout.lanes.map((lane) => lane.y)) + 24;

  return (
    <div className="sprout-map">
      <div className="map-toolbar" aria-label="表示倍率">
        <button className="icon-button" onClick={() => changeZoom(Math.max(0, zoomIndex - 1))} disabled={zoomIndex === 0} aria-label="縮小">−</button>
        <span>{Math.round(zoom * 100)}%</span>
        <button className="icon-button" onClick={() => changeZoom(Math.min(ZOOM_STEPS.length - 1, zoomIndex + 1))} disabled={zoomIndex === ZOOM_STEPS.length - 1} aria-label="拡大">＋</button>
        {currentLeaf && <button className="button ghost small" onClick={() => centerOn(currentLeaf)}>いまここへ戻る</button>}
        <input
          className="map-search"
          aria-label="葉を検索"
          placeholder="メッセージ・タグ・ラベルで検索"
          value={query}
          onChange={(event) => changeQuery(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              stepMatch(event.shiftKey ? -1 : 1);
            } else if (event.key === "Escape") {
              changeQuery("");
            }
          }}
        />
        {searchText && (matches.length ? (
          <>
            <span role="status">{matchIndex < 0 ? `${matches.length}件` : `${matchIndex + 1} / ${matches.length}件`}</span>
            <button className="icon-button" onClick={() => stepMatch(-1)} aria-label="前の一致">↑</button>
            <button className="icon-button" onClick={() => stepMatch(1)} aria-label="次の一致">↓</button>
          </>
        ) : <span role="status">該当なし</span>)}
        {query && <button className="icon-button" onClick={() => changeQuery("")} aria-label="検索を解除">×</button>}
        {hintedLeaf && <span className="map-hint" title={leafDescription(hintedLeaf)}>{leafDescription(hintedLeaf).split("\n").join("・")}</span>}
      </div>
      <div
        className={`map-scroll${panning ? " panning" : ""}`}
        ref={scroller}
        onWheel={onMapWheel}
        onPointerDown={onMapPointerDown}
        onPointerMove={onMapPointerMove}
        onPointerUp={onMapPointerEnd}
        onPointerCancel={onMapPointerEnd}
      >
        <svg
          className="map-canvas"
          width={layout.width * zoom}
          height={layout.height * zoom}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="group"
          aria-label="芽のマップ"
        >
          <line className="ground" x1={MAP.groundX} x2={MAP.groundX} y1={groundTop} y2={groundBottom} />
          <text className="ground-label" x={MAP.groundX} y={groundBottom + 16} textAnchor="middle">はじまり</text>
          {pending && <path className="pending-stem" d={pendingPath(pending)} />}
          {layout.lanes.map((lane, index) => (
            <g key={lane.id} className="stem" style={laneStyle(index)}>
              <path d={lanePath(lane)} />
              {!lane.live && (
                <text className="lane-label" x={lane.endX + MAP.leafWidth / 2 + BRANCH_LABEL.endGap} y={lane.y + 4}>
                  {`削除済みブランチ由来: ${lane.name}`}
                </text>
              )}
            </g>
          ))}
          {layout.labels.map((label) => (
            <g key={`${label.x}:${label.y}`} className={`branch-label ${label.placement}`}>
              {label.placement === "below" && (
                <path d={`M${label.x + MAP.underRight} ${label.y - LABEL_LINE - MAP.underGap + 8} V${label.y - 4} H${label.x + 4}`} />
              )}
              {label.branches.map((branch, index) => {
                const selected = selection?.kind === "branch" && selection.id === branch.id;
                const textProps = label.placement === "end"
                  ? { x: label.x, y: label.y + 4 + (index - (label.branches.length - 1) / 2) * LABEL_LINE, textAnchor: "start" as const }
                  : { x: label.x, y: label.y + index * LABEL_LINE, textAnchor: "end" as const };
                return (
                  <g
                    key={branch.id}
                    className={`branch-name${branch.current ? " current" : ""}${selected ? " selected" : ""}`}
                    role="button"
                    tabIndex={0}
                    aria-label={`ブランチ ${branch.name}`}
                    aria-pressed={selected}
                    onClick={() => onSelectBranch(branch.id)}
                    onKeyDown={(event) => onKey(event, () => onSelectBranch(branch.id))}
                  >
                    <text {...textProps}>{branchLabelText(branch)}</text>
                  </g>
                );
              })}
            </g>
          ))}
          {layout.leaves.map((leaf) => {
            const here = leaf.commit.id === layout.currentId;
            const selected = leaf.commit.id === selectedId;
            const thumbnail = leaf.commit.attachments.find(
              (attachment) => attachment.role === "thumbnail" && STATIC_IMAGE_TYPES.has(attachment.media_type),
            );
            const top = leaf.leafY;
            return (
              <g
                key={leaf.commit.id}
                className={`leaf${here ? " here" : ""}${selected ? " selected" : ""}${searchText ? (matchIds.has(leaf.commit.id) ? " match" : " dimmed") : ""}`}
                style={laneStyle(leaf.lane)}
                role="button"
                tabIndex={0}
                aria-label={leaf.commit.message}
                aria-pressed={selected}
                onClick={() => onSelect(leaf.commit.id)}
                onKeyDown={(event) => onKey(event, () => onSelect(leaf.commit.id))}
                onMouseEnter={() => setHinted(leaf.commit.id)}
                onMouseLeave={() => setHinted(null)}
                onFocus={() => setHinted(leaf.commit.id)}
                onBlur={() => setHinted(null)}
              >
                <title>{leafDescription(leaf)}</title>
                <path className="leaf-stalk" d={`M${leaf.x} ${leaf.y} V${leaf.y - MAP.stalk + 4}`} />
                <circle className="node" cx={leaf.x} cy={leaf.y} r={here ? 7 : 6} />
                <rect className="leaf-card" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight + MAP.caption} />
                {thumbnail ? (
                  <LeafImage leaf={leaf} attachment={thumbnail} projectDir={projectDir} sproutProgram={sproutProgram} />
                ) : (
                  <>
                    <rect className="leaf-box empty" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight} />
                    <text className="leaf-placeholder" x={leaf.x} y={top + MAP.leafHeight / 2 + 4} textAnchor="middle">画像なし</text>
                  </>
                )}
                {here && <rect className="here-ring" x={leaf.leafX - 4} y={top - 4} width={MAP.leafWidth + 8} height={MAP.leafHeight + MAP.caption + 8} />}
                <rect className="leaf-frame" x={leaf.leafX} y={top} width={MAP.leafWidth} height={MAP.leafHeight + MAP.caption} />
                <text className="leaf-message" x={leaf.leafX + 6} y={top + MAP.leafHeight + 13}>
                  {leafCaption(leaf.commit.message, measureChip)}
                </text>
                {leaf.tags.map((tag, index) => {
                  const chip = tagChip(tag, measureChip);
                  return (
                    <g key={tag} className="tag-chip">
                      <title>{`#${tag}`}</title>
                      <rect x={leaf.leafX - 6} y={top - 9 + index * 22} width={chip.width} height={18} />
                      <text x={leaf.leafX} y={top + 4 + index * 22}>{chip.text}</text>
                    </g>
                  );
                })}
                {leafMarks(leaf) && <Badge className="marks-badge" x={leaf.leafX + MAP.leafWidth - 4 - badgeWidth(leafMarks(leaf), measureChip)} y={top + MAP.leafHeight - 22} text={leafMarks(leaf)} measure={measureChip} />}
                {here && <Badge className="here-badge" x={leaf.leafX + MAP.leafWidth + 6 - badgeWidth("いまここ", measureChip)} y={top - 10} text="いまここ" measure={measureChip} />}
                {selected && <Badge className="selected-badge" x={leaf.leafX - 6} y={top + MAP.leafHeight + MAP.caption - 2} text="選択中" measure={measureChip} />}
              </g>
            );
          })}
          {layout.leaves.flatMap((leaf) =>
            leaf.buds.map((bud, index) => budNode(bud, budX(leaf.x), leaf.y + MAP.underGap + index * MAP.budStep)),
          )}
          {layout.rootBuds.map(({ bud, x, y }) => budNode(bud, x, y))}
          {pending && (
            <g
              className={`unsaved-bud${unsavedSelected ? " selected" : ""}`}
              role="button"
              tabIndex={0}
              aria-label="未保存の芽"
              aria-pressed={unsavedSelected}
              onClick={onSelectUnsaved}
              onKeyDown={(event) => onKey(event, onSelectUnsaved)}
            >
              <path className="leaf-stalk" d={`M${pending.x} ${pending.y} V${pending.y - MAP.stalk + 4}`} />
              <circle className="node" cx={pending.x} cy={pending.y} r={6} />
              <rect className="unsaved-frame" x={pending.leafX} y={pending.leafY} width={MAP.leafWidth} height={MAP.leafHeight + MAP.caption} />
              <path className="unsaved-band" d={`M${pending.leafX} ${pending.leafY + BAND_HEIGHT} V${pending.leafY + 8} q0 -8 8 -8 H${pending.leafX + MAP.leafWidth - 8} q8 0 8 8 V${pending.leafY + BAND_HEIGHT} Z`} />
              <text className="unsaved-band-text" x={pending.leafX + 8} y={pending.leafY + 14}>{`未保存 · ${unsavedCount}件の変更`}</text>
              <text className="unsaved-text" x={pending.x} y={pending.leafY + BAND_HEIGHT + (MAP.leafHeight + MAP.caption - BAND_HEIGHT) / 2 + (pending.fork ? -4 : 4)} textAnchor="middle">
                未保存の芽
              </text>
              {pending.fork && (
                <text className="unsaved-note" x={pending.x} y={pending.leafY + BAND_HEIGHT + (MAP.leafHeight + MAP.caption - BAND_HEIGHT) / 2 + 14} textAnchor="middle">
                  保存すると新しい枝
                </text>
              )}
              {unsavedSelected && <Badge className="selected-badge" x={pending.leafX - 6} y={pending.leafY + MAP.leafHeight + MAP.caption - 2} text="選択中" measure={measureChip} />}
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}
