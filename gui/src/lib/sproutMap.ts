import type { Bud, CommitGraph, GraphCommit } from "./sprout";

export const MAP = {
  row: 96,
  lane: 280,
  leafWidth: 112,
  leafHeight: 72,
  gap: 18,
  top: 120,
  bottom: 64,
  left: 160,
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
  name: string;
  x: number;
  /** Fork point on the parent lane and the side its leaf sits on, or null when the lane grows from the ground. */
  fork: { x: number; y: number; side: -1 | 1 } | null;
  bottomY: number;
  topY: number;
  live: boolean;
}

export interface MapLabel {
  x: number;
  y: number;
  names: string[];
  current: boolean;
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
  const laneNames: string[] = [];
  for (const commit of ordered) {
    if (!laneNames.includes(commit.branch_name)) laneNames.push(commit.branch_name);
  }
  const height = MAP.top + MAP.bottom + Math.max(ordered.length, 1) * MAP.row;
  const groundY = height - MAP.bottom;
  const tagsByCommit = new Map<string, string[]>();
  for (const tag of graph.tags) tagsByCommit.set(tag.commit_id, [...(tagsByCommit.get(tag.commit_id) ?? []), tag.name]);
  const budsByCommit = new Map<string, Bud[]>();
  for (const bud of graph.buds ?? []) {
    if (bud.base_commit_id) budsByCommit.set(bud.base_commit_id, [...(budsByCommit.get(bud.base_commit_id) ?? []), bud]);
  }

  const perLane = new Map<number, number>();
  const leaves: MapLeaf[] = ordered.map((commit, row) => {
    const lane = laneNames.indexOf(commit.branch_name);
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
  const liveNames = new Set(graph.branches.map((branch) => branch.name));

  const lanes: MapLane[] = laneNames.map((name, index) => {
    const members = leaves.filter((leaf) => leaf.lane === index);
    const first = members[0];
    const parent = first.commit.parent_id && ids.has(first.commit.parent_id) ? byId.get(first.commit.parent_id) : undefined;
    return {
      name,
      x: MAP.left + index * MAP.lane,
      fork: parent && parent.lane !== index ? { x: parent.x, y: parent.y, side: parent.side } : null,
      bottomY: first.y,
      topY: members[members.length - 1].y,
      live: liveNames.has(name),
    };
  });

  const labelsByCommit = new Map<string, MapLabel>();
  for (const branch of graph.branches) {
    const leaf = branch.commit_id ? byId.get(branch.commit_id) : undefined;
    if (!leaf) continue;
    const label = labelsByCommit.get(leaf.commit.id) ?? { x: leaf.x, y: leaf.y - MAP.row - 4, names: [], current: false };
    label.names.push(branch.name);
    label.current ||= branch.current;
    labelsByCommit.set(leaf.commit.id, label);
  }

  const currentTip = graph.branches.find((branch) => branch.current)?.commit_id ?? null;
  const currentId = graph.current_commit !== undefined ? graph.current_commit : currentTip;
  const width = MAP.left + (laneNames.length - 1) * MAP.lane + MAP.gap + MAP.leafWidth + 48;
  return {
    leaves,
    lanes,
    labels: [...labelsByCommit.values()],
    width: Math.max(width, MAP.left * 2),
    height,
    groundY,
    currentId: currentId ?? null,
  };
}
