import { describe, expect, it } from "vitest";
import { flattenCommitGraph } from "./graph";
import type { CommitGraph, GraphCommit } from "./sprout";

function commit(id: string, parentId: string | null, branchName: string): GraphCommit {
  return {
    id,
    parent_id: parentId,
    branch_name: branchName,
    created_at: `2026-08-09T00:00:0${id}+00:00`,
    message: `commit ${id}`,
    attachments: [],
    note: null,
    note_updated_at: null,
    labels: [],
  };
}

const graph: CommitGraph = {
  commits: [commit("4", "2", "deleted-side"), commit("3", "2", "main"), commit("2", "1", "main"), commit("1", null, "main")],
  branches: [
    { name: "main", commit_id: "3", comment: "", current: true },
  ],
  tags: [{ name: "draft", commit_id: "2", comment: "", created_at: "2026-08-09T00:00:02+00:00" }],
};

describe("flattenCommitGraph", () => {
  it("orders every live and deleted-branch commit by parent depth", () => {
    const result = flattenCommitGraph(graph, new Set(), 100);
    expect(result.rows.map((row) => [row.commit.id, row.depth])).toEqual([
      ["1", 0], ["2", 1], ["3", 2], ["4", 2],
    ]);
    expect(result.rows.find((row) => row.commit.id === "3")?.currentTip).toBe(true);
    expect(result.rows.find((row) => row.commit.id === "2")?.tags[0].name).toBe("draft");
  });

  it("supports collapsing and incremental display limits", () => {
    expect(flattenCommitGraph(graph, new Set(["2"]), 100).rows.map((row) => row.commit.id)).toEqual(["1", "2"]);
    const limited = flattenCommitGraph(graph, new Set(), 2);
    expect(limited.rows).toHaveLength(2);
    expect(limited.totalVisible).toBe(4);
  });

  it("still emits malformed cyclic commits once", () => {
    const cyclic: CommitGraph = { commits: [commit("1", "2", "old"), commit("2", "1", "old")], branches: [], tags: [] };
    expect(flattenCommitGraph(cyclic, new Set(), 10).rows.map((row) => row.commit.id).sort()).toEqual(["1", "2"]);
  });
});
