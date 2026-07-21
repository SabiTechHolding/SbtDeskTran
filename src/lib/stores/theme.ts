import { writable } from "svelte/store";
import { invoke } from "@tauri-apps/api/core";

type ThemeName = "dark" | "light";

function createThemeStore() {
  const { subscribe, set, update } = writable<{ current: ThemeName }>({
    current: "dark",
  });

  return {
    subscribe,
    toggle: () =>
      update((state) => {
        const next = state.current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        invoke("save_setting", { key: "theme", value: next });
        return { current: next as ThemeName };
      }),
    init: (theme: ThemeName) => {
      document.documentElement.setAttribute("data-theme", theme);
      set({ current: theme });
    },
  };
}

export const themeStore = createThemeStore();
