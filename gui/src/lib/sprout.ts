import { invoke } from "@tauri-apps/api/core";

export interface StatusChange {
  state: "added" | "modified" | "deleted" | string;
  path: string;
}

export interface SproutStatus {
  branch: string;
  changes: StatusChange[];
  tracked?: string[];
  untracked?: string[];
}

export interface PathOperationResult {
  paths: string[];
}

export interface CommitResult {
  id: string;
  branch: string;
  message: string;
  removed_paths: string[];
}

export interface CommitLogEntry {
  id: string;
  parent_id: string | null;
  created_at: string;
  message: string;
  note: string | null;
  note_updated_at: string | null;
  labels: string[];
}

export interface CommitThumbnail {
  commit_id: string;
  role: "thumbnail";
  original_name: string;
  media_type: string;
  object_hash: string;
  size: number;
  created_at: string;
  updated_at: string;
}

export interface CommitFile {
  path: string;
  object_hash: string;
  size: number;
  mtime_ns: number;
}

export interface CommitDetail extends CommitLogEntry {
  branch_name: string;
  thumbnail: CommitThumbnail | null;
  files: CommitFile[];
}

export interface BranchInfo {
  name: string;
  commit_id: string | null;
  comment: string;
  current: boolean;
}

export interface SproutCliError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function normalizeCliError(error: unknown): SproutCliError {
  let candidate = error;
  if (typeof candidate === "string") {
    const message = candidate;
    try {
      candidate = JSON.parse(candidate);
    } catch {
      return { code: "gui_error", message, details: {} };
    }
  }

  if (isRecord(candidate)) {
    const details = isRecord(candidate.details) ? candidate.details : {};
    return {
      code: typeof candidate.code === "string" ? candidate.code : "gui_error",
      message:
        typeof candidate.message === "string"
          ? candidate.message
          : "Sproutの操作に失敗しました",
      details,
    };
  }

  return {
    code: "gui_error",
    message: "Sproutの操作に失敗しました",
    details: {},
  };
}

export function isUninitializedProject(error: SproutCliError): boolean {
  return error.message.includes("not inside a Sprout project");
}

export function canDiscardChanges(error: SproutCliError): boolean {
  return error.code === "uncommitted_changes" && error.details.can_discard === true;
}

export async function runSprout<T>(
  projectDir: string,
  args: string[],
  sproutProgram: string,
): Promise<T> {
  return invoke<T>("run_sprout", {
    projectDir,
    args,
    sproutProgram: sproutProgram.trim() || null,
  });
}
