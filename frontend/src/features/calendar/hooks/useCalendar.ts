import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { calendarService } from "../../../services/calendar-service";
import type { CalendarEventCreatePayload } from "../../../types/calendar";

export function useCalendarStatus() {
  return useQuery({
    queryKey: ["calendar", "status"],
    queryFn: calendarService.getStatus,
    retry: false,
  });
}

export function useCalendarEvents(enabled: boolean, daysAhead = 7, maxResults = 50) {
  return useQuery({
    queryKey: ["calendar", "events", daysAhead, maxResults],
    queryFn: () => calendarService.listEvents(daysAhead, maxResults),
    enabled,
    retry: false,
  });
}

export function useConnectCalendarMutation() {
  return useMutation({
    mutationFn: (redirectTo?: string) => calendarService.getConnectUrl(redirectTo ?? "/copilot"),
  });
}

export function useDisconnectCalendarMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: calendarService.disconnect,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}

export function useCreateCalendarEventMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CalendarEventCreatePayload) => calendarService.createEvent(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["calendar"] });
    },
  });
}
