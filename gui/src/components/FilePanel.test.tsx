// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import FilePanel from "./FilePanel";

const longPath = `素材/${"とても長い日本語のフォルダ名/".repeat(8)}最終版のファイル名.psd`;

afterEach(cleanup);

describe("FilePanel", () => {
  const props = { untracked: [], busy: false, onAddFiles: vi.fn(), onAddFolder: vi.fn(), onTrack: vi.fn(), onUntrack: vi.fn(), onClose: vi.fn() };
  it("filters both lists by path while retaining their actions", () => {
    const onTrack = vi.fn(); const onUntrack = vi.fn();
    render(<FilePanel {...props} tracked={["assets/A.png", "notes.txt"]} untracked={["assets/B.png", "draft.txt"]} onTrack={onTrack} onUntrack={onUntrack} />);
    fireEvent.change(screen.getByRole("searchbox"), { target: { value: "ASSETS/" } });
    expect(screen.queryByText("notes.txt")).toBeNull();
    expect(screen.queryByText("draft.txt")).toBeNull();
    expect(screen.getByRole("status").textContent).toBe("追跡中 1件・未追跡 1件が一致");
    fireEvent.click(screen.getByRole("button", { name: "追跡する" }));
    fireEvent.click(screen.getByRole("button", { name: "追跡解除" }));
    expect(onTrack).toHaveBeenCalledWith("assets/B.png");
    expect(onUntrack).toHaveBeenCalledWith("assets/A.png");
  });

  it("chooses a cover file and offers applying or clearing it", () => {
    const onSetCover = vi.fn();
    const onClearCover = vi.fn();
    const onApplyCover = vi.fn();
    render(<FilePanel {...props} tracked={["poster.png", "notes.md"]} cover={{ file_id: "f", path: "poster.png" }} onSetCover={onSetCover} onClearCover={onClearCover} onApplyCover={onApplyCover} />);

    expect(screen.queryByRole("button", { name: "poster.pngをサムネイル自動生成元に設定" })).toBeNull();
    expect(screen.getByText("生成元")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "notes.mdをサムネイル自動生成元に設定" }));
    fireEvent.click(screen.getByRole("button", { name: "既存の葉へ適用" }));
    fireEvent.click(screen.getByRole("button", { name: "解除" }));
    expect(onSetCover).toHaveBeenCalledWith("notes.md");
    expect(onApplyCover).toHaveBeenCalledOnce();
    expect(onClearCover).toHaveBeenCalledOnce();
  });

  it("explains a cover that is no longer tracked", () => {
    render(<FilePanel {...props} tracked={[]} cover={{ file_id: "f", path: null }} onSetCover={vi.fn()} onClearCover={vi.fn()} onApplyCover={vi.fn()} />);
    expect(screen.getByText(/追跡を解除したファイルが指定されています/)).toBeTruthy();
  });

  it("keeps the full long path readable and its row actions usable", () => {
    const onUntrack = vi.fn();
    const onTrack = vi.fn();
    render(<FilePanel tracked={[longPath]} untracked={[`${longPath}.bak`]} busy={false} onAddFiles={vi.fn()} onAddFolder={vi.fn()} onTrack={onTrack} onUntrack={onUntrack} onClose={vi.fn()} />);

    expect(screen.getByTitle(longPath).textContent).toBe(longPath);
    fireEvent.click(screen.getByRole("button", { name: "追跡解除" }));
    fireEvent.click(screen.getByRole("button", { name: "追跡する" }));

    expect(onUntrack).toHaveBeenCalledWith(longPath);
    expect(onTrack).toHaveBeenCalledWith(`${longPath}.bak`);
  });
});
