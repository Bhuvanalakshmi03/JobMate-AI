import { apiRequest } from "./api-client";
import type {
  CareerProfile,
  ProfilePayload,
  SkillInput,
  SkillsListResponse,
} from "../types/profile";

export const profileService = {
  getProfile: (): Promise<CareerProfile> => apiRequest<CareerProfile>("/profile"),

  createProfile: (payload: ProfilePayload): Promise<CareerProfile> =>
    apiRequest<CareerProfile>("/profile", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateProfile: (payload: ProfilePayload): Promise<CareerProfile> =>
    apiRequest<CareerProfile>("/profile", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  getSkills: (): Promise<SkillsListResponse> => apiRequest<SkillsListResponse>("/profile/skills"),

  replaceSkills: (skills: SkillInput[]): Promise<SkillsListResponse> =>
    apiRequest<SkillsListResponse>("/profile/skills", {
      method: "PUT",
      body: JSON.stringify({ skills }),
    }),
};

