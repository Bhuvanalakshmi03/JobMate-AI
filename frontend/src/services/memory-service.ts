import { apiRequest } from "./api-client";
import type {
  CareerMemoryCreatePayload,
  CareerMemoryItem,
  CareerMemoryListResponse,
  CareerMemoryUpdatePayload,
  MemoryConsent,
} from "../types/memory";

export const memoryService = {
  getConsent: (): Promise<MemoryConsent> => apiRequest<MemoryConsent>("/memory/consent"),

  updateConsent: (payload: {
    ai_consent_given: boolean;
    notification_consent?: boolean;
  }): Promise<MemoryConsent> =>
    apiRequest<MemoryConsent>("/memory/consent", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  listMemories: (category?: string): Promise<CareerMemoryListResponse> =>
    apiRequest<CareerMemoryListResponse>(
      category ? `/memory?category=${encodeURIComponent(category)}` : "/memory"
    ),

  createMemory: (payload: CareerMemoryCreatePayload): Promise<CareerMemoryItem> =>
    apiRequest<CareerMemoryItem>("/memory", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateMemory: (
    memoryId: string,
    payload: CareerMemoryUpdatePayload
  ): Promise<CareerMemoryItem> =>
    apiRequest<CareerMemoryItem>(`/memory/${memoryId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteMemory: (memoryId: string): Promise<void> =>
    apiRequest<void>(`/memory/${memoryId}`, {
      method: "DELETE",
    }),

  clearAll: (): Promise<void> =>
    apiRequest<void>("/memory", {
      method: "DELETE",
    }),
};
