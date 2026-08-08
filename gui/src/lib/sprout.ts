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
