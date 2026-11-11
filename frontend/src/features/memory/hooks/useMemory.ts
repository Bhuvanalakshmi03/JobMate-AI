import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { memoryService } from "../../../services/memory-service";
import type {
  CareerMemoryCreatePayload,
  CareerMemoryUpdatePayload,
} from "../../../types/memory";

export function useMemoriesList(category?: string) {
  return useQuery({
    queryKey: ["memory", "list", category ?? "all"],
    queryFn: () => memoryService.listMemories(category || undefined),
    retry: false,
  });
}

export function useUpdateMemoryConsentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { ai_consent_given: boolean; notification_consent?: boolean }) =>
      memoryService.updateConsent(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}

export function useCreateMemoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CareerMemoryCreatePayload) => memoryService.createMemory(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}

export function useUpdateMemoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: { memoryId: string; payload: CareerMemoryUpdatePayload }) =>
      memoryService.updateMemory(params.memoryId, params.payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}

export function useDeleteMemoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memoryId: string) => memoryService.deleteMemory(memoryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}

export function useClearAllMemoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: memoryService.clearAll,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["memory"] });
    },
  });
}
