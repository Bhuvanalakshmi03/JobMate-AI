export type WorkMode = "remote" | "hybrid" | "onsite";
export type ExperienceLevel =
  | "student"
  | "intern"
  | "entry_level"
  | "junior"
  | "mid_level"
  | "senior";
export type SkillCategory = "technical" | "soft" | "tool" | "language" | "framework";
export type SkillProficiency = "beginner" | "intermediate" | "advanced" | "expert";

export interface CareerProfile {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  timezone: string;
  headline?: string | null;
  summary?: string | null;
  phone?: string | null;
  location?: string | null;
  university?: string | null;
  degree?: string | null;
  graduation_year?: number | null;
  experience_level?: ExperienceLevel | null;
  years_of_experience?: number | null;
  target_roles: string[];
  preferred_locations: string[];
  work_mode_preferences: WorkMode[];
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  ai_consent_given: boolean;
  notification_consent: boolean;
  profile_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfilePayload {
  full_name?: string | null;
  timezone?: string | null;
  headline?: string | null;
  summary?: string | null;
  phone?: string | null;
  location?: string | null;
  university?: string | null;
  degree?: string | null;
  graduation_year?: number | null;
  experience_level?: ExperienceLevel | null;
  years_of_experience?: number | null;
  target_roles: string[];
  preferred_locations: string[];
  work_mode_preferences: WorkMode[];
  linkedin_url?: string | null;
  github_url?: string | null;
  portfolio_url?: string | null;
  ai_consent_given: boolean;
  notification_consent: boolean;
}

export interface SkillInput {
  name: string;
  category: SkillCategory;
  proficiency: SkillProficiency;
  years_experience?: number | null;
  is_verified: boolean;
}

export interface UserSkill extends SkillInput {
  id: string;
  normalized_name: string;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface SkillsListResponse {
  skills: UserSkill[];
  total: number;
}

