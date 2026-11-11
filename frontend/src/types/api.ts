export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | unknown[] | null;
  request_id?: string | null;
  timestamp: string;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface DependencyStatus {
  status: "healthy" | "unavailable" | "unhealthy";
  detail?: string | null;
}

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded" | "unavailable";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  dependencies: Record<string, DependencyStatus>;
}

