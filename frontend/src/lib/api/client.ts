const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

type RequestOptions = {
  method?: string;
  body?: unknown | FormData;
  headers?: Record<string, string>;
};

export async function apiClient<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const token = typeof window !== "undefined"
    ? localStorage.getItem("access_token")
    : null;

  const isFormData = body instanceof FormData;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    ...(body ? { body: isFormData ? body : JSON.stringify(body) } : {}),
  });

  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new ApiError(res.status, error);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, public data: unknown) {
    super(`API error ${status}`);
  }
}
