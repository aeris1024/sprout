import { describe, expect, it } from "vitest";
import { MAP, layoutSproutMap } from "./sproutMap";
import type { CommitGraph, GraphCommit } from "./sprout";

function commit(id: string, parent: string | null, branch: string, minute: number): GraphCommit {
  return {
    id,
    parent_id: parent,
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
    { name: "main", commit_id: "d", comment: "", current: true },
    { name: "side", commit_id: "x", comment: "", current: false },
    { name: "copy", commit_id: "x", comment: "", current: false },
  ],
  tags: [{ name: "draft", commit_id: "a", comment: "", created_at: "" }],
  buds: [{ id: "bud", base_commit_id: "b", branch_name: "main", created_at: "", changes: [], files: [] }],
};

describe("layoutSproutMap", () => {
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
    expect(lanes.side.fork).toEqual({ x: byId.b.x, y: byId.b.y });
    expect(lanes.side.x).toBeGreaterThan(lanes.main.x);
    expect(lanes.gone.live).toBe(false);
    expect(lanes.side.live).toBe(true);
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
    const layout = layoutSproutMap({ commits: many, branches: [{ name: "main", commit_id: "c499", comment: "", current: true }], tags: [] });
    expect(performance.now() - started).toBeLessThan(200);
    expect(layout.leaves).toHaveLength(500);
    expect(layout.height).toBe(MAP.top + MAP.bottom + 500 * MAP.row);
  });
});
