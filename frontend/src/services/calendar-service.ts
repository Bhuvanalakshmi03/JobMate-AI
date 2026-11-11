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
    apiRequest<CalendarStatusResponse>("/calendar/status"),

  getConnectUrl: (redirectTo = "/copilot"): Promise<CalendarConnectResponse> =>
    apiRequest<CalendarConnectResponse>(
      `/calendar/connect?mode=json&redirect_to=${encodeURIComponent(redirectTo)}`
    ),

  listEvents: (daysAhead = 14, maxResults = 15): Promise<CalendarEventListResponse> =>
    apiRequest<CalendarEventListResponse>(
      `/calendar/events?days_ahead=${daysAhead}&max_results=${maxResults}`
    ),

  createEvent: (payload: CalendarEventCreatePayload): Promise<CalendarEventItem> =>
    apiRequest<CalendarEventItem>("/calendar/events", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  disconnect: (): Promise<void> =>
    apiRequest<void>("/calendar/disconnect", {
      method: "DELETE",
    }),
};
