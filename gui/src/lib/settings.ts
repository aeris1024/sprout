import { load, type Store } from "@tauri-apps/plugin-store";
import { isTauri } from "@tauri-apps/api/core";

const SETTINGS_FILE = "settings.json";
const RECENT_LIMIT = 8;
const BROWSER_SETTINGS_KEY = "sprout.settings";

export interface AppSettings {
  recentProjects: string[];
  sproutProgram: string;
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

export async function loadSettings(): Promise<AppSettings> {
  if (!isTauri()) {
    const saved = window.localStorage.getItem(BROWSER_SETTINGS_KEY);
    if (!saved) return defaultSettings;
    return { ...defaultSettings, ...JSON.parse(saved) } as AppSettings;
  }
  const store = await appStore();
  return {
    recentProjects:
      (await store.get<string[]>("recentProjects")) ??
      defaultSettings.recentProjects,
    sproutProgram:
      (await store.get<string>("sproutProgram")) ??
      defaultSettings.sproutProgram,
  };
}

export async function saveSettings(settings: AppSettings): Promise<void> {
  if (!isTauri()) {
    window.localStorage.setItem(BROWSER_SETTINGS_KEY, JSON.stringify(settings));
    return;
  }
  const store = await appStore();
  await store.set("recentProjects", settings.recentProjects);
  await store.set("sproutProgram", settings.sproutProgram);
  await store.save();
}
