import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

/** A folder the GUI was asked to open from outside, e.g. Explorer's "Sproutで開く". */
export interface LaunchRequest {
  path: string;
  /** Set when the path cannot be opened as a folder. */
  problem: "not_found" | "not_directory" | null;
}

/** Take the folder waiting to be opened, if any; each request is returned only once. */
export async function takeLaunchRequest(): Promise<LaunchRequest | null> {
  return (await invoke<LaunchRequest | null>("take_launch_request")) ?? null;
}

/** Call `handler` whenever another launch hands a folder to this window. Resolves to an unsubscribe. */
export async function onLaunchRequest(handler: () => void): Promise<() => void> {
  return listen("launch-request", handler);
}

/** The part of `sprout info --json` used to find the project a subfolder belongs to. */
export interface RepositoryInfo {
  repository: { root: string };
}

export function launchProblemMessage(request: LaunchRequest): string {
  return request.problem === "not_directory"
    ? `フォルダではないため開けません: ${request.path}`
    : `フォルダが見つからないため開けません: ${request.path}`;
}

/** Windows paths are case-insensitive, so compare the folder the same way Explorer does. */
export function sameFolder(left: string, right: string): boolean {
  const normalize = (path: string) => path.replace(/[\\/]+$/, "").replace(/\//g, "\\").toLowerCase();
  return normalize(left) === normalize(right);
}
