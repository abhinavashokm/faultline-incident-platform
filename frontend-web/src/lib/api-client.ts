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
}

export async function delay(ms: number = 300): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// In-memory access token storage
let memoryAccessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  memoryAccessToken = token;
}

export function getAccessToken(): string | null {
  return memoryAccessToken;
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

export const apiClient = {
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = new URL(buildUrl(path));
    if (options?.params) {
      Object.entries(options.params).forEach(([key, val]) => {
        if (val !== undefined) url.searchParams.append(key, String(val));
      });
    }

    const authHeaders: Record<string, string> = {};
    if (memoryAccessToken) {
      authHeaders["Authorization"] = `Bearer ${memoryAccessToken}`;
    }

    const response = await fetch(url.toString(), {
      credentials: "include",
      ...options,
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || response.statusText;
      throw new ApiError(response.status, message, errorData);
    }

    return response.json();
  },

  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const authHeaders: Record<string, string> = {};
    if (memoryAccessToken) {
      authHeaders["Authorization"] = `Bearer ${memoryAccessToken}`;
    }

    const response = await fetch(buildUrl(path), {
      credentials: "include",
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
        ...options?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || errorData.message || response.statusText;
      throw new ApiError(response.status, message, errorData);
    }

    return response.json();
  },
};

