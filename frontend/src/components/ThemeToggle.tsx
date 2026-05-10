/**
 * ThemeToggle - Theme picker popover
 *
 * Full popover picker showing all available themes with color swatch previews.
 * Pass compact={true} on public pages to show a simple light/dark toggle instead.
 */

import { Palette, Check, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useTheme, THEME_CONFIGS } from "@/hooks/use-theme";
import type { Theme } from "@/hooks/use-theme";

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { theme, setTheme } = useTheme();

  if (compact) {
    const isDark = theme === "dark" || theme === "system";
    const toggle = () => setTheme(isDark ? "light" : "dark");

    return (
      <Button
        variant="ghost"
        size="icon"
        onClick={toggle}
        className="rounded-full"
        aria-label="Toggle theme"
      >
        <Moon className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Sun className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="rounded-full"
          aria-label="Choose theme"
        >
          <Palette className="h-5 w-5" />
          <span className="sr-only">Choose theme</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-56 p-2">
        <div className="grid gap-1">
          {THEME_CONFIGS.map((config) => (
            <button
              key={config.id}
              onClick={() => setTheme(config.id as Theme)}
              className="flex items-center gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground transition-colors w-full text-left"
            >
              <div className="flex gap-0.5">
                <div
                  className="h-5 w-5 rounded-l-md border border-border"
                  style={{ backgroundColor: config.swatch[0] }}
                />
                <div
                  className="h-5 w-5 rounded-r-md border border-border"
                  style={{ backgroundColor: config.swatch[1] }}
                />
              </div>
              <span className="flex-1">{config.label}</span>
              {theme === config.id && (
                <Check className="h-4 w-4 text-primary" />
              )}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
