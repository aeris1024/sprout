// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import PreviewPanel, { type PreviewActions } from "./PreviewPanel";
import { runSprout, type CommitAttachment } from "../lib/sprout";
vi.mock("../lib/sprout", async (original) => ({ ...await original<typeof import("../lib/sprout")>(), runSprout: vi.fn() }));
afterEach(() => { cleanup(); vi.mocked(runSprout).mockReset(); });
const first = { id: "one", commit_id: "commit", object_hash: "hash1", role: "preview", position: 0, original_name: "one.png", media_type: "image/png", size: 123 } as CommitAttachment;
const second = { ...first, id: "two", position: 1, original_name: "two.jpg" };
const actions: PreviewActions = { add: vi.fn(), paste: vi.fn(), pastePaths: vi.fn(), replace: vi.fn(), remove: vi.fn(), export: vi.fn(), order: vi.fn() };
const props = { attachments: [first, second], busy: false, actions, projectDir: "project", program: "sprout", commitId: "commit" };
const reply = { data_url: "data:image/png;base64,AA==", width: 3000, height: 1500, display_width: 2048, display_height: 1024 };
it("loads only the selected image and closes the display", async () => {
  vi.mocked(runSprout).mockResolvedValue(reply);
  render(<PreviewPanel {...props} />);
  expect(runSprout).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "one.pngを表示" }));
  expect((await screen.findByRole("img", { name: "one.png" })).getAttribute("src")).toBe(reply.data_url);
  expect(runSprout).toHaveBeenCalledWith("project", ["preview", "image", "commit", "one"], "sprout");
  expect(screen.getByText("3000 × 1500 px（表示用に縮小）")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "画像表示を閉じる" }));
  expect(screen.queryByRole("img")).toBeNull();
});
it("ignores old replies when selecting another attachment", async () => {
  let finish!: (value: unknown) => void;
  vi.mocked(runSprout).mockReturnValueOnce(new Promise((resolve) => { finish = resolve; })).mockResolvedValueOnce(reply);
  render(<PreviewPanel {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "one.pngを表示" }));
  fireEvent.click(screen.getByRole("button", { name: "two.jpgを表示" }));
  await screen.findByRole("img", { name: "two.jpg" });
  finish({ ...reply, data_url: "stale" });
  await waitFor(() => expect(screen.getByRole("img").getAttribute("src")).toBe(reply.data_url));
});
it("shows reused image format metadata only after selection", async () => {
  vi.mocked(runSprout).mockResolvedValue({ ...reply, format: "PNG" });
  render(<PreviewPanel {...props} />);
  expect(runSprout).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "one.pngを表示" }));
  expect(await screen.findByText("PNG · 3000 × 1500 px（表示用に縮小）")).toBeTruthy();
});
it.each(["hash", "delete", "project", "commit"])("clears displayed content after %s changes", async (change) => {
  vi.mocked(runSprout).mockResolvedValue(reply);
  const view = render(<PreviewPanel {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "one.pngを表示" }));
  await screen.findByRole("img");
  view.rerender(<PreviewPanel {...props} attachments={change === "delete" ? [second] : change === "hash" ? [{ ...first, object_hash: "new" }, second] : props.attachments} projectDir={change === "project" ? "other" : "project"} commitId={change === "commit" ? "other" : "commit"} />);
  expect(screen.queryByRole("img")).toBeNull();
  expect(runSprout).toHaveBeenCalledTimes(1);
});
it("reports decode failures, keeps export available, and retries", async () => {
  vi.mocked(runSprout).mockRejectedValueOnce({ code: "invalid_preview_image", message: "Broken image", details: {} }).mockResolvedValueOnce(reply);
  render(<PreviewPanel {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "one.pngを表示" }));
  await screen.findByText("Broken image");
  expect(screen.getByRole("button", { name: "one.pngを取り出す" })).toBeTruthy();
  fireEvent.click(screen.getByText("画像を再読み込み"));
  const image = await screen.findByRole("img");
  fireEvent.error(image);
  await screen.findByText("画像を表示できませんでした。取り出して確認してください。");
});
