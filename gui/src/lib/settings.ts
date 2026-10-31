import { load, type Store } from "@tauri-apps/plugin-store";
import { isTauri } from "@tauri-apps/api/core";

const SETTINGS_FILE = "settings.json";
const RECENT_LIMIT = 8;
const BROWSER_SETTINGS_KEY = "sprout.settings";

export interface AppSettings {
  recentProjects: string[];
  sproutProgram: string;
  panelWidth?: number;
}

const defaultSettings: AppSettings = {
  recentProjects: [],
  sproutProgram: "",
};

let storePromise: Promise<Store> | undefined;

function appStore(): Promise<Store> {
  storePromise ??= load(SETTINGS_FILE, {
    autoSave: 100,
    defaults: {
      recentProjects: defaultSettings.recentProjects,
      sproutProgram: defaultSettings.sproutProgram,
    },
  });
  return storePromise;
}

export function nextRecentProjects(current: string[], project: string): string[] {
  const normalized = project.trim();
  return [normalized, ...current.filter((item) => item !== normalized)].slice(
    0,
    RECENT_LIMIT,
  );
}

export function removeRecentProject(current: string[], project: string): string[] {
  return current.filter((item) => item !== project);
}

function browserSettings(): AppSettings {
  const saved = window.localStorage.getItem(BROWSER_SETTINGS_KEY);
  if (!saved) return defaultSettings;
  return { ...defaultSettings, ...JSON.parse(saved) } as AppSettings;
}

export async function loadSettings(): Promise<AppSettings> {
  if (!isTauri()) return browserSettings();
  const store = await appStore();
  return {
    recentProjects:
      (await store.get<string[]>("recentProjects")) ??
      defaultSettings.recentProjects,
    sproutProgram:
      (await store.get<string>("sproutProgram")) ??
      defaultSettings.sproutProgram,
    panelWidth: await store.get<number>("panelWidth"),
  };
}

export async function saveSettings(settings: AppSettings): Promise<void> {
  if (!isTauri()) {
    window.localStorage.setItem(BROWSER_SETTINGS_KEY, JSON.stringify({ ...browserSettings(), ...settings }));
    return;
  }
  const store = await appStore();
  await store.set("recentProjects", settings.recentProjects);
  await store.set("sproutProgram", settings.sproutProgram);
  await store.save();
}

/** Saved apart from the other settings, which are written from state that does not hold the width. */
export async function savePanelWidth(panelWidth: number): Promise<void> {
  if (!isTauri()) {
    window.localStorage.setItem(BROWSER_SETTINGS_KEY, JSON.stringify({ ...browserSettings(), panelWidth }));
    return;
  }
  const store = await appStore();
  await store.set("panelWidth", panelWidth);
  await store.save();
}
