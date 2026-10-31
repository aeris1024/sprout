import { useRef, type KeyboardEvent, type PointerEvent } from "react";
import { PANEL_WIDTH, clampPanelWidth } from "../lib/panelWidth";

interface PanelSplitterProps {
  width: number;
  /** Follows the pointer or key; the width is not saved yet. */
  onResize: (width: number) => void;
  /** The final width to keep across restarts. */
  onCommit: (width: number) => void;
}

/** A jsdom or hidden workspace reports no width, which leaves only the fixed limits. */
function workspaceWidth(element: HTMLElement): number {
  return element.parentElement?.clientWidth || Infinity;
}

export default function PanelSplitter({ width, onResize, onCommit }: PanelSplitterProps) {
  const drag = useRef<{ pointer: number; x: number; width: number; latest: number } | null>(null);

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.button !== 0) return;
    const start = clampPanelWidth(width, workspaceWidth(event.currentTarget));
    drag.current = { pointer: event.pointerId, x: event.clientX, width: start, latest: start };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    // The panel is on the right, so moving left widens it.
    drag.current.latest = clampPanelWidth(drag.current.width + drag.current.x - event.clientX, workspaceWidth(event.currentTarget));
    onResize(drag.current.latest);
  }

  function onPointerEnd() {
    if (!drag.current) return;
    const { width: start, latest } = drag.current;
    drag.current = null;
    if (latest !== start) onCommit(latest);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const available = workspaceWidth(event.currentTarget);
    const current = clampPanelWidth(width, available);
    const targets: Record<string, number> = {
      ArrowLeft: current + PANEL_WIDTH.step,
      ArrowRight: current - PANEL_WIDTH.step,
      Home: PANEL_WIDTH.min,
      End: PANEL_WIDTH.max,
    };
    if (!(event.key in targets)) return;
    event.preventDefault();
    const next = clampPanelWidth(targets[event.key], available);
    onResize(next);
    onCommit(next);
  }

  return (
    <div
      className="panel-splitter"
      role="separator"
      aria-orientation="vertical"
      aria-label="パネルの幅"
      aria-valuemin={PANEL_WIDTH.min}
      aria-valuemax={PANEL_WIDTH.max}
      aria-valuenow={width}
      tabIndex={0}
      title="ドラッグでパネルの幅を変更（ダブルクリックで元の幅）"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerEnd}
      onPointerCancel={onPointerEnd}
      onDoubleClick={() => {
        onResize(PANEL_WIDTH.default);
        onCommit(PANEL_WIDTH.default);
      }}
      onKeyDown={onKeyDown}
    />
  );
}
