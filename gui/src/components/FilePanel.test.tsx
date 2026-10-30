// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import FilePanel from "./FilePanel";

const longPath = `素材/${"とても長い日本語のフォルダ名/".repeat(8)}最終版のファイル名.psd`;

afterEach(cleanup);

describe("FilePanel", () => {
  const props = { untracked: [], busy: false, onAddFiles: vi.fn(), onAddFolder: vi.fn(), onTrack: vi.fn(), onUntrack: vi.fn(), onClose: vi.fn() };

  it("chooses a cover file and offers applying or clearing it", () => {
    const onSetCover = vi.fn();
    const onClearCover = vi.fn();
    const onApplyCover = vi.fn();
    render(<FilePanel {...props} tracked={["poster.png", "notes.md"]} cover={{ file_id: "f", path: "poster.png" }} onSetCover={onSetCover} onClearCover={onClearCover} onApplyCover={onApplyCover} />);

    expect(screen.queryByRole("button", { name: "poster.pngを代表にする" })).toBeNull();
    expect(screen.getByText("代表")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "notes.mdを代表にする" }));
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
