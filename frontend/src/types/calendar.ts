export interface CalendarStatusResponse {
  connected: boolean;
  google_email: string | null;
  scopes: string[];
  token_expires_at: string | null;
}

export interface CalendarConnectResponse {
  authorization_url: string;
  state: string;
}

export interface CalendarEventItem {
  event_id: string;
  summary: string;
  start_iso: string;
  end_iso: string;
  location: string | null;
  description: string | null;
  html_link: string | null;
  status: string;
}

export interface CalendarEventListResponse {
  connected: boolean;
  items: CalendarEventItem[];
}

export interface CalendarEventCreatePayload {
  summary: string;
  start_iso: string;
  end_iso: string;
  description?: string | null;
  location?: string | null;
  timezone?: string;
}
