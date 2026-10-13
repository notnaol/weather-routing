/**
 * API client for the backend.
 * All API calls go through this module.
 */

const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '/api/v1'
const API_BASE = rawBase.endsWith('/') ? rawBase.slice(0, -1) : rawBase

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown,
  ) {
    super(`API Error ${status}: ${statusText}`)
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = `${API_BASE}${normalizedPath}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!res.ok) {
    const body = await res.json().catch(() => undefined)
    throw new ApiError(res.status, res.statusText, body)
  }

  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
