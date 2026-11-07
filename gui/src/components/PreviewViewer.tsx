import { useEffect, useId, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { formatBytes, normalizeCliError, type CommitAttachment } from "../lib/sprout";
import { cachedPreviewImage, isViewableImage, loadPreviewImage, previewImageKey, type PreviewImageData } from "../lib/previewImages";

interface PreviewViewerProps {
  projectDir: string;
  program: string;
  /** The leaf's message, shown above the preview name. */
  leafTitle: string;
  /** Previews of one leaf in their saved order. */
  previews: CommitAttachment[];
  startId: string;
  busy: boolean;
  onExport: (id: string, name: string) => void;
  onClose: () => void;
}

type ImageState = { key: string; image?: PreviewImageData; error?: string };

const FOCUSABLE = 'button:not(:disabled), [href], input:not(:disabled), [tabindex]:not([tabindex="-1"])';

function previewName(item: CommitAttachment): string {
  return item.display_name || item.original_name;
}

function sizeText(image: PreviewImageData): string {
  const reduced = image.width !== image.display_width || image.height !== image.display_height;
  const original = `${image.format ? `${image.format} · ` : ""}元の寸法 ${image.width} × ${image.height} px`;
  return reduced ? `${original}（表示用に ${image.display_width} × ${image.display_height} px へ縮小済み）` : original;
}

/** The element that had the keyboard before the viewer opened, or the map's tab stop if it is gone. */
function restoreFocus(element: Element | null) {
  const target = element instanceof HTMLElement || element instanceof SVGElement ? element : null;
  if (target?.isConnected) target.focus();
  else document.querySelector<HTMLElement>('[data-map-node][tabindex="0"]')?.focus();
}

/** A modal over the whole window for looking through one leaf's previews. */
export default function PreviewViewer({ projectDir, program, leafTitle, previews, startId, busy, onExport, onClose }: PreviewViewerProps) {
  const titleId = useId();
  const dialog = useRef<HTMLDivElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const [currentId, setCurrentId] = useState(startId);
  const lastIndex = useRef(0);
  const found = previews.findIndex((item) => item.id === currentId);
  // A preview removed while shown gives way to the one now at its place.
  const index = found >= 0 ? found : Math.min(lastIndex.current, previews.length - 1);
  lastIndex.current = index;
  const current = previews[index];
  const [actualSize, setActualSize] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ImageState>({ key: "" });
  const drag = useRef<{ pointer: number; x: number; y: number; left: number; top: number; moved: boolean } | null>(null);
  /** Set when a drag ends, so the click that follows does not switch the size. */
  const dragged = useRef(false);
  const viewable = Boolean(current && isViewableImage(current));
  const key = current ? previewImageKey(projectDir, program, current) : "";
  const image = state.key === key ? state.image : cachedPreviewImage(key);
  const error = state.key === key ? state.error : undefined;

  useLayoutEffect(() => {
    const opener = document.activeElement;
    dialog.current?.focus();
    return () => restoreFocus(opener);
  }, []);

  useEffect(() => {
    if (!current || !viewable) return undefined;
    let active = true;
    setState({ key });
    void loadPreviewImage(projectDir, program, current)
      .then((value) => { if (active) setState({ key, image: value }); })
      .catch((cause) => { if (active) setState({ key, error: normalizeCliError(cause).message }); });
    return () => { active = false; };
  }, [key, viewable, attempt]);

  // Each preview starts at the top left of its own picture.
  useLayoutEffect(() => {
    stage.current?.scrollTo?.({ left: 0, top: 0 });
  }, [key]);

  if (!current) return null;

  function step(offset: number) {
    if (previews.length < 2) return;
    setCurrentId(previews[(index + offset + previews.length) % previews.length].id);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    // Keys pressed in the viewer never reach the map, the panels or the window's shortcuts.
    event.stopPropagation();
    if (event.nativeEvent.isComposing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      step(event.key === "ArrowLeft" ? -1 : 1);
    } else if (event.key === "Tab") {
      const items = Array.from(dialog.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
      if (!items.length) return;
      const position = items.indexOf(document.activeElement as HTMLElement);
      const next = event.shiftKey ? (position <= 0 ? items.length - 1 : position - 1) : (position < 0 || position === items.length - 1 ? 0 : position + 1);
      event.preventDefault();
      items[next].focus();
    }
  }

  function onStagePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    dragged.current = false;
    if (event.button !== 0 || !actualSize) return;
    const element = event.currentTarget;
    drag.current = { pointer: event.pointerId, x: event.clientX, y: event.clientY, left: element.scrollLeft, top: element.scrollTop, moved: false };
    element.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function onStagePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    const start = drag.current;
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) start.moved = true;
    event.currentTarget.scrollLeft = start.left - dx;
    event.currentTarget.scrollTop = start.top - dy;
  }

  function onStagePointerUp() {
    const moved = drag.current?.moved ?? false;
    drag.current = null;
    if (moved) dragged.current = true;
  }

  function toggleSize() {
    if (dragged.current) { dragged.current = false; return; }
    setActualSize((value) => !value);
  }

  const ratio = typeof window !== "undefined" && window.devicePixelRatio > 0 ? window.devicePixelRatio : 1;
  const name = previewName(current);
  let content;
  if (!viewable) {
    content = <div className="viewer-card">
      <p>この形式はここでは表示できません。取り出して確認してください。</p>
      <p className="panel-copy">{current.media_type} · {formatBytes(current.size)}</p>
      <button className="button secondary" disabled={busy} onClick={() => onExport(current.id, current.original_name)}>取り出す</button>
    </div>;
  } else if (error) {
    content = <div className="viewer-card" role="alert">
      <p>{error}</p>
      <p className="panel-copy">{current.media_type} · {formatBytes(current.size)}</p>
      <div className="action-row">
        <button className="button secondary" onClick={() => setAttempt((value) => value + 1)}>画像を再読み込み</button>
        <button className="button secondary" disabled={busy} onClick={() => onExport(current.id, current.original_name)}>取り出す</button>
      </div>
    </div>;
  } else if (image) {
    const width = image.display_width / ratio;
    const height = image.display_height / ratio;
    content = <img
      className={`viewer-image${actualSize ? " actual" : ""}`}
      src={image.data_url}
      alt={name}
      draggable={false}
      // Fitting keeps the aspect ratio by limiting an auto size; actual size fixes it to screen pixels.
      style={actualSize ? { width: `${width}px`, height: `${height}px` } : { maxWidth: `min(100%, ${width}px)`, maxHeight: `min(100%, ${height}px)` }}
      onClick={toggleSize}
      onError={() => setState({ key, error: "画像を表示できませんでした。取り出して確認してください。" })}
    />;
  } else {
    content = <p className="viewer-loading" role="status">画像を読み込み中…</p>;
  }

  return createPortal(
    <div
      className="viewer-backdrop"
      onPointerDown={(event) => { if (event.target === event.currentTarget) onClose(); }}
      onKeyDown={onKeyDown}
      onPaste={(event) => { event.stopPropagation(); event.preventDefault(); }}
    >
      <div
        className="viewer"
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onBlur={(event) => {
          // A button disabled while it has the keyboard drops it on the page; keep it in the viewer.
          if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
          requestAnimationFrame(() => {
            const element = dialog.current;
            if (element && !element.contains(document.activeElement)) element.focus();
          });
        }}
      >
        <header className="viewer-head">
          <div className="viewer-title">
            <p className="eyebrow">{leafTitle}</p>
            <h2 id={titleId}>{name}</h2>
          </div>
          <span className="viewer-position" aria-label={`${previews.length}件中${index + 1}件目`}>{index + 1} / {previews.length}</span>
          <button
            className={`button secondary small${actualSize ? " pressed" : ""}`}
            aria-pressed={actualSize}
            onClick={() => setActualSize((value) => !value)}
            title="表示用画像の1ピクセルを画面の1ピクセルで表示します"
          >等倍</button>
          <button className="icon-button" onClick={onClose} aria-label="プレビューの表示を閉じる">×</button>
        </header>
        <div className="viewer-body">
          {previews.length > 1 && <button className="viewer-nav" onClick={() => step(-1)} aria-label="前のプレビュー">‹</button>}
          <div
            ref={stage}
            className={`viewer-stage${actualSize ? " actual" : ""}`}
            onPointerDown={onStagePointerDown}
            onPointerMove={onStagePointerMove}
            onPointerUp={onStagePointerUp}
            onPointerCancel={onStagePointerUp}
          >
            {content}
          </div>
          {previews.length > 1 && <button className="viewer-nav" onClick={() => step(1)} aria-label="次のプレビュー">›</button>}
        </div>
        <footer className="viewer-foot">
          <p className="panel-copy">
            {image && !error ? `${sizeText(image)} · ${actualSize ? "等倍で表示中（ドラッグで移動）" : "ウィンドウに合わせて表示中"}` : `${current.media_type} · ${formatBytes(current.size)}`}
          </p>
          {current.description && <p className="viewer-description">{current.description}</p>}
          {previews.length > 1 && <ol className="viewer-list" aria-label="プレビューの一覧">
            {previews.map((item, position) => <li key={item.id}>
              <button
                className={`viewer-list-item${position === index ? " current" : ""}`}
                aria-current={position === index ? "true" : undefined}
                onClick={() => setCurrentId(item.id)}
              >{`${position + 1}. ${previewName(item)}`}{isViewableImage(item) ? "" : "（画像以外）"}</button>
            </li>)}
          </ol>}
        </footer>
      </div>
    </div>,
    document.body,
  );
}
