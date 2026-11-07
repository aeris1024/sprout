// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PreviewViewer from "./PreviewViewer";
import { runSprout, type CommitAttachment } from "../lib/sprout";
import { clearPreviewImageCache } from "../lib/previewImages";

vi.mock("../lib/sprout", async (original) => ({ ...await original<typeof import("../lib/sprout")>(), runSprout: vi.fn() }));
afterEach(() => { cleanup(); vi.mocked(runSprout).mockReset(); clearPreviewImageCache(); });

const base = { commit_id: "commit", role: "preview", size: 2048, display_name: "", description: "" } as CommitAttachment;
const front = { ...base, id: "front", object_hash: "h1", position: 0, original_name: "front.png", media_type: "image/png", display_name: "正面" };
const side = { ...base, id: "side", object_hash: "h2", position: 1, original_name: "side.jpg", media_type: "image/jpeg", description: "右から見た図" };
const model = { ...base, id: "model", object_hash: "h3", position: 2, original_name: "model.stl", media_type: "model/stl" };
const reply = (name: string) => ({ format: "PNG", data_url: `data:image/png;base64,${name}`, width: 3000, height: 1500, display_width: 2048, display_height: 1024 });

function renderViewer(props: Partial<Parameters<typeof PreviewViewer>[0]> = {}) {
  vi.mocked(runSprout).mockImplementation(async (_dir, args) => reply(String(args[4])));
  const onClose = vi.fn();
  const onExport = vi.fn();
  render(<PreviewViewer projectDir="project" program="sprout" leafTitle="モデルの確認" previews={[front, side, model]} startId="front" busy={false} onExport={onExport} onClose={onClose} {...props} />);
  return { onClose, onExport, dialog: screen.getByRole("dialog") };
}

it("loads only the shown image, switches in saved order, and reuses images already seen", async () => {
  const user = userEvent.setup();
  const { dialog } = renderViewer();
  expect((await within(dialog).findByRole("img", { name: "正面" })).getAttribute("src")).toBe("data:image/png;base64,front");
  expect(runSprout).toHaveBeenCalledTimes(1);
  expect(runSprout).toHaveBeenCalledWith("project", ["leaf", "preview", "image", "commit", "front"], "sprout");
  expect(within(dialog).getByText("1 / 3")).toBeTruthy();
  expect(within(dialog).getByText(/元の寸法 3000 × 1500 px（表示用に 2048 × 1024 px へ縮小済み）/)).toBeTruthy();

  await user.keyboard("{ArrowRight}");
  expect(await within(dialog).findByRole("img", { name: "side.jpg" })).toBeTruthy();
  expect(within(dialog).getByText("2 / 3")).toBeTruthy();
  expect(within(dialog).getByText("右から見た図")).toBeTruthy();
  await user.click(within(dialog).getByRole("button", { name: "次のプレビュー" }));
  expect(within(dialog).getByText("3 / 3")).toBeTruthy();
  await user.keyboard("{ArrowRight}");
  expect(within(dialog).getByText("1 / 3")).toBeTruthy();
  expect(within(dialog).getByRole("img", { name: "正面" })).toBeTruthy();
  await user.keyboard("{ArrowLeft}");
  await user.click(within(dialog).getByRole("button", { name: "2. side.jpg" }));
  expect(within(dialog).getByRole("button", { name: "2. side.jpg" }).getAttribute("aria-current")).toBe("true");
  expect(within(dialog).getByRole("img", { name: "side.jpg" })).toBeTruthy();
  expect(runSprout).toHaveBeenCalledTimes(2);
});

it("starts at the chosen preview and switches between fitting the window and actual size", async () => {
  const user = userEvent.setup();
  renderViewer({ startId: "side" });
  const image = await screen.findByRole("img", { name: "side.jpg" });
  expect(runSprout).toHaveBeenCalledWith("project", ["leaf", "preview", "image", "commit", "side"], "sprout");
  expect(image.classList.contains("actual")).toBe(false);
  expect(screen.getByText(/ウィンドウに合わせて表示中/)).toBeTruthy();
  const actual = screen.getByRole("button", { name: "等倍" });
  await user.click(actual);
  expect(actual.getAttribute("aria-pressed")).toBe("true");
  expect(image.classList.contains("actual")).toBe(true);
  expect(image.style.width).toBe("2048px");
  expect(screen.getByText(/等倍で表示中/)).toBeTruthy();
  await user.click(image);
  expect(actual.getAttribute("aria-pressed")).toBe("false");
});

it("shows previews that are not images as a card that can be exported", async () => {
  const user = userEvent.setup();
  const { onExport } = renderViewer({ startId: "model" });
  expect(screen.getByText("この形式はここでは表示できません。取り出して確認してください。")).toBeTruthy();
  expect(screen.getByRole("button", { name: "3. model.stl（画像以外）" })).toBeTruthy();
  expect(runSprout).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "取り出す" }));
  expect(onExport).toHaveBeenCalledWith("model", "model.stl");
});

it("reports images that cannot be shown, then retries", async () => {
  const user = userEvent.setup();
  const { onExport } = renderViewer();
  vi.mocked(runSprout).mockReset();
  vi.mocked(runSprout).mockRejectedValueOnce({ code: "invalid_preview_image", message: "Broken image", details: {} }).mockResolvedValueOnce(reply("again"));
  await user.click(screen.getByRole("button", { name: "2. side.jpg" }));
  expect((await screen.findByRole("alert")).textContent).toContain("Broken image");
  await user.click(screen.getByRole("button", { name: "取り出す" }));
  expect(onExport).toHaveBeenCalledWith("side", "side.jpg");
  await user.click(screen.getByRole("button", { name: "画像を再読み込み" }));
  expect((await screen.findByRole("img", { name: "side.jpg" })).getAttribute("src")).toBe("data:image/png;base64,again");
});

it("closes with Escape or the close button without letting keys reach the rest of the window, and gives the keyboard back", async () => {
  const user = userEvent.setup();
  const opener = document.createElement("button");
  opener.textContent = "葉";
  document.body.append(opener);
  opener.focus();
  const outside = vi.fn();
  window.addEventListener("keydown", outside);
  const pasted = vi.fn();
  window.addEventListener("paste", pasted);
  try {
    const { onClose, dialog } = renderViewer();
    expect(document.activeElement).toBe(dialog);
    await user.keyboard("{ArrowRight}{Control>}s{/Control}");
    fireEvent.paste(dialog);
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(outside).not.toHaveBeenCalled();
    expect(pasted).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "プレビューの表示を閉じる" }));
    expect(onClose).toHaveBeenCalledTimes(2);
    cleanup();
    expect(document.activeElement).toBe(opener);
  } finally {
    window.removeEventListener("keydown", outside);
    window.removeEventListener("paste", pasted);
    opener.remove();
  }
});

it("keeps Tab inside the viewer", async () => {
  const user = userEvent.setup();
  const outside = document.createElement("button");
  outside.textContent = "外";
  document.body.prepend(outside);
  try {
    const { dialog } = renderViewer({ previews: [front] });
    await waitFor(() => expect(screen.getByRole("img", { name: "正面" })).toBeTruthy());
    for (let index = 0; index < 4; index += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
    await user.tab({ shift: true });
    expect(dialog.contains(document.activeElement)).toBe(true);
    expect(screen.queryByRole("button", { name: "次のプレビュー" })).toBeNull();
    expect(screen.queryByRole("list", { name: "プレビューの一覧" })).toBeNull();
  } finally {
    outside.remove();
  }
});

it("moves to the preview now in place when the shown one is removed", async () => {
  const onClose = vi.fn();
  vi.mocked(runSprout).mockImplementation(async (_dir, args) => reply(String(args[4])));
  const view = render(<PreviewViewer projectDir="project" program="sprout" leafTitle="葉" previews={[front, side, model]} startId="side" busy={false} onExport={vi.fn()} onClose={onClose} />);
  await screen.findByRole("img", { name: "side.jpg" });
  view.rerender(<PreviewViewer projectDir="project" program="sprout" leafTitle="葉" previews={[front, model]} startId="side" busy={false} onExport={vi.fn()} onClose={onClose} />);
  expect(screen.getByText("2 / 2")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "model.stl" })).toBeTruthy();
});
