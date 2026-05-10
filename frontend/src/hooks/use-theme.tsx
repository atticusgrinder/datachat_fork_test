/**
 * useTheme / ThemeProvider - Theme management with custom color themes
 *
 * ThemeProvider wraps the app and manages theme state.
 * useTheme hook provides current theme and setTheme function.
 * Persists preference to localStorage and applies classes to document root.
 */

import { createContext, useContext, useEffect, useState, useMemo, useCallback } from "react";

export type Theme =
  | "dark"
  | "light"
  | "system"
  | "midnight-ocean"
  | "emerald-dusk"
  | "sunset-noir"
  | "rose-garden"
  | "arctic-frost"
  | "sandstone";

export type ThemeConfig = {
  id: Theme;
  label: string;
  isDark: boolean;
  swatch: [string, string]; // [bg color, accent color] for picker preview
};

export const THEME_CONFIGS: ThemeConfig[] = [
  { id: "light", label: "Light", isDark: false, swatch: ["#ffffff", "#333333"] },
  { id: "dark", label: "Dark", isDark: true, swatch: ["#141414", "#3d3d3d"] },
  { id: "midnight-ocean", label: "Midnight Ocean", isDark: true, swatch: ["#0f1729", "#2db8b0"] },
  { id: "emerald-dusk", label: "Emerald Dusk", isDark: true, swatch: ["#0f1f14", "#33a362"] },
  { id: "sunset-noir", label: "Sunset Noir", isDark: true, swatch: ["#1a1510", "#d4922a"] },
  { id: "rose-garden", label: "Rose Garden", isDark: false, swatch: ["#f7eef1", "#c9516c"] },
  { id: "arctic-frost", label: "Arctic Frost", isDark: false, swatch: ["#eff3f8", "#2d5fd4"] },
  { id: "sandstone", label: "Sandstone", isDark: false, swatch: ["#f5efe6", "#c05a2c"] },
];

const ALL_THEME_CLASSES = [
  "light",
  "dark",
  "theme-midnight-ocean",
  "theme-emerald-dusk",
  "theme-sunset-noir",
  "theme-rose-garden",
  "theme-arctic-frost",
  "theme-sandstone",
];

export function isDarkTheme(theme: Theme): boolean {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  const config = THEME_CONFIGS.find((t) => t.id === theme);
  return config?.isDark ?? false;
}

type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

type ThemeProviderState = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
};

const initialState: ThemeProviderState = {
  theme: "system",
  setTheme: () => null,
};

const ThemeProviderContext = createContext<ThemeProviderState>(initialState);

export function ThemeProvider({
  children,
  defaultTheme = "system",
  storageKey = "vite-ui-theme",
  ...props
}: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem(storageKey) as Theme) || defaultTheme
  );

  useEffect(() => {
    const root = window.document.documentElement;

    root.classList.remove(...ALL_THEME_CLASSES);

    if (theme === "system") {
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
        .matches
        ? "dark"
        : "light";
      root.classList.add(systemTheme);
      return;
    }

    if (theme === "dark" || theme === "light") {
      root.classList.add(theme);
      return;
    }

    // Custom theme: apply theme class, plus "dark" if it's a dark-based theme
    const config = THEME_CONFIGS.find((t) => t.id === theme);
    if (config?.isDark) {
      root.classList.add("dark", `theme-${theme}`);
    } else {
      root.classList.add(`theme-${theme}`);
    }
  }, [theme]);

  const handleSetTheme = useCallback((newTheme: Theme) => {
    localStorage.setItem(storageKey, newTheme);
    setTheme(newTheme);
  }, [storageKey]);

  const value = useMemo(() => ({
    theme,
    setTheme: handleSetTheme,
  }), [theme, handleSetTheme]);

  return (
    <ThemeProviderContext.Provider {...props} value={value}>
      {children}
    </ThemeProviderContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeProviderContext);

  if (context === undefined)
    throw new Error("useTheme must be used within a ThemeProvider");

  return context;
};
