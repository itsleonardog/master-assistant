import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Merge conditional class names and resolve conflicting Tailwind utilities.
 *
 * @param inputs Class values accepted by `clsx`.
 * @returns A single, conflict-free class string.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
