import { describe, expect, it } from "vitest";
import { MAP, SIDE_LABEL, branchLabelText, estimateChipText, lanePath, layoutSproutMap, tagChip } from "./sproutMap";
import type { BranchInfo, CommitGraph, GraphCommit, GraphTag } from "./sprout";

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

/** A graph as the CLI reports it, with no recorded position unless one is given. */
function tree(commits: GraphCommit[], branches: BranchInfo[] = [], tags: GraphTag[] = []): CommitGraph {
  return { current_commit: null, at_branch_tip: true, commits, branches, tags, buds: [] };
}

const graph: CommitGraph = {
  current_commit: "b",
  at_branch_tip: false,
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
  it.each([0, 1])("preserves creation order across branches when clocks repeat or roll back (%s)", (minute) => {
    const a = commit("a", null, "main", 1);
    const b = commit("b", "a", "main", 1);
    const c = commit("c", "a", "side", minute);
    const commits = [c, b, a];
    expect(layoutSproutMap(tree(commits)).leaves.map((leaf) => leaf.commit.id)).toEqual(["a", "b", "c"]);
    expect(commits).toEqual([c, b, a]);
    expect(c.created_at).toBe(commit("c", "a", "side", minute).created_at);
  });

  it("places a parent first even when the supplied array puts it before its child", () => {
    expect(layoutSproutMap(tree([
      commit("a", null, "main", 2), commit("b", "a", "main", 0),
    ])).leaves.map((leaf) => leaf.commit.id)).toEqual(["a", "b"]);
  });

  it("keeps branch identity across renames and reuses names on distinct lanes", () => {
    const root = { ...commit("root", null, "original-id", 1), branch_name: "old-name" };
    const renamed = { ...commit("renamed", "root", "original-id", 2), branch_name: "new-name" };
    const reused = { ...commit("reused", "root", "new-id", 3), branch_name: "old-name" };
    const layout = layoutSproutMap(tree([reused, renamed, root], [
      { id: "original-id", name: "new-name", commit_id: "renamed", comment: "", current: true },
      { id: "new-id", name: "old-name", commit_id: "reused", comment: "", current: false },
    ]));
    expect(layout.lanes.map((lane) => [lane.id, lane.name])).toEqual([
      ["original-id", "new-name"], ["new-id", "old-name"],
    ]);
    const leaves = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));
    expect(leaves.root.lane).toBe(leaves.renamed.lane);
    expect(leaves.reused.lane).not.toBe(leaves.root.lane);

    const deleted = layoutSproutMap(tree([reused, root], [
      { id: "new-id", name: "old-name", commit_id: "reused", comment: "", current: true },
    ]));
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
    expect(layout.labels.map((label) => [label.branches.map((branch) => branch.name), label.current])).toEqual([
      [["main"], true],
      [["side", "copy"], false],
    ]);
  });

  it("uses the recorded position without guessing it from the current branch tip", () => {
    expect(layoutSproutMap({ ...graph, current_commit: null }).currentId).toBeNull();
    expect(layoutSproutMap(tree([], [])).leaves).toEqual([]);
  });

  it("places buds kept before the first commit on the ground", () => {
    const rootBud = (id: string) => ({ id, base_commit_id: null, branch_id: "main", branch_name: "main", created_at: "", changes: [], files: [] });
    const layout = layoutSproutMap({ ...graph, buds: [...graph.buds, rootBud("r1"), rootBud("r2")] });
    expect(layout.rootBuds.map((item) => item.bud.id)).toEqual(["r1", "r2"]);
    expect(layout.rootBuds.every((item) => item.y > layout.groundY)).toBe(true);
    expect(layout.rootBuds[1].x - layout.rootBuds[0].x).toBeGreaterThanOrEqual(MAP.budWidth);
    expect(layout.leaves.flatMap((leaf) => leaf.buds.map((bud) => bud.id))).toEqual(["bud"]);

    const empty = layoutSproutMap({ ...tree([]), buds: Array.from({ length: 6 }, (_, index) => rootBud(`e${index}`)) });
    expect(empty.rootBuds).toHaveLength(6);
    expect(empty.width).toBeGreaterThanOrEqual(empty.rootBuds[5].x + MAP.budWidth);
  });

  it("keeps parents below children made within the same second", () => {
    const sameSecond = [commit("child", "parent", "main", 1), commit("parent", "root", "main", 1), commit("root", null, "main", 0)];
    const layout = layoutSproutMap(tree(sameSecond, []));
    expect(layout.leaves.map((leaf) => leaf.commit.id)).toEqual(["root", "parent", "child"]);
    const reversed = layoutSproutMap(tree([...sameSecond].reverse(), []));
    expect(reversed.leaves.map((leaf) => leaf.commit.id)).toEqual(["root", "parent", "child"]);
  });

  it("sizes tag chips for full-width names and shortens names that do not fit", () => {
    const ascii = tagChip("v1");
    const japanese = tagChip("提出");
    expect(ascii.text).toBe("#v1");
    expect(japanese.text).toBe("#提出");
    // Two full-width characters need clearly more room than two ASCII ones.
    expect(japanese.width - ascii.width).toBeGreaterThanOrEqual(8);
    expect(tagChip("線画完成").text).toBe("#線画完成");
    expect(tagChip("線画完成").width).toBeLessThanOrEqual(MAP.leafWidth - 12);

    const long = tagChip("クライアント最終確認済み版");
    expect(long.text.endsWith("…")).toBe(true);
    expect(long.text.startsWith("#クライアント")).toBe(true);
    expect(long.width).toBeLessThanOrEqual(MAP.leafWidth - 12);
    expect(tagChip("a".repeat(40)).text).toMatch(/^#a+…$/);
  });

  it("fits tag chips to measured font widths", () => {
    // Proportional katakana is narrower than the estimate, so more of the name stays visible.
    const narrow = (text: string) => [...text].length * 6;
    const chip = tagChip("クライアント最終確認済み版", narrow);
    expect(chip.text).toBe("#クライアント最終確認済み版");
    expect(chip.width).toBe(14 * 6 + 12);
    const wide = (text: string) => [...text].length * 14;
    const shortened = tagChip("クライアント最終確認済み版", wide);
    expect(shortened.text).toBe("#クライア…");
    expect(shortened.width).toBe(6 * 14 + 12);
  });

  it("puts names of branches whose tip is partway up a stem beside it, away from the leaf", () => {
    const chain = [commit("c", "b", "main", 2), commit("b", "a", "main", 1), commit("a", null, "main", 0)];
    const branch = (id: string, tip: string, current = false) => ({ id, name: id, commit_id: tip, comment: "", current });
    const layout = layoutSproutMap(tree(chain, [branch("main", "c"), branch("分岐2", "b", true), branch("copy", "b"), branch("early", "a")]));
    const leaves = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));
    const byNames = Object.fromEntries(layout.labels.map((label) => [label.branches.map((item) => item.name).join(","), label]));

    expect(byNames.main.placement).toBe("top");
    const mid = byNames["分岐2,copy"];
    expect(mid).toMatchObject({ placement: "side", x: leaves.b.x, y: leaves.b.y, current: true });
    // The leaf of b is on the right, so the names sprout to the left and do not cover it.
    expect(leaves.b.side).toBe(1);
    expect(mid.placement === "side" && mid.direction).toBe(-1);
    const early = byNames.early;
    expect(leaves.a.side).toBe(-1);
    expect(early.placement === "side" && early.direction).toBe(1);
  });

  it("makes room for side names at both edges of the map", () => {
    const chain = [commit("c", "b", "main", 2), commit("b", "a", "main", 1), commit("a", null, "main", 0)];
    const longName = "とても長い名前の分岐ブランチ";
    const plain = layoutSproutMap(tree(chain, [{ id: "main", name: "main", commit_id: "c", comment: "", current: true }]));
    const shifted = layoutSproutMap(tree(chain, [
      { id: "main", name: "main", commit_id: "c", comment: "", current: false },
      { id: "left", name: longName, commit_id: "b", comment: "", current: true },
      { id: "right", name: longName, commit_id: "a", comment: "", current: false },
    ]));
    expect(plain.leaves[0].x).toBe(MAP.left);
    const shift = shifted.leaves[0].x - MAP.left;
    expect(shift).toBeGreaterThan(0);
    expect(shifted.lanes[0].x).toBe(MAP.left + shift);
    const leftLabel = shifted.labels.find((label) => label.branches[0].id === "left")!;
    const textStart = leftLabel.x - (SIDE_LABEL.stubEnd + SIDE_LABEL.textGap);
    expect(textStart - estimateChipText(branchLabelText(leftLabel.branches[0])) * SIDE_LABEL.fontScale).toBeGreaterThanOrEqual(SIDE_LABEL.margin - 1);
    const rightLabel = shifted.labels.find((label) => label.branches[0].id === "right")!;
    const textEnd = rightLabel.x + SIDE_LABEL.stubEnd + SIDE_LABEL.textGap + estimateChipText(longName) * SIDE_LABEL.fontScale;
    expect(shifted.width).toBeGreaterThanOrEqual(textEnd);
  });

  it("handles hundreds of snapshots", () => {
    const many = Array.from({ length: 500 }, (_, index) =>
      commit(`c${index}`, index ? `c${index - 1}` : null, "main", index % 60),
    ).map((item, index) => ({ ...item, created_at: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString() }));
    const started = performance.now();
    const layout = layoutSproutMap(tree(many, [{ id: "main", name: "main", commit_id: "c499", comment: "", current: true }]));
    expect(performance.now() - started).toBeLessThan(200);
    expect(layout.leaves).toHaveLength(500);
    expect(layout.height).toBe(MAP.top + MAP.bottom + 500 * MAP.row);
  });
});
