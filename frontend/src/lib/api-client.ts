import { keysToCamel, keysToSnake, camelToSnakeCase } from "./utils";

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  /**
   * Internal flag: set to true on the retry after a token refresh so we
   * never enter an infinite refresh loop.
   */
  _retried?: boolean;
  /**
   * Controls case conversion. Defaults to true (converts snake_case response to camelCase,
   * and camelCase body to snake_case).
   */
  transformCase?: boolean;
}

export async function delay(ms: number = 300): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// In-memory access token
// ---------------------------------------------------------------------------

let memoryAccessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  memoryAccessToken = token;
}

export function clearAccessToken(): void {
  memoryAccessToken = null;
}

export function getAccessToken(): string | null {
  return memoryAccessToken;
}

// ---------------------------------------------------------------------------
// Silent token refresh
// ---------------------------------------------------------------------------

/**
 * A single in-flight refresh promise shared across all concurrent callers so
 * we never send two refresh requests at the same time.
 */
let _refreshPromise: Promise<string> | null = null;

/**
 * Optional callback set by the AuthProvider so the client can trigger a
 * redirect to /login when a refresh fails.
 */
let _onRefreshFailure: (() => void) | null = null;

export function setRefreshFailureHandler(handler: () => void): void {
  _onRefreshFailure = handler;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const cleanBase = API_BASE_URL.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

function extractErrorMessage(errorData: any, fallback: string): string {
  if (!errorData) return fallback;
  const detail = errorData.detail ?? errorData.message;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    // FastAPI/Pydantic validation error list: [{ type, loc, msg, input }, ...]
    return detail
      .map((item) => (typeof item === "string" ? item : item?.msg || JSON.stringify(item)))
      .filter(Boolean)
      .join(", ") || fallback;
  }
  if (typeof detail === "object" && detail !== null) {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return fallback;
}

/**
 * Calls POST /api/v1/auth/refresh using the HttpOnly refresh-token cookie.
 * Returns the new access token on success. Throws on failure.
 * Deduplicates concurrent callers — only one network request is made at a time.
 */
export async function refreshAccessToken(): Promise<string> {
  if (_refreshPromise) {
    return _refreshPromise;
  }

  _refreshPromise = (async () => {
    try {
      const response = await fetch(buildUrl("/api/v1/auth/refresh"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = extractErrorMessage(errorData, response.statusText);
        throw new ApiError(response.status, message, errorData);
      }

      const data = await response.json();
      const newToken: string = data.access_token;
      setAccessToken(newToken);
      return newToken;
    } catch (err) {
      clearAccessToken();
      _onRefreshFailure?.();
      throw err;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

// ---------------------------------------------------------------------------
// Shared request helpers
// ---------------------------------------------------------------------------

function buildAuthHeaders(): Record<string, string> {
  return memoryAccessToken
    ? { Authorization: `Bearer ${memoryAccessToken}` }
    : {};
}

async function handleResponse<T>(
  response: Response,
  transformCase: boolean = true
): Promise<T> {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = extractErrorMessage(errorData, response.statusText);
    throw new ApiError(response.status, message, errorData);
  }
  const data = await response.json();
  if (transformCase && data !== null && typeof data === "object") {
    return keysToCamel<T>(data);
  }
  return data as T;
}

function isAuthEndpoint(path: string): boolean {
  return (
    path.includes("/api/v1/auth/login") ||
    path.includes("/api/v1/auth/refresh") ||
    path.includes("/api/v1/auth/signup") ||
    path.includes("/api/v1/auth/verify-email") ||
    path.includes("/api/v1/auth/resend-verification")
  );
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const apiClient = {
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = new URL(buildUrl(path));
    if (options?.params) {
      Object.entries(options.params).forEach(([key, val]) => {
        if (val !== undefined) {
          const transformedKey =
            options.transformCase !== false ? camelToSnakeCase(key) : key;
          url.searchParams.append(transformedKey, String(val));
        }
      });
    }

    const response = await fetch(url.toString(), {
      credentials: "include",
      ...options,
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
        ...options?.headers,
      },
    });

    // 401 interception: attempt one silent refresh then retry (skip for auth endpoints)
    if (response.status === 401 && !options?._retried && !isAuthEndpoint(path)) {
      await refreshAccessToken();
      return apiClient.get<T>(path, { ...options, _retried: true });
    }

    return handleResponse<T>(response, options?.transformCase ?? true);
  },

  async post<T>(
    path: string,
    body?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    const transform = options?.transformCase ?? true;
    const transformedBody =
      transform && body !== undefined && body !== null && typeof body === "object"
        ? keysToSnake(body)
        : body;

    const response = await fetch(buildUrl(path), {
      credentials: "include",
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
        ...options?.headers,
      },
      body: transformedBody !== undefined ? JSON.stringify(transformedBody) : undefined,
    });

    // 401 interception: attempt one silent refresh then retry (skip for auth endpoints)
    if (response.status === 401 && !options?._retried && !isAuthEndpoint(path)) {
      await refreshAccessToken();
      return apiClient.post<T>(path, body, { ...options, _retried: true });
    }

    return handleResponse<T>(response, transform);
  },

  async patch<T>(
    path: string,
    body?: unknown,
    options?: RequestOptions
  ): Promise<T> {
    const transform = options?.transformCase ?? true;
    const transformedBody =
      transform && body !== undefined && body !== null && typeof body === "object"
        ? keysToSnake(body)
        : body;

    const response = await fetch(buildUrl(path), {
      credentials: "include",
      ...options,
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...buildAuthHeaders(),
        ...options?.headers,
      },
      body: transformedBody !== undefined ? JSON.stringify(transformedBody) : undefined,
    });

    // 401 interception: attempt one silent refresh then retry (skip for auth endpoints)
    if (response.status === 401 && !options?._retried && !isAuthEndpoint(path)) {
      await refreshAccessToken();
      return apiClient.patch<T>(path, body, { ...options, _retried: true });
    }

    return handleResponse<T>(response, transform);
  },
};

