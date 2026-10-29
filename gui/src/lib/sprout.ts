import { invoke } from "@tauri-apps/api/core";

export interface StatusChange {
  state: "added" | "modified" | "deleted" | string;
  path: string;
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
}

export interface Bud {
  id: string;
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
  tags: GraphTag[];
  buds: Bud[];
}

export interface GoResult {
  current_commit: string;
  branch: string;
  branch_id: string;
  at_branch_tip: boolean;
  bud: Bud | null;
  changes: StatusChange[];
}

/** What `delete-commit` changes, or would change with --dry-run. */
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
