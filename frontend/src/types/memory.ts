export type MemoryCategory = "preference" | "goal" | "strength" | "weakness" | "note";

export interface MemoryConsent {
  ai_consent_given: boolean;
  notification_consent: boolean;
}

export interface CareerMemoryItem {
  id: string;
  user_id: string;
  category: string;
  title: string;
  content: string;
  source: string;
  memory_key: string | null;
  is_approved: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CareerMemoryListResponse {
  consent: MemoryConsent;
  items: CareerMemoryItem[];
  total: number;
}

export interface CareerMemoryCreatePayload {
  category: MemoryCategory;
  title: string;
  content: string;
  memory_key?: string | null;
  is_approved?: boolean;
}

export interface CareerMemoryUpdatePayload {
  category?: MemoryCategory;
  title?: string;
  content?: string;
  is_approved?: boolean;
  is_active?: boolean;
}
