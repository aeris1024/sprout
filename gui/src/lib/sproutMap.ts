import type { BranchInfo, Bud, CommitGraph, GraphCommit } from "./sprout";

export const MAP = {
  /** Horizontal distance between snapshots; each snapshot has its own column. */
  column: 148,
  leafWidth: 112,
  leafHeight: 72,
  /** Line from a node up to the message under its leaf. */
  stalk: 22,
  /** Height of the message line under a leaf. */
  caption: 18,
  /** Room above a lane's stem for leaves and their badges. */
  above: 142,
  /** Minimum room below a lane's stem. */
  below: 34,
  /** Gap between the stem and the first bud or name under a node. */
  underGap: 14,
  top: 12,
  bottom: 24,
  /** X of the ground line that stems without a fork grow from. */
  groundX: 36,
  left: 108,
  right: 48,
  budWidth: 84,
  budHeight: 22,
  budStep: 28,
  /** Left edge of the first bud kept before the first commit. */
  rootBudLeft: 24,
  /** How far buds and hanging names under a node reach right of it, clear of a fork curving out. */
  underRight: 10,
};

/** Number of stem colors the theme defines (`--branch-1` and onward). */
export const LANE_COLORS = 5;

export function laneColor(lane: number): number {
  return (lane % LANE_COLORS) + 1;
}

export interface MapLeaf {
  commit: GraphCommit;
  lane: number;
  /** Node on the stem. */
  x: number;
  y: number;
  /** Top-left corner of the leaf rectangle above the node. */
  leafX: number;
  leafY: number;
  tags: string[];
  buds: Bud[];
}

export interface MapLane {
  id: string;
  name: string;
  /** Y of the stem; the lane grows to the right along it. */
  y: number;
  /** Fork point on the parent lane, or null when the lane grows from the ground. */
  fork: { x: number; y: number } | null;
  startX: number;
  endX: number;
  live: boolean;
}

/** A bud kept before the first commit, placed below the map because it has no leaf. */
export interface MapRootBud {
  bud: Bud;
  x: number;
  y: number;
}

/**
 * Names of the live branches whose tip is one leaf. At the end of a stem they follow it on the right;
 * on a leaf partway along a stem they hang below the node, under its buds, so they cover no leaf.
 * Things under a node sit to its left, because a fork curves out of the node to the right:
 * `x` of hanging names is their right edge and `y` the baseline of the first name.
 */
export type MapLabel =
  | { placement: "end"; x: number; y: number; branches: BranchInfo[]; current: boolean }
  | { placement: "below"; x: number; y: number; nodeY: number; branches: BranchInfo[]; current: boolean };

/**
 * Where unsaved changes would be saved. After the tip of the current branch they continue its stem;
 * anywhere else saving grows a new branch, so they get a row of their own forking from the current leaf.
 */
export interface MapPending {
  x: number;
  y: number;
  leafX: number;
  leafY: number;
  from: { x: number; y: number };
  fork: boolean;
}

/** Vertical distance between stacked branch names. */
export const LABEL_LINE = 18;

/** Geometry of branch names: gap after a stem end, and the font scale relative to tag chips. */
export const BRANCH_LABEL = { endGap: 20, fontScale: 13 / 11, margin: 12 };

export function branchLabelText(branch: BranchInfo): string {
  return branch.current ? `${branch.name}（現在のブランチ）` : branch.name;
}

function labelWidth(label: MapLabel): number {
  return Math.max(...label.branches.map((branch) => estimateChipText(branchLabelText(branch)) * BRANCH_LABEL.fontScale));
}

/** Horizontal extent of a label, used to keep it inside the map. */
function labelExtent(label: MapLabel): { left: number; right: number } {
  const width = labelWidth(label);
  return label.placement === "end" ? { left: label.x, right: label.x + width } : { left: label.x - width, right: label.x };
}

/** Approximate advance widths of the 11px tag chip font, wide enough for Yu Gothic UI and fallbacks. */
const CHIP_FONT = { narrow: 7, wide: 11.5, padding: 12 };
const WIDE_CHARACTER = /[ᄀ-ᅟ⺀-꓏가-힣豈-﫿︰-﹏＀-｠￠-￦\u{20000}-\u{3fffd}]/u;

/** Measures rendered text width; the estimate is used where no font metrics are available. */
export type TextMeasure = (text: string) => number;

export function estimateChipText(text: string): number {
  let width = 0;
  for (const character of text) width += WIDE_CHARACTER.test(character) ? CHIP_FONT.wide : CHIP_FONT.narrow;
  return width;
}

/** Width of a badge such as 「いまここ」 drawn with the tag chip font. */
export function badgeWidth(text: string, measure: TextMeasure = estimateChipText): number {
  return Math.ceil(measure(text)) + CHIP_FONT.padding;
}

/** Label and width of a leaf's tag chip; names that do not fit the leaf end with an ellipsis. */
export function tagChip(tag: string, measure: TextMeasure = estimateChipText): { text: string; width: number } {
  const maxWidth = MAP.leafWidth - 12;
  const characters = [...`#${tag}`];
  let text = characters.join("");
  while (characters.length > 1 && measure(text) + CHIP_FONT.padding > maxWidth) {
    characters.pop();
    text = `${characters.join("")}…`;
  }
  return { text, width: Math.min(maxWidth, Math.ceil(measure(text)) + CHIP_FONT.padding) };
}

/** Leaf message shortened with an ellipsis to fit under the leaf; messages use a 12px font. */
export function leafCaption(message: string, measure: TextMeasure = estimateChipText): string {
  const maxWidth = MAP.leafWidth - 12;
  const characters = [...message];
  let text = message;
  while (characters.length > 1 && measure(text) * (12 / 11) > maxWidth) {
    characters.pop();
    text = `${characters.join("")}…`;
  }
  return text;
}

/** Curve from a node down to a lower row, reaching it before the next column's leaf. */
export function forkPath(from: { x: number; y: number }, toY: number, endX: number): string {
  const { x, y } = from;
  return `M${x} ${y} C${x + 40} ${y} ${x + 20} ${toY} ${x + 80} ${toY} H${Math.max(endX, x + 80)}`;
}

/** Path of a lane's stem: from the ground, or curving down out of its fork. */
export function lanePath(lane: MapLane): string {
  return lane.fork ? forkPath(lane.fork, lane.y, lane.endX) : `M${MAP.groundX} ${lane.y} H${lane.endX}`;
}

/** Left edge of the buds under a node. */
export function budX(nodeX: number): number {
  return nodeX + MAP.underRight - MAP.budWidth;
}

/** Path from the current leaf to the unsaved changes. */
export function pendingPath(pending: MapPending): string {
  return pending.fork ? forkPath(pending.from, pending.y, pending.x) : `M${pending.from.x} ${pending.y} H${pending.x}`;
}

export interface SproutMapLayout {
  leaves: MapLeaf[];
  lanes: MapLane[];
  labels: MapLabel[];
  rootBuds: MapRootBud[];
  pending: MapPending | null;
  width: number;
  height: number;
  currentId: string | null;
}

export interface LayoutOptions {
  /** Whether the working tree has unsaved changes to show next to the current leaf. */
  unsaved?: boolean;
}

/**
 * The CLI lists commits newest first by creation sequence, independent of clocks.
 * Parents are always placed before their children.
 */
function oldestFirst(commits: GraphCommit[]): GraphCommit[] {
  const sorted = [...commits].reverse();
  const byId = new Map(sorted.map((commit) => [commit.id, commit]));
  const placed = new Set<string>();
  const result: GraphCommit[] = [];
  for (const commit of sorted) {
    const chain: GraphCommit[] = [];
    let cursor: GraphCommit | undefined = commit;
    while (cursor && !placed.has(cursor.id)) {
      placed.add(cursor.id);
      chain.push(cursor);
      cursor = cursor.parent_id ? byId.get(cursor.parent_id) : undefined;
    }
    result.push(...chain.reverse());
  }
  return result;
}

/** Lay out commits oldest-at-left, one column per commit and one row per branch the commits were created on. */
export function layoutSproutMap(graph: CommitGraph, options: LayoutOptions = {}): SproutMapLayout {
  const layout = layoutFrom(graph, options, MAP.left);
  // Long names hanging below the first snapshots may need more room on the left than the default margin.
  const minLeft = Math.min(Infinity, ...layout.labels.map((label) => labelExtent(label).left));
  const shift = Number.isFinite(minLeft) ? Math.max(0, Math.ceil(BRANCH_LABEL.margin - minLeft)) : 0;
  return shift ? layoutFrom(graph, options, MAP.left + shift) : layout;
}

function layoutFrom(graph: CommitGraph, options: LayoutOptions, left: number): SproutMapLayout {
  const ordered = oldestFirst(graph.commits);
  const ids = new Set(ordered.map((commit) => commit.id));
  const laneIds: string[] = [];
  for (const commit of ordered) {
    if (!laneIds.includes(commit.branch_id)) laneIds.push(commit.branch_id);
  }
  const column = new Map(ordered.map((commit, index) => [commit.id, index]));
  const laneOf = (commit: GraphCommit) => laneIds.indexOf(commit.branch_id);
  const lastInLane = new Map<number, GraphCommit>();
  for (const commit of ordered) lastInLane.set(laneOf(commit), commit);

  const tagsByCommit = new Map<string, string[]>();
  for (const tag of graph.tags) tagsByCommit.set(tag.commit_id, [...(tagsByCommit.get(tag.commit_id) ?? []), tag.name]);
  const budsByCommit = new Map<string, Bud[]>();
  const rootBudList: Bud[] = [];
  for (const bud of graph.buds) {
    if (bud.base_commit_id && ids.has(bud.base_commit_id)) budsByCommit.set(bud.base_commit_id, [...(budsByCommit.get(bud.base_commit_id) ?? []), bud]);
    else if (!bud.base_commit_id) rootBudList.push(bud);
  }

  const byId = new Map(ordered.map((commit) => [commit.id, commit]));
  const current = graph.current_commit ? byId.get(graph.current_commit) : undefined;
  const currentBranch = graph.branches.find((branch) => branch.current);
  // Saving extends the stem only from the tip of the current branch's own lane; elsewhere it grows a new branch.
  const extendsLane = Boolean(
    current && currentBranch && currentBranch.id === current.branch_id && currentBranch.commit_id === current.id
      && lastInLane.get(laneOf(current))?.id === current.id,
  );
  const pendingRow = options.unsaved && current && !extendsLane ? laneOf(current) + 1 : -1;
  /** Visual row of a lane, leaving room for a new branch's row right after the current one. */
  const rowOf = (lane: number) => (pendingRow >= 0 && lane >= pendingRow ? lane + 1 : lane);
  const rowCount = laneIds.length + (pendingRow >= 0 ? 1 : 0);

  const xOf = (commit: GraphCommit) => left + (column.get(commit.id) ?? 0) * MAP.column;
  const pendingX = current ? xOf(current) + MAP.column : 0;

  // Names of branches whose tip is partway along a stem hang below that node, under its buds.
  const labelsByCommit = new Map<string, BranchInfo[]>();
  for (const branch of graph.branches) {
    if (branch.commit_id && ids.has(branch.commit_id)) labelsByCommit.set(branch.commit_id, [...(labelsByCommit.get(branch.commit_id) ?? []), branch]);
  }
  const isEnd = (commit: GraphCommit) => lastInLane.get(laneOf(commit))?.id === commit.id;
  const belowNeeded = (commit: GraphCommit) => {
    const buds = budsByCommit.get(commit.id)?.length ?? 0;
    const names = isEnd(commit) ? 0 : labelsByCommit.get(commit.id)?.length ?? 0;
    return MAP.underGap + buds * MAP.budStep + (names ? names * LABEL_LINE + 8 : 0) + 8;
  };
  const below = Array.from({ length: rowCount }, () => MAP.below);
  for (const commit of ordered) {
    const row = rowOf(laneOf(commit));
    below[row] = Math.max(below[row], belowNeeded(commit));
  }
  const rowY: number[] = [];
  let cursor = MAP.top;
  for (let row = 0; row < rowCount; row += 1) {
    rowY.push(cursor + MAP.above);
    cursor += MAP.above + below[row];
  }

  const leaves: MapLeaf[] = ordered.map((commit) => {
    const lane = laneOf(commit);
    const x = xOf(commit);
    const y = rowY[rowOf(lane)];
    return {
      commit,
      lane,
      x,
      y,
      leafX: x - MAP.leafWidth / 2,
      leafY: y - MAP.stalk - MAP.caption - MAP.leafHeight,
      tags: tagsByCommit.get(commit.id) ?? [],
      buds: budsByCommit.get(commit.id) ?? [],
    };
  });
  const leafById = new Map(leaves.map((leaf) => [leaf.commit.id, leaf]));
  const currentLeaf = current ? leafById.get(current.id) : undefined;

  let pending: MapPending | null = null;
  if (options.unsaved && currentLeaf) {
    const y = pendingRow >= 0 ? rowY[pendingRow] : currentLeaf.y;
    pending = {
      x: pendingX,
      y,
      leafX: pendingX - MAP.leafWidth / 2,
      leafY: y - MAP.stalk - MAP.caption - MAP.leafHeight,
      from: { x: currentLeaf.x, y: currentLeaf.y },
      fork: pendingRow >= 0,
    };
  }

  const liveIds = new Set(graph.branches.map((branch) => branch.id));
  const lanes: MapLane[] = laneIds.map((id, index) => {
    const members = leaves.filter((leaf) => leaf.lane === index);
    const first = members[0];
    const last = members[members.length - 1];
    const parent = first.commit.parent_id && ids.has(first.commit.parent_id) ? leafById.get(first.commit.parent_id) : undefined;
    return {
      id,
      name: graph.branches.find((branch) => branch.id === id)?.name ?? first.commit.branch_name,
      y: first.y,
      fork: parent && parent.lane !== index ? { x: parent.x, y: parent.y } : null,
      startX: first.x,
      endX: last.x,
      live: liveIds.has(id),
    };
  });

  const labels: MapLabel[] = [];
  for (const [commitId, branches] of labelsByCommit) {
    const leaf = leafById.get(commitId)!;
    const currentFlag = branches.some((branch) => branch.current);
    if (isEnd(leaf.commit)) {
      // Unsaved changes continuing this stem come first; the names follow them.
      const after = pending && !pending.fork && pending.from.x === leaf.x && pending.y === leaf.y ? pending.x : leaf.x;
      labels.push({ placement: "end", x: after + MAP.leafWidth / 2 + BRANCH_LABEL.endGap, y: leaf.y, branches, current: currentFlag });
    } else {
      labels.push({ placement: "below", x: leaf.x - MAP.underRight, y: leaf.y + MAP.underGap + leaf.buds.length * MAP.budStep + LABEL_LINE, nodeY: leaf.y, branches, current: currentFlag });
    }
  }

  const rootTop = cursor + 8;
  const rootBuds = rootBudList.map((bud, index) => ({ bud, x: MAP.rootBudLeft + index * (MAP.budWidth + 8), y: rootTop }));

  const lastX = leaves.length ? leaves[leaves.length - 1].x : left;
  const right = Math.max(
    lastX + MAP.leafWidth / 2 + MAP.right,
    pending ? pending.x + MAP.leafWidth / 2 + MAP.right : 0,
    ...labels.map((label) => labelExtent(label).right + BRANCH_LABEL.margin),
    rootBuds.length ? rootBuds[rootBuds.length - 1].x + MAP.budWidth + 24 : 0,
  );
  return {
    leaves,
    lanes,
    labels,
    rootBuds,
    pending,
    width: Math.ceil(right),
    height: (rootBuds.length ? rootTop + MAP.budHeight : cursor) + MAP.bottom,
    // The CLI records the position explicitly; a missing one is never guessed from a branch tip.
    currentId: graph.current_commit,
  };
}
