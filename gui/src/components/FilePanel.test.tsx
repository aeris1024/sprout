// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import FilePanel from "./FilePanel";

const longPath = `素材/${"とても長い日本語のフォルダ名/".repeat(8)}最終版のファイル名.psd`;

afterEach(cleanup);

describe("FilePanel", () => {
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
