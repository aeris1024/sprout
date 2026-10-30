// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import SproutMap from "./SproutMap";
import type { Bud, CommitGraph } from "../lib/sprout";

afterEach(cleanup);

function renderMap(buds: Partial<Bud>[]) {
  const graph: CommitGraph = {
    current_commit: "c1",
    at_branch_tip: true,
    commits: [{ id: "c1", parent_id: null, branch_id: "b1", branch_name: "main", created_at: "2026-10-30T00:00:00.000000+00:00", message: "Base", attachments: [], note: null, note_updated_at: null, labels: [] }],
    branches: [{ id: "b1", name: "main", commit_id: "c1", comment: "", current: true }],
    tags: [],
    buds: buds.map((bud, index) => ({ id: `bud${index}`, base_commit_id: "c1", branch_id: "b1", branch_name: "main", created_at: "2026-10-30T00:00:00.000000+00:00", changes: [{ state: "modified", path: "a.txt" }], files: [], ...bud })),
  };
  render(<SproutMap graph={graph} selection={null} unsavedCount={0} projectDir="C:/p" sproutProgram="" onSelect={vi.fn()} onSelectBud={vi.fn()} onSelectBranch={vi.fn()} onSelectUnsaved={vi.fn()} />);
}

it("shows a bud's name on the map and keeps long names readable through the label", () => {
  renderMap([{ name: "配色" }, { name: "とても長いつぼみの名前です" }, { name: "" }]);
  expect(screen.getByText("配色")).toBeTruthy();
  expect(screen.getByRole("button", { name: "つぼみ「配色」（1件の変更）" })).toBeTruthy();
  expect(screen.getByText("とても長いつ…")).toBeTruthy();
  expect(screen.getByRole("button", { name: "つぼみ「とても長いつぼみの名前です」（1件の変更）" })).toBeTruthy();
  expect(screen.getByText("つぼみ 1")).toBeTruthy();
});
