import { apiRequest } from "./api-client";
import type { HealthResponse, ReadinessResponse } from "../types/api";

export const healthService = {
  getLiveness: (): Promise<HealthResponse> => apiRequest<HealthResponse>("/health"),
  getReadiness: (): Promise<ReadinessResponse> => apiRequest<ReadinessResponse>("/health/ready"),
};

