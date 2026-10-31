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

export const apiClient = {
  async get<T>(path: string, options?: RequestOptions): Promise<T> {
    const url = new URL(path, typeof window !== "undefined" ? window.location.origin : "http://localhost:3000");
    if (options?.params) {
      Object.entries(options.params).forEach(([key, val]) => {
        if (val !== undefined) url.searchParams.append(key, String(val));
      });
    }

    const response = await fetch(url.toString(), {
      ...options,
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData.message || response.statusText, errorData);
    }

    return response.json();
  },

  async post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    const response = await fetch(path, {
      ...options,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(response.status, errorData.message || response.statusText, errorData);
    }

    return response.json();
  },
};

