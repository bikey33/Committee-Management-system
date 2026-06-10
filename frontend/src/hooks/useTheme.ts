import { useState } from "react";
import { applyTheme, getStoredTheme, type Theme } from "@/lib/theme";

/**
 * Theme state hook. The `.dark` class is applied to <html> on app load
 * (see main.tsx); this hook reads the current value and flips it.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() =>
    document.documentElement.classList.contains("dark") ? "dark" : getStoredTheme()
  );

  const setTheme = (next: Theme) => {
    applyTheme(next);
    setThemeState(next);
  };

  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");

  return { theme, isDark: theme === "dark", toggle, setTheme };
}
