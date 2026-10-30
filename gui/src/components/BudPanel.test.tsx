// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BudPanel from "./BudPanel";
import type { Bud } from "../lib/sprout";

const bud: Bud = {
  id: "bud1",
  name: "",
  base_commit_id: "c1",
  branch_id: "gone",
  branch_name: "old",
  created_at: "2026-10-30T00:00:00.000000+00:00",
  changes: [{ state: "modified", path: "a.txt" }],
  files: [],
};

function panel(overrides: Partial<Bud>, onRename = vi.fn().mockResolvedValue(true)) {
  render(
    <BudPanel
      bud={{ ...bud, ...overrides }}
      baseMessage="Base"
      branches={[]}
      deletedBranches={[{ id: "gone", name: "old", comment: "", created_at: bud.created_at, deleted_at: "2026-10-31T00:00:00.000000+00:00" }]}
      busy={false}
      onRestore={vi.fn()}
      onDrop={vi.fn()}
      onRename={onRename}
      onClose={vi.fn()}
    />,
  );
  return onRename;
}

afterEach(cleanup);

describe("BudPanel", () => {
  it("names an unnamed bud and closes the editor once saved", async () => {
    const onRename = panel({});
    expect(screen.getByRole("heading", { name: "「Base」の上の変更 1件" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "名前を付ける" }));
    fireEvent.change(screen.getByLabelText("つぼみの名前"), { target: { value: "別案" } });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));
    expect(onRename).toHaveBeenCalledWith("bud1", "別案");
    await waitFor(() => expect(screen.queryByLabelText("つぼみの名前")).toBeNull());
  });

  it("keeps a refused name in the input", async () => {
    panel({ name: "前の名前" }, vi.fn().mockResolvedValue(false));
    expect(screen.getByRole("heading", { name: "前の名前" })).toBeTruthy();
    expect(screen.getByText("「Base」の上の変更 1件")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "名前を編集" }));
    fireEvent.change(screen.getByLabelText("つぼみの名前"), { target: { value: "拒否される名前" } });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));
    await waitFor(() => expect((screen.getByLabelText("つぼみの名前") as HTMLInputElement).value).toBe("拒否される名前"));
  });

  it("shows when the bud's branch was deleted", () => {
    panel({});
    expect(screen.getByText(/2026\/10\/31.*削除済みのため/)).toBeTruthy();
  });
});
