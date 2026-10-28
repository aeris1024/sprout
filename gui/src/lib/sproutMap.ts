import type { BranchInfo, Bud, CommitGraph, GraphCommit } from "./sprout";

export const MAP = {
  row: 96,
  lane: 280,
  leafWidth: 112,
  leafHeight: 72,
  gap: 18,
  top: 120,
  bottom: 64,
  left: 160,
  budWidth: 84,
  budHeight: 22,
  /** Left edge of the first bud kept before the first commit, right of the ground label. */
  rootBudLeft: 120,
};

export interface MapLeaf {
  commit: GraphCommit;
  lane: number;
  side: -1 | 1;
  x: number;
  y: number;
  /** Left edge of the leaf rectangle. */
  leafX: number;
  tags: string[];
  buds: Bud[];
}

export interface MapLane {
  id: string;
  name: string;
  x: number;
  /** Fork point on the parent lane and the side its leaf sits on, or null when the lane grows from the ground. */
  fork: { x: number; y: number; side: -1 | 1 } | null;
  bottomY: number;
  topY: number;
  live: boolean;
}

/** A bud kept before the first commit, placed on the ground because it has no leaf. */
export interface MapRootBud {
  bud: Bud;
  x: number;
  y: number;
}

/** Names of the live branches whose tip is one leaf, stacked above it. */
export interface MapLabel {
  x: number;
  y: number;
  branches: BranchInfo[];
  current: boolean;
}

/** Vertical distance between stacked branch names on one tip. */
export const LABEL_LINE = 18;

/** Approximate advance widths of the 11px tag chip font, wide enough for Yu Gothic UI and fallbacks. */
const CHIP_FONT = { narrow: 7, wide: 11.5, padding: 12 };
const WIDE_CHARACTER = /[\u1100-\u115f\u2e80-\ua4cf\uac00-\ud7a3\uf900-\ufaff\ufe30-\ufe4f\uff00-\uff60\uffe0-\uffe6\u{20000}-\u{3fffd}]/u;

/** Measures rendered text width; the estimate is used where no font metrics are available. */
export type TextMeasure = (text: string) => number;

export function estimateChipText(text: string): number {
  let width = 0;
  for (const character of text) width += WIDE_CHARACTER.test(character) ? CHIP_FONT.wide : CHIP_FONT.narrow;
  return width;
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

/** Path of a lane's stem: from the ground, or curving out of its fork without crossing the fork's leaf. */
export function lanePath(lane: MapLane, groundY: number): string {
  if (!lane.fork) return `M${lane.x} ${groundY} V${lane.topY}`;
  const { x, y, side } = lane.fork;
  // A leaf on the right of the stem would be crossed, so climb above it before turning.
  const turnY = side > 0 ? y - MAP.leafHeight / 2 - 12 : y;
  const riseY = turnY - 48;
  return `M${x} ${y} V${turnY} C${x} ${turnY - 24} ${lane.x} ${turnY - 12} ${lane.x} ${riseY} V${lane.topY}`;
}

export interface SproutMapLayout {
  leaves: MapLeaf[];
  lanes: MapLane[];
  labels: MapLabel[];
  rootBuds: MapRootBud[];
  width: number;
  height: number;
  groundY: number;
  currentId: string | null;
}

/**
 * Order commits oldest first. The CLI lists newest first, so within one second the
 * later array position is older; parents are always placed before their children.
 */
function oldestFirst(commits: GraphCommit[]): GraphCommit[] {
  const sorted = commits
    .map((commit, index) => ({ commit, index }))
    .sort((a, b) => a.commit.created_at.localeCompare(b.commit.created_at) || b.index - a.index)
    .map((item) => item.commit);
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

/** Lay out commits oldest-at-bottom, one lane per branch the commits were created on. */
export function layoutSproutMap(graph: CommitGraph): SproutMapLayout {
  const ordered = oldestFirst(graph.commits);
  const ids = new Set(ordered.map((commit) => commit.id));
  const laneIds: string[] = [];
  for (const commit of ordered) {
    if (!laneIds.includes(commit.branch_id)) laneIds.push(commit.branch_id);
  }
  const height = MAP.top + MAP.bottom + Math.max(ordered.length, 1) * MAP.row;
  const groundY = height - MAP.bottom;
  const tagsByCommit = new Map<string, string[]>();
  for (const tag of graph.tags) tagsByCommit.set(tag.commit_id, [...(tagsByCommit.get(tag.commit_id) ?? []), tag.name]);
  const budsByCommit = new Map<string, Bud[]>();
  const rootBuds: MapRootBud[] = [];
  for (const bud of graph.buds) {
    if (bud.base_commit_id) budsByCommit.set(bud.base_commit_id, [...(budsByCommit.get(bud.base_commit_id) ?? []), bud]);
    else rootBuds.push({ bud, x: MAP.rootBudLeft + rootBuds.length * (MAP.budWidth + 8), y: groundY + 16 });
  }

  const perLane = new Map<number, number>();
  const leaves: MapLeaf[] = ordered.map((commit, row) => {
    const lane = laneIds.indexOf(commit.branch_id);
    const count = perLane.get(lane) ?? 0;
    perLane.set(lane, count + 1);
    const side: -1 | 1 = count % 2 === 0 ? -1 : 1;
    const x = MAP.left + lane * MAP.lane;
    const y = groundY - MAP.row / 2 - row * MAP.row;
    return {
      commit,
      lane,
      side,
      x,
      y,
      leafX: side < 0 ? x - MAP.gap - MAP.leafWidth : x + MAP.gap,
      tags: tagsByCommit.get(commit.id) ?? [],
      buds: budsByCommit.get(commit.id) ?? [],
    };
  });
  const byId = new Map(leaves.map((leaf) => [leaf.commit.id, leaf]));
  const liveIds = new Set(graph.branches.map((branch) => branch.id));

  const lanes: MapLane[] = laneIds.map((id, index) => {
    const members = leaves.filter((leaf) => leaf.lane === index);
    const first = members[0];
    const parent = first.commit.parent_id && ids.has(first.commit.parent_id) ? byId.get(first.commit.parent_id) : undefined;
    return {
      id,
      name: graph.branches.find((branch) => branch.id === id)?.name ?? first.commit.branch_name,
      x: MAP.left + index * MAP.lane,
      fork: parent && parent.lane !== index ? { x: parent.x, y: parent.y, side: parent.side } : null,
      bottomY: first.y,
      topY: members[members.length - 1].y,
      live: liveIds.has(id),
    };
  });

  const labelsByCommit = new Map<string, MapLabel>();
  for (const branch of graph.branches) {
    const leaf = branch.commit_id ? byId.get(branch.commit_id) : undefined;
    if (!leaf) continue;
    const label = labelsByCommit.get(leaf.commit.id) ?? { x: leaf.x, y: leaf.y - MAP.row - 4, branches: [], current: false };
    label.branches.push(branch);
    label.current ||= branch.current;
    labelsByCommit.set(leaf.commit.id, label);
  }

  const width = MAP.left + (laneIds.length - 1) * MAP.lane + MAP.gap + MAP.leafWidth + 48;
  const rootBudsRight = rootBuds.length ? rootBuds[rootBuds.length - 1].x + MAP.budWidth + 24 : 0;
  return {
    leaves,
    lanes,
    labels: [...labelsByCommit.values()],
    rootBuds,
    width: Math.max(width, MAP.left * 2, rootBudsRight),
    height,
    groundY,
    // The CLI records the position explicitly; a missing one is never guessed from a branch tip.
    currentId: graph.current_commit,
  };
}
