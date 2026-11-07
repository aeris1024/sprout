import { runSprout, type CommitAttachment } from "./sprout";

/** Display image of a preview, as `leaf preview image` returns it. */
export interface PreviewImageData {
  format?: string;
  data_url: string;
  width: number;
  height: number;
  display_width: number;
  display_height: number;
}

/** Display images are large, so only the last few viewed are kept for going back. */
const MAX_CACHE_ENTRIES = 8;
const cache = new Map<string, PreviewImageData>();
const pending = new Map<string, Promise<PreviewImageData>>();

export function previewImageKey(projectDir: string, program: string, attachment: CommitAttachment): string {
  return [projectDir, program, attachment.commit_id, attachment.id, attachment.object_hash].join("\u0000");
}

/** Whether the GUI tries to decode this preview as a still image. */
export function isViewableImage(attachment: CommitAttachment): boolean {
  return attachment.media_type.startsWith("image/") || /\.(png|jpe?g|webp|bmp)$/i.test(attachment.original_name);
}

export function clearPreviewImageCache(): void {
  cache.clear();
  pending.clear();
}

/** A display image already loaded, without asking the CLI. */
export function cachedPreviewImage(key: string): PreviewImageData | undefined {
  return cache.get(key);
}

export function loadPreviewImage(projectDir: string, program: string, attachment: CommitAttachment): Promise<PreviewImageData> {
  const key = previewImageKey(projectDir, program, attachment);
  const existing = cache.get(key);
  if (existing) {
    cache.delete(key);
    cache.set(key, existing);
    return Promise.resolve(existing);
  }
  const inFlight = pending.get(key);
  if (inFlight) return inFlight;
  const request = runSprout<PreviewImageData>(projectDir, ["leaf", "preview", "image", attachment.commit_id, attachment.id], program)
    .then((image) => {
      if (pending.get(key) === request) {
        cache.set(key, image);
        while (cache.size > MAX_CACHE_ENTRIES) {
          const oldest = cache.keys().next().value;
          if (typeof oldest !== "string") break;
          cache.delete(oldest);
        }
      }
      return image;
    })
    .finally(() => { if (pending.get(key) === request) pending.delete(key); });
  pending.set(key, request);
  return request;
}
