import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reminderService } from "../../../services/reminder-service";
import type { ReminderCreatePayload } from "../../../types/reminder";

export function useRemindersList(status?: string) {
  return useQuery({
    queryKey: ["reminders", "list", status ?? "all"],
    queryFn: () => reminderService.listReminders(status || undefined),
    retry: false,
  });
}

export function useCreateReminderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReminderCreatePayload) => reminderService.createReminder(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}

export function useCancelReminderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reminderId: string) => reminderService.cancelReminder(reminderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}

export function useDismissReminderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reminderId: string) => reminderService.dismissReminder(reminderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}

export function useDispatchRemindersMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reminderService.dispatchDue,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}

export function useDeleteReminderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reminderId: string) => reminderService.deleteReminder(reminderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });
}
