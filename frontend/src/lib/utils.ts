import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Converts a snake_case string to camelCase.
 * e.g. "affected_users_count" -> "affectedUsersCount"
 */
export function snakeToCamelCase(str: string): string {
  return str.replace(/([-_][a-z0-9])/gi, ($1) =>
    $1.toUpperCase().replace("-", "").replace("_", "")
  );
}

/**
 * Converts a camelCase string to snake_case.
 * e.g. "affectedUsersCount" -> "affected_users_count"
 */
export function camelToSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Recursively transforms object keys to camelCase.
 */
export function keysToCamel<T>(obj: unknown): T {
  if (Array.isArray(obj)) {
    return obj.map((v) => keysToCamel(v)) as unknown as T;
  }
  if (obj !== null && typeof obj === "object" && !(obj instanceof Date) && !(obj instanceof RegExp)) {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        snakeToCamelCase(key),
        keysToCamel(value),
      ])
    ) as unknown as T;
  }
  return obj as T;
}

/**
 * Recursively transforms object keys to snake_case.
 */
export function keysToSnake<T>(obj: unknown): T {
  if (Array.isArray(obj)) {
    return obj.map((v) => keysToSnake(v)) as unknown as T;
  }
  if (obj !== null && typeof obj === "object" && !(obj instanceof Date) && !(obj instanceof RegExp)) {
    return Object.fromEntries(
      Object.entries(obj as Record<string, unknown>).map(([key, value]) => [
        camelToSnakeCase(key),
        keysToSnake(value),
      ])
    ) as unknown as T;
  }
  return obj as T;
}


