import { beforeEach, describe, expect, it, vi } from "vitest";
import { clearThumbnailCache, loadThumbnailDataUrl, thumbnailCacheKey } from "./thumbnails";
import type { CommitAttachment } from "./sprout";

const mocks = vi.hoisted(() => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: mocks.invoke }));

const attachment: CommitAttachment = {
  commit_id: "a".repeat(64),
  role: "thumbnail",
  original_name: "preview.png",
  media_type: "image/png",
  object_hash: "b".repeat(64),
  size: 3,
  created_at: "2026-08-09T00:00:00+00:00",
  updated_at: "2026-08-09T00:00:00+00:00",
};

describe("thumbnail cache", () => {
  beforeEach(() => {
    clearThumbnailCache();
    mocks.invoke.mockReset();
    mocks.invoke.mockResolvedValue("data:image/png;base64,AQID");
  });

  it("keys entries by project, commit, object hash, and media type", () => {
    expect(thumbnailCacheKey("C:/work", attachment)).toContain(attachment.object_hash);
    expect(thumbnailCacheKey("C:/work", attachment)).not.toBe(
      thumbnailCacheKey("C:/other", attachment),
    );
  });

  it("deduplicates concurrent and repeated thumbnail retrieval", async () => {
    const first = loadThumbnailDataUrl("C:/work", attachment, "sprout");
    const second = loadThumbnailDataUrl("C:/work", attachment, "sprout");
    await expect(Promise.all([first, second])).resolves.toEqual([
      "data:image/png;base64,AQID",
      "data:image/png;base64,AQID",
    ]);
    await loadThumbnailDataUrl("C:/work", attachment, "sprout");
    expect(mocks.invoke).toHaveBeenCalledTimes(1);
  });

  it("retrieves a replacement when the object hash changes", async () => {
    await loadThumbnailDataUrl("C:/work", attachment, "");
    await loadThumbnailDataUrl("C:/work", { ...attachment, object_hash: "c".repeat(64) }, "");
    expect(mocks.invoke).toHaveBeenCalledTimes(2);
  });
});
