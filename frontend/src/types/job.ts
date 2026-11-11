export interface JobMatchPreview {
  overall_score: number;
  matching_skills: string[];
  missing_skills: string[];
  algorithm_version: string;
}

export interface JobSummary {
  id: string;
  source_provider: string;
  title: string;
  company: string;
  location?: string | null;
  work_mode: string;
  experience_level: string;
  employment_type: string;
  required_skills: string[];
  preferred_skills: string[];
  salary_range?: string | null;
  external_url: string;
  source_domain?: string | null;
  posted_at?: string | null;
  retrieved_at: string;
  is_active: boolean;
  is_saved: boolean;
  match_preview?: JobMatchPreview | null;
}

export interface JobDetail extends JobSummary {
  description: string;
  requirements_summary?: string | null;
  education_requirements: string[];
  min_years_experience?: number | null;
}

export interface JobSearchResponse {
  items: JobSummary[];
  total: number;
  source: string;
  cached: boolean;
}

export interface JobSearchParams {
  q?: string;
  location?: string;
  work_mode?: string;
  experience_level?: string;
  skills?: string;
  refresh?: boolean;
  limit?: number;
}

export interface JobMatch {
  id: string;
  user_id: string;
  job_id: string;
  algorithm_version: string;
  overall_score: number;
  factor_scores: Record<string, number>;
  weights_used: Record<string, number>;
  matching_skills: string[];
  missing_skills: string[];
  match_explanation: string;
  recommended_preparation: string[];
  computed_at: string;
}

export interface RecommendedJobItem {
  job: JobSummary;
  match: JobMatch;
}

export interface RecommendedJobsResponse {
  items: RecommendedJobItem[];
  total: number;
  algorithm_version: string;
}

export interface SavedJobResponse {
  job_id: string;
  is_saved: boolean;
  notes?: string | null;
  saved_at: string;
}
