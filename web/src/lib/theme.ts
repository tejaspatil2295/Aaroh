export type Theme = "light" | "dark" | "system";
const KEY = "aaroh.theme";

export const getTheme = (): Theme => {
  try {
    return (localStorage.getItem(KEY) as Theme) || "system";
  } catch {
    return "system";
  }
};

export function applyTheme(t: Theme = getTheme()) {
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* ignore */
  }
  const dark = t === "dark" || (t === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0b0b0f" : "#f7f7f8");
}

window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => getTheme() === "system" && applyTheme("system"));
