import type { ApiErrorResponse } from "../types/api";

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string | null;
  readonly details?: Record<string, unknown> | unknown[] | null;

  constructor(params: {
    status: number;
    code: string;
    message: string;
    requestId?: string | null;
    details?: Record<string, unknown> | unknown[] | null;
  }) {
    super(params.message);
    this.name = "ApiClientError";
    this.status = params.status;
    this.code = params.code;
    this.requestId = params.requestId;
    this.details = params.details;
  }
}

export interface RequestOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
  timeoutMs?: number;
}

const DEFAULT_BASE_URL = "/api/v1";
const DEFAULT_TIMEOUT_MS = 30000;

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return (configured && configured.trim().replace(/\/$/, "")) || DEFAULT_BASE_URL;
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

function isAbortLikeError(err: unknown): boolean {
  if (err instanceof DOMException && err.name === "AbortError") return true;
  if (err instanceof Error && err.name === "AbortError") return true;
  return false;
}

async function performFetch<T>(url: string, options: RequestOptions): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers = {}, signal, ...rest } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  try {
    const response = await fetch(url, {
      ...rest,
      credentials: "include",
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        ...(rest.body && !(rest.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...headers,
      },
    });

    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler();
    }

    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    const parsed = isJson ? ((await response.json()) as unknown) : null;

    if (!response.ok) {
      const apiError = (parsed as ApiErrorResponse | null)?.error;
      if (!isJson && response.status >= 502 && response.status <= 504) {
        throw new ApiClientError({
          status: response.status,
          code: "GATEWAY_UNAVAILABLE",
          message:
            "The JobMate AI API server is temporarily unavailable or restarting. Please retry.",
        });
      }
      throw new ApiClientError({
        status: response.status,
        code: apiError?.code ?? `HTTP_${response.status}`,
        message: apiError?.message ?? `Request failed with status ${response.status}`,
        requestId: apiError?.request_id ?? response.headers.get("X-Request-ID"),
        details: apiError?.details ?? null,
      });
    }

    return parsed as T;
  } catch (err) {
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (isAbortLikeError(err)) {
      throw new ApiClientError({
        status: 408,
        code: "REQUEST_TIMEOUT",
        message: "The server took too long to respond. Please try again.",
      });
    }
    throw new ApiClientError({
      status: 0,
      code: "NETWORK_ERROR",
      message:
        "Unable to reach the JobMate AI API server. Verify the backend is running and retry.",
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${getApiBaseUrl()}${normalizedPath}`;
  const method = (options.method ?? "GET").toUpperCase();
  const canRetry = method === "GET";

  try {
    return await performFetch<T>(url, options);
  } catch (err) {
    const isTransient =
      err instanceof ApiClientError &&
      (err.code === "NETWORK_ERROR" || err.code === "GATEWAY_UNAVAILABLE");
    if (canRetry && isTransient) {
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      return await performFetch<T>(url, options);
    }
    throw err;
  }
}
