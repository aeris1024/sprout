import { describe, expect, it } from "vitest";
import { MAP, lanePath, layoutSproutMap } from "./sproutMap";
import type { CommitGraph, GraphCommit } from "./sprout";

function commit(id: string, parent: string | null, branch: string, minute: number): GraphCommit {
  return {
    id,
    parent_id: parent,
    branch_id: branch,
    branch_name: branch,
    created_at: `2026-10-28T00:${String(minute).padStart(2, "0")}:00+00:00`,
    message: id,
    note: null,
    note_updated_at: null,
    labels: [],
    attachments: [],
  };
}

const graph: CommitGraph = {
  current_commit: "b",
  commits: [
    commit("d", "c", "main", 4),
    commit("x", "b", "side", 3),
    commit("c", "b", "main", 2),
    commit("b", "a", "main", 1),
    commit("a", null, "main", 0),
    commit("z", "a", "gone", 5),
  ],
  branches: [
    { id: "main", name: "main", commit_id: "d", comment: "", current: true },
    { id: "side", name: "side", commit_id: "x", comment: "", current: false },
    { id: "copy", name: "copy", commit_id: "x", comment: "", current: false },
  ],
  tags: [{ name: "draft", commit_id: "a", comment: "", created_at: "" }],
  buds: [{ id: "bud", base_commit_id: "b", branch_id: "main", branch_name: "main", created_at: "", changes: [], files: [] }],
};

describe("layoutSproutMap", () => {
  it("keeps branch identity across renames and reuses names on distinct lanes", () => {
    const root = { ...commit("root", null, "original-id", 1), branch_name: "old-name" };
    const renamed = { ...commit("renamed", "root", "original-id", 2), branch_name: "new-name" };
    const reused = { ...commit("reused", "root", "new-id", 3), branch_name: "old-name" };
    const layout = layoutSproutMap({
      commits: [reused, renamed, root],
      branches: [
        { id: "original-id", name: "new-name", commit_id: "renamed", comment: "", current: true },
        { id: "new-id", name: "old-name", commit_id: "reused", comment: "", current: false },
      ],
      tags: [],
    });
    expect(layout.lanes.map((lane) => [lane.id, lane.name])).toEqual([
      ["original-id", "new-name"], ["new-id", "old-name"],
    ]);
    const leaves = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));
    expect(leaves.root.lane).toBe(leaves.renamed.lane);
    expect(leaves.reused.lane).not.toBe(leaves.root.lane);

    const deleted = layoutSproutMap({
      commits: [reused, root],
      branches: [{ id: "new-id", name: "old-name", commit_id: "reused", comment: "", current: true }],
      tags: [],
    });
    expect(deleted.lanes.map((lane) => [lane.id, lane.live])).toEqual([
      ["original-id", false], ["new-id", true],
    ]);
  });

  it("puts older snapshots lower and alternates leaves along each stem", () => {
    const layout = layoutSproutMap(graph);
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));

    expect(byId.a.y).toBeGreaterThan(byId.b.y);
    expect(byId.b.y).toBeGreaterThan(byId.c.y);
    expect(byId.c.y).toBeGreaterThan(byId.d.y);
    expect([byId.a.side, byId.b.side, byId.c.side, byId.d.side]).toEqual([-1, 1, -1, 1]);
    expect(byId.a.leafX).toBe(byId.a.x - MAP.gap - MAP.leafWidth);
    expect(byId.b.leafX).toBe(byId.b.x + MAP.gap);
    expect(layout.groundY).toBeGreaterThan(byId.a.y);
  });

  it("grows branches from their fork point and marks deleted origins", () => {
    const layout = layoutSproutMap(graph);
    const lanes = Object.fromEntries(layout.lanes.map((lane) => [lane.name, lane]));
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));

    expect(lanes.main.fork).toBeNull();
    expect(lanes.side.fork).toEqual({ x: byId.b.x, y: byId.b.y, side: byId.b.side });
    expect(lanes.side.x).toBeGreaterThan(lanes.main.x);
    expect(lanes.gone.live).toBe(false);
    expect(lanes.side.live).toBe(true);
  });

  it("routes a fork from a right-side leaf above that leaf", () => {
    const lane = { id: "x", name: "x", x: 500, fork: { x: 100, y: 400, side: 1 as const }, bottomY: 300, topY: 100, live: true };
    const path = lanePath(lane, 900);
    const turnY = 400 - MAP.leafHeight / 2 - 12;
    expect(path.startsWith(`M100 400 V${turnY} C`)).toBe(true);
    expect(lanePath({ ...lane, fork: { ...lane.fork, side: -1 } }, 900).startsWith("M100 400 V400 C")).toBe(true);
    expect(lanePath({ ...lane, fork: null }, 900)).toBe("M500 900 V100");
  });

  it("labels branch tips, tags, buds, and the current position", () => {
    const layout = layoutSproutMap(graph);
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));

    expect(layout.currentId).toBe("b");
    expect(byId.a.tags).toEqual(["draft"]);
    expect(byId.b.buds.map((bud) => bud.id)).toEqual(["bud"]);
    expect(layout.labels.map((label) => [label.names, label.current])).toEqual([
      [["main"], true],
      [["side", "copy"], false],
    ]);
  });

  it("falls back to the current branch tip without a recorded position", () => {
    expect(layoutSproutMap({ ...graph, current_commit: undefined }).currentId).toBe("d");
    expect(layoutSproutMap({ commits: [], branches: [], tags: [] }).leaves).toEqual([]);
  });

  it("keeps parents below children made within the same second", () => {
    const sameSecond = [commit("child", "parent", "main", 1), commit("parent", "root", "main", 1), commit("root", null, "main", 0)];
    const layout = layoutSproutMap({ commits: sameSecond, branches: [], tags: [] });
    expect(layout.leaves.map((leaf) => leaf.commit.id)).toEqual(["root", "parent", "child"]);
    const reversed = layoutSproutMap({ commits: [...sameSecond].reverse(), branches: [], tags: [] });
    expect(reversed.leaves.map((leaf) => leaf.commit.id)).toEqual(["root", "parent", "child"]);
  });

  it("handles hundreds of snapshots", () => {
    const many = Array.from({ length: 500 }, (_, index) =>
      commit(`c${index}`, index ? `c${index - 1}` : null, "main", index % 60),
    ).map((item, index) => ({ ...item, created_at: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString() }));
    const started = performance.now();
    const layout = layoutSproutMap({ commits: many, branches: [{ id: "main", name: "main", commit_id: "c499", comment: "", current: true }], tags: [] });
    expect(performance.now() - started).toBeLessThan(200);
    expect(layout.leaves).toHaveLength(500);
    expect(layout.height).toBe(MAP.top + MAP.bottom + 500 * MAP.row);
  });
});
