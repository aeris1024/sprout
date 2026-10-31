import { invoke } from "@tauri-apps/api/core";
import { translateCliError } from "./cliErrors";

export interface StatusChange {
  state: "added" | "modified" | "deleted" | "renamed" | string;
  path: string;
  /** Saved spelling of the path when only its spelling changed. */
  previous_path?: string;
}

export interface SproutStatus {
  branch: string;
  branch_id: string;
  /** Snapshot the working tree was last placed on; null before the first commit. */
  current_commit: string | null;
  at_branch_tip: boolean;
  changes: StatusChange[];
  tracked?: string[];
  untracked?: string[];
  /** File thumbnails are made from; path is null once it is no longer tracked. */
  cover?: { file_id: string; path: string | null };
}

export interface CoverApplyResult {
  dry_run: boolean;
  applied: string[];
  skipped: { commit_id: string; reason: string }[];
  kept: number;
}

const coverReasons: Record<string, string> = {
  cover_missing: "サムネイル自動生成元が追跡されていません",
  cover_not_image: "サムネイル自動生成元が対応する画像ではありません",
  cover_animated: "アニメーション画像は使えません",
  cover_too_large: "サムネイル自動生成元の画像が大きすぎます",
  cover_unreadable: "サムネイル自動生成元を読み取れませんでした",
};

export function coverReasonLabel(reason: string | null | undefined): string {
  return (reason && coverReasons[reason]) || "サムネイル自動生成元から作れませんでした";
}

export interface PathOperationResult {
  paths: string[];
}

export interface CommitResult {
  id: string;
  branch: string;
  branch_id: string;
  created_branch?: boolean;
  message: string;
  removed_paths: string[];
  /** Present when a cover file is set and no thumbnail was given. */
  cover?: { applied: boolean; reason: string | null };
}

export interface ProjectLabel {
  name: string;
  leaf_count: number;
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

export interface CommitAttachment {
  id: string;
  position: number;
  commit_id: string;
  role: string;
  original_name: string;
  display_name?: string;
  description?: string;
  media_type: string;
  object_hash: string;
  size: number;
  created_at: string;
  updated_at: string;
}

export interface CommitThumbnail extends CommitAttachment {
  role: "thumbnail";
}

export interface CommitFile {
  path: string;
  object_hash: string;
  size: number;
  mtime_ns: number;
  file_id?: string;
}

export interface CommitDetail extends CommitLogEntry {
  branch_id: string;
  branch_name: string;
  thumbnail: CommitThumbnail | null;
  attachments: CommitAttachment[];
  files: CommitFile[];
}

export interface BranchInfo {
  id: string;
  name: string;
  commit_id: string | null;
  comment: string;
  current: boolean;
  created_at?: string;
}

export interface DeletedBranch {
  id: string;
  name: string;
  comment: string;
  created_at: string;
  deleted_at: string;
}

export interface GraphCommit extends CommitLogEntry {
  branch_id: string;
  branch_name: string;
  attachments: CommitAttachment[];
}

export interface GraphTag {
  name: string;
  commit_id: string;
  comment: string;
  created_at: string;
}

export interface BudFile {
  path: string;
  object_hash: string;
  size: number;
  mtime_ns: number;
  file_id?: string;
}

export interface Bud {
  id: string;
  /** Optional name given by the user; empty for automatically kept buds. */
  name?: string;
  base_commit_id: string | null;
  branch_id: string;
  branch_name: string;
  created_at: string;
  changes: StatusChange[];
  files: BudFile[];
}

export interface CommitGraph {
  current_commit: string | null;
  at_branch_tip: boolean;
  commits: GraphCommit[];
  /** Live branches only; deleted branches remain identifiable through commit and bud branch IDs. */
  branches: BranchInfo[];
  deleted_branches?: DeletedBranch[];
  tags: GraphTag[];
  buds: Bud[];
}

export interface GoResult {
  current_commit: string | null;
  branch: string;
  branch_id: string;
  at_branch_tip: boolean;
  bud: Bud | null;
  changes: StatusChange[];
}

/** What `leaf delete` changes, or would change with --dry-run. */
export interface CommitDeletion {
  dry_run: boolean;
  commit: { id: string; created_at: string; message: string };
  parent_id: string | null;
  moved_branches: { id: string; name: string; current: boolean }[];
  moved_current: boolean;
  reconnected_children: string[];
  rebased_buds: string[];
  reclaimable_objects: string[];
  reclaimable_bytes: number;
}

export interface RepositoryStats {
  commits: number;
  branches: number;
  tracked_paths: number;
  buds: number;
  objects: number;
  objects_bytes: number;
  logical_bytes: number;
  unique_bytes: number;
  dedup_saved_bytes: number;
}

export interface GcResult {
  dry_run: boolean;
  removed_objects: number;
  removed_temps: number;
  freed_bytes: number;
  objects: string[];
  temps: string[];
}

export interface DoctorReport {
  ok: boolean;
  checked_objects: number;
  issues: { kind: string; detail: string }[];
}

export interface SproutCliError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  /** The message is already in the GUI's words and is not to be looked up again. */
  translated?: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export interface TrashItem {
  id: string;
  kind: "commit" | "preview_delete" | "preview_replace" | "bud_delete" | "discard" | "note_delete" | "tag_delete" | "branch_delete";
  target_id: string;
  title: string;
  created_at: string;
  protected_bytes: number;
  reclaimable_bytes: number;
  objects: string[];
  changes?: { table: string; before: Record<string, unknown>; after: Record<string, unknown> | null }[];
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
    const code = typeof candidate.code === "string" ? candidate.code : "gui_error";
    if (typeof candidate.message !== "string") {
      return { code, message: "Sproutの操作に失敗しました", details };
    }
    // Errors pass through here again on their way to the notice, some with text added.
    if (candidate.translated === true) {
      return { code, message: candidate.message, details, translated: true };
    }
    const message = translateCliError(code, candidate.message, details);
    return { code, message, details, ...(message !== candidate.message && { translated: true }) };
  }

  return {
    code: "gui_error",
    message: "Sproutの操作に失敗しました",
    details: {},
  };
}

export function isUninitializedProject(error: SproutCliError): boolean {
  // CLIs older than the not_initialized code report this only in the message.
  return error.code === "not_initialized" || error.message.includes("not inside a Sprout project");
}

export interface BranchIdentity {
  /** Name the branch had when the commit or bud was created. */
  createdName: string;
  /** Current name of the same branch, or null when it has been deleted. */
  currentName: string | null;
}

/** Resolve a recorded branch by ID so renamed and deleted branches are not confused with reused names. */
export function branchIdentity(branchId: string, createdName: string, branches: BranchInfo[]): BranchIdentity {
  return { createdName, currentName: branches.find((branch) => branch.id === branchId)?.name ?? null };
}

export function branchIdentityLabel({ createdName, currentName }: BranchIdentity): string {
  if (currentName === null) return `${createdName}（削除済み）`;
  if (currentName !== createdName) return `${currentName}（作成時: ${createdName}）`;
  return currentName;
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KiB`;
  if (size < 1024 * 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)} MiB`;
  return `${(size / 1024 / 1024 / 1024).toFixed(1)} GiB`;
}

export function formatLocalTime(value: string): string {
  return new Date(value).toLocaleString("ja-JP");
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
