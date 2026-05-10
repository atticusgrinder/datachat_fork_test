/**
 * cn - Tailwind class name utility
 *
 * Merges multiple class names and resolves Tailwind conflicts.
 * Standard shadcn/ui utility used throughout the app.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
