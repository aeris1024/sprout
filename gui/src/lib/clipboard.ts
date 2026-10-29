import { invoke } from "@tauri-apps/api/core";

export const THUMBNAIL_MEDIA_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
export const THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024;

/** Return the first image in a paste, or null when the paste carries no image. */
export function clipboardImage(data: DataTransfer | null): File | null {
  if (!data) return null;
  for (const item of Array.from(data.items ?? [])) {
    if (item.kind === "file" && item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) return file;
    }
  }
  return Array.from(data.files ?? []).find((file) => file.type.startsWith("image/")) ?? null;
}

/** Explain why an image cannot be a thumbnail, or return null when it can. */
export function thumbnailImageProblem(file: File): string | null {
  if (!THUMBNAIL_MEDIA_TYPES.has(file.type)) {
    return "貼り付けた画像はサムネイルに使えない形式です（PNG・JPEG・WebPに対応）";
  }
  if (file.size > THUMBNAIL_MAX_BYTES) return "貼り付けた画像がサムネイルの上限（2 MiB）を超えています";
  return null;
}

function readBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result);
      resolve(result.slice(result.indexOf(",") + 1));
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

/** Save a pasted image to a temporary file and return its path for the CLI. */
export async function savePastedThumbnail(file: File): Promise<string> {
  return invoke<string>("save_pasted_thumbnail", { mediaType: file.type, data: await readBase64(file) });
}

export function discardPastedThumbnail(path: string): Promise<void> {
  return invoke<void>("discard_pasted_thumbnail", { path });
}

/** Store any pasted file temporarily; unlike thumbnails, previews have no format limit. */
export async function savePastedPreview(file: File): Promise<string> {
  return invoke<string>("save_pasted_preview", { name: file.name || "clipboard.bin", data: await readBase64(file) });
}

/** Native Explorer file references are not always exposed as WebView File objects. */
export function readClipboardFiles(): Promise<string[]> {
  return invoke<string[]>("read_clipboard_files");
}
