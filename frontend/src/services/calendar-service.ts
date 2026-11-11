import { apiRequest } from "./api-client";
import type {
  CalendarConnectResponse,
  CalendarEventCreatePayload,
  CalendarEventItem,
  CalendarEventListResponse,
  CalendarStatusResponse,
} from "../types/calendar";

export const calendarService = {
  getStatus: (): Promise<CalendarStatusResponse> =>
    apiRequest<CalendarStatusResponse>("/calendar/status", {
      timeoutMs: 30000,
    }),

  getConnectUrl: (redirectTo = "/copilot"): Promise<CalendarConnectResponse> =>
    apiRequest<CalendarConnectResponse>(
      `/calendar/connect?mode=json&redirect_to=${encodeURIComponent(redirectTo)}`,
      { timeoutMs: 30000 }
    ),

  listEvents: (daysAhead = 7, maxResults = 50): Promise<CalendarEventListResponse> =>
    apiRequest<CalendarEventListResponse>(
      `/calendar/events?days_ahead=${daysAhead}&max_results=${maxResults}`,
      { timeoutMs: 30000 }
    ),

  createEvent: (payload: CalendarEventCreatePayload): Promise<CalendarEventItem> =>
    apiRequest<CalendarEventItem>("/calendar/events", {
      method: "POST",
      timeoutMs: 30000,
      body: JSON.stringify(payload),
    }),

  disconnect: (): Promise<void> =>
    apiRequest<void>("/calendar/disconnect", {
      method: "DELETE",
      timeoutMs: 30000,
    }),
};
