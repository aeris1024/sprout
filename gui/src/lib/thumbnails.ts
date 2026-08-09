import { invoke } from "@tauri-apps/api/core";
import type { CommitAttachment } from "./sprout";

const MAX_CACHE_ENTRIES = 128;
const cache = new Map<string, string>();
const pending = new Map<string, Promise<string>>();

export function thumbnailCacheKey(projectDir: string, attachment: CommitAttachment): string {
  return [projectDir, attachment.commit_id, attachment.object_hash, attachment.media_type].join("\u0000");
}

export function clearThumbnailCache(): void {
  cache.clear();
  pending.clear();
}

export function loadThumbnailDataUrl(
  projectDir: string,
  attachment: CommitAttachment,
  sproutProgram: string,
): Promise<string> {
  const key = thumbnailCacheKey(projectDir, attachment);
  const existing = cache.get(key);
  if (existing) {
    cache.delete(key);
    cache.set(key, existing);
    return Promise.resolve(existing);
  }
  const inFlight = pending.get(key);
  if (inFlight) return inFlight;

  const request = invoke<string>("read_sprout_thumbnail", {
    projectDir,
    commitId: attachment.commit_id,
    mediaType: attachment.media_type,
    sproutProgram: sproutProgram.trim() || null,
  })
    .then((dataUrl) => {
      cache.set(key, dataUrl);
      while (cache.size > MAX_CACHE_ENTRIES) {
        const oldest = cache.keys().next().value;
        if (typeof oldest !== "string") break;
        cache.delete(oldest);
      }
      return dataUrl;
    })
    .finally(() => pending.delete(key));
  pending.set(key, request);
  return request;
}
