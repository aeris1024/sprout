// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

const mocks = vi.hoisted(() => ({
  open: vi.fn(),
  runSprout: vi.fn(),
  loadSettings: vi.fn(),
  saveSettings: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({ open: mocks.open }));
vi.mock("./lib/sprout", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./lib/sprout")>()),
  runSprout: mocks.runSprout,
}));
vi.mock("./lib/settings", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./lib/settings")>()),
  loadSettings: mocks.loadSettings,
  saveSettings: mocks.saveSettings,
}));

describe("Sprout GUI project flow", () => {
  beforeEach(() => {
    mocks.open.mockReset();
    mocks.runSprout.mockReset();
    mocks.loadSettings.mockReset();
    mocks.saveSettings.mockReset();
    mocks.loadSettings.mockResolvedValue({
      recentProjects: [],
      sproutProgram: "",
    });
    mocks.saveSettings.mockResolvedValue(undefined);
  });

  afterEach(cleanup);

  it("offers init, loads status, and remembers the selected project", async () => {
    const user = userEvent.setup();
    const project = "C:\\work\\new-project";
    mocks.open.mockResolvedValue(project);
    mocks.runSprout
      .mockRejectedValueOnce({
        code: "sprout_error",
        message: "not inside a Sprout project (run 'sprout init')",
        details: {},
      })
      .mockResolvedValueOnce({ root: project })
      .mockResolvedValueOnce({
        branch: "main",
        changes: [],
        tracked: [],
        untracked: [],
      });

    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));

    expect(
      await screen.findByRole("heading", {
        name: "このフォルダはまだSproutプロジェクトではありません",
      }),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "このフォルダを初期化" }));

    expect(await screen.findByRole("heading", { name: "new-project" })).toBeTruthy();
    expect(screen.getByText("作業ツリーはクリーンです")).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenNthCalledWith(
      2,
      project,
      ["init", "."],
      "",
    );
    expect(mocks.runSprout).toHaveBeenNthCalledWith(
      3,
      project,
      ["status", "--tracked", "--untracked"],
      "",
    );
    await waitFor(() =>
      expect(mocks.saveSettings).toHaveBeenCalledWith({
        recentProjects: [project],
        sproutProgram: "",
      }),
    );
  });

  it("shows a retry action for repository locks", async () => {
    const user = userEvent.setup();
    const project = "C:\\work\\locked";
    mocks.open.mockResolvedValue(project);
    mocks.runSprout
      .mockRejectedValueOnce({
        code: "repository_locked",
        message: "another Sprout operation is already running",
        details: { retryable: true },
      })
      .mockResolvedValueOnce({
        branch: "main",
        changes: [],
        tracked: [],
        untracked: [],
      });

    render(<App />);
    await user.click(screen.getByRole("button", { name: "プロジェクトを選択" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "another Sprout operation is already running",
    );

    await user.click(screen.getByRole("button", { name: "再試行" }));
    expect(await screen.findByRole("heading", { name: "locked" })).toBeTruthy();
    expect(mocks.runSprout).toHaveBeenCalledTimes(2);
  });
});
