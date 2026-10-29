import { describe, expect, it } from "vitest";
import { BRANCH_LABEL, LABEL_LINE, MAP, branchLabelText, estimateChipText, laneColor, lanePath, layoutSproutMap, leafCaption, pendingPath, tagChip } from "./sproutMap";
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

  it("puts older snapshots to the left, one column each, with leaves above the stem", () => {
    const layout = layoutSproutMap(graph);
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));

    expect(layout.leaves.map((leaf) => leaf.x)).toEqual(layout.leaves.map((_, index) => MAP.left + index * MAP.column));
    expect(byId.b.x).toBeGreaterThan(byId.a.x);
    expect(byId.c.x).toBeGreaterThan(byId.b.x);
    expect(byId.d.x).toBeGreaterThan(byId.c.x);
    expect(new Set(layout.leaves.map((leaf) => leaf.x)).size).toBe(layout.leaves.length);
    expect([byId.b.y, byId.c.y, byId.d.y]).toEqual([byId.a.y, byId.a.y, byId.a.y]);
    expect(byId.a.leafX).toBe(byId.a.x - MAP.leafWidth / 2);
    expect(byId.a.leafY + MAP.leafHeight + MAP.caption + MAP.stalk).toBe(byId.a.y);
    expect(byId.a.leafY).toBeGreaterThanOrEqual(0);
  });

  it("grows branches from their fork point on rows below and marks deleted origins", () => {
    const layout = layoutSproutMap(graph);
    const lanes = Object.fromEntries(layout.lanes.map((lane) => [lane.name, lane]));
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));

    expect(lanes.main.fork).toBeNull();
    expect(lanes.side.fork).toEqual({ x: byId.b.x, y: byId.b.y });
    expect(lanes.side.y).toBeGreaterThan(lanes.main.y);
    expect(byId.x.y).toBe(lanes.side.y);
    // A row below starts after the leaves of the row above it.
    expect(lanes.side.y - MAP.above).toBeGreaterThanOrEqual(lanes.main.y);
    expect([lanes.main.startX, lanes.main.endX]).toEqual([byId.a.x, byId.d.x]);
    expect(lanes.gone.live).toBe(false);
    expect(lanes.side.live).toBe(true);
    expect([0, 1, 4, 5].map(laneColor)).toEqual([1, 2, 5, 1]);
  });

  it("curves a fork down to its row before the next column", () => {
    const lane = { id: "x", name: "x", y: 400, fork: { x: 100, y: 200 }, startX: 248, endX: 544, live: true };
    expect(lanePath(lane)).toBe("M100 200 C140 200 120 400 180 400 H544");
    expect(lanePath({ ...lane, fork: null })).toBe(`M${MAP.groundX} 400 H544`);
    const from = { x: 100, y: 200 };
    expect(pendingPath({ x: 248, y: 200, leafX: 0, leafY: 0, from, fork: false })).toBe("M100 200 H248");
    expect(pendingPath({ x: 248, y: 400, leafX: 0, leafY: 0, from, fork: true })).toBe("M100 200 C140 200 120 400 180 400 H248");
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

  it("places buds kept before the first commit below the map", () => {
    const rootBud = (id: string) => ({ id, base_commit_id: null, branch_id: "main", branch_name: "main", created_at: "", changes: [], files: [] });
    const layout = layoutSproutMap({ ...graph, buds: [...graph.buds, rootBud("r1"), rootBud("r2")] });
    expect(layout.rootBuds.map((item) => item.bud.id)).toEqual(["r1", "r2"]);
    const lowest = Math.max(...layout.lanes.map((lane) => lane.y));
    expect(layout.rootBuds.every((item) => item.y > lowest)).toBe(true);
    expect(layout.height).toBeGreaterThanOrEqual(layout.rootBuds[0].y + MAP.budHeight);
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

  it("puts names after stem ends and hangs names of tips partway along a stem below their buds", () => {
    const chain = [commit("c", "b", "main", 2), commit("b", "a", "main", 1), commit("a", null, "main", 0)];
    const branch = (id: string, tip: string, current = false) => ({ id, name: id, commit_id: tip, comment: "", current });
    const branches = [branch("main", "c"), branch("分岐2", "b", true), branch("copy", "b")];
    const bud = { id: "bud", base_commit_id: "b", branch_id: "main", branch_name: "main", created_at: "", changes: [], files: [] };
    const plain = layoutSproutMap(tree(chain, [branch("main", "c")]));
    const layout = layoutSproutMap({ ...tree(chain, branches), buds: [bud] });
    const leaves = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));
    const byNames = Object.fromEntries(layout.labels.map((label) => [label.branches.map((item) => item.name).join(","), label]));

    expect(byNames.main).toMatchObject({ placement: "end", y: leaves.c.y });
    expect(byNames.main.x).toBeGreaterThan(leaves.c.leafX + MAP.leafWidth);
    const mid = byNames["分岐2,copy"];
    expect(mid).toMatchObject({ placement: "below", x: leaves.b.x - MAP.underRight, nodeY: leaves.b.y, current: true });
    // The first name starts under the bud of b, so neither covers the other or a leaf.
    expect(mid.y - LABEL_LINE).toBeGreaterThanOrEqual(leaves.b.y + MAP.underGap + MAP.budStep - 8);
    // The row grows to fit the bud and both names.
    expect(layout.height).toBeGreaterThan(plain.height);
    expect(layout.height).toBeGreaterThanOrEqual(mid.y + LABEL_LINE);
  });

  it("makes room for long names at both edges of the map", () => {
    const chain = [commit("c", "b", "main", 2), commit("b", "a", "main", 1), commit("a", null, "main", 0)];
    const longName = "とても長い名前の分岐ブランチ";
    const plain = layoutSproutMap(tree(chain, [{ id: "main", name: "main", commit_id: "c", comment: "", current: true }]));
    const shifted = layoutSproutMap(tree(chain, [
      { id: "main", name: longName, commit_id: "c", comment: "", current: false },
      { id: "left", name: longName, commit_id: "a", comment: "", current: true },
    ]));
    expect(plain.leaves[0].x).toBe(MAP.left);
    const shift = shifted.leaves[0].x - MAP.left;
    expect(shift).toBeGreaterThan(0);
    const leftLabel = shifted.labels.find((label) => label.branches[0].id === "left")!;
    const width = estimateChipText(branchLabelText(leftLabel.branches[0])) * BRANCH_LABEL.fontScale;
    expect(leftLabel.x - width).toBeGreaterThanOrEqual(BRANCH_LABEL.margin - 1);
    const endLabel = shifted.labels.find((label) => label.branches[0].id === "main")!;
    expect(shifted.width).toBeGreaterThanOrEqual(endLabel.x + estimateChipText(longName) * BRANCH_LABEL.fontScale);
  });

  it("handles hundreds of snapshots", () => {
    const many = Array.from({ length: 500 }, (_, index) =>
      commit(`c${index}`, index ? `c${index - 1}` : null, "main", index % 60),
    ).map((item, index) => ({ ...item, created_at: new Date(Date.UTC(2026, 0, 1, 0, index)).toISOString() }));
    const started = performance.now();
    const layout = layoutSproutMap(tree(many, [{ id: "main", name: "main", commit_id: "c499", comment: "", current: true }]));
    expect(performance.now() - started).toBeLessThan(200);
    expect(layout.leaves).toHaveLength(500);
    expect(layout.leaves[499].x).toBe(MAP.left + 499 * MAP.column);
    expect(layout.height).toBe(MAP.top + MAP.above + MAP.below + MAP.bottom);
  });

  it("continues the current branch's stem with unsaved changes at its tip", () => {
    const chain = [commit("c", "b", "main", 2), commit("b", "a", "main", 1), commit("a", null, "main", 0)];
    const atTip = { ...tree(chain, [{ id: "main", name: "main", commit_id: "c", comment: "", current: true }]), current_commit: "c" };
    expect(layoutSproutMap(atTip).pending).toBeNull();
    const layout = layoutSproutMap(atTip, { unsaved: true });
    const c = layout.leaves.find((leaf) => leaf.commit.id === "c")!;
    expect(layout.pending).toMatchObject({ x: c.x + MAP.column, y: c.y, fork: false, from: { x: c.x, y: c.y } });
    // The branch name moves past the unsaved leaf.
    expect(layout.labels[0].x).toBeGreaterThan(layout.pending!.leafX + MAP.leafWidth);
    expect(layout.width).toBeGreaterThanOrEqual(layout.pending!.leafX + MAP.leafWidth);
  });

  it("grows unsaved changes as a new branch row from a snapshot partway along a stem", () => {
    const layout = layoutSproutMap(graph, { unsaved: true });
    const byId = Object.fromEntries(layout.leaves.map((leaf) => [leaf.commit.id, leaf]));
    const lanes = Object.fromEntries(layout.lanes.map((lane) => [lane.name, lane]));
    const pending = layout.pending!;
    expect(pending).toMatchObject({ x: byId.b.x + MAP.column, fork: true, from: { x: byId.b.x, y: byId.b.y } });
    // The new row sits right under the current row and pushes the later rows down.
    expect(pending.y).toBeGreaterThan(lanes.main.y);
    expect(lanes.side.y).toBeGreaterThan(pending.y);
    expect(lanes.side.y).toBeGreaterThan(layoutSproutMap(graph).lanes[1].y);
    // A different branch on the current snapshot also means saving grows a new branch.
    const copy = layoutSproutMap({ ...graph, current_commit: "x", branches: graph.branches.map((item) => ({ ...item, current: item.id === "copy" })) }, { unsaved: true });
    expect(copy.pending?.fork).toBe(true);
  });

  it("shortens leaf messages that do not fit under the leaf", () => {
    expect(leafCaption("線画")).toBe("線画");
    const long = leafCaption("背景と人物の色をまとめて調整した版");
    expect(long.endsWith("…")).toBe(true);
    expect(estimateChipText(long) * (12 / 11)).toBeLessThanOrEqual(MAP.leafWidth - 12);
  });
});
