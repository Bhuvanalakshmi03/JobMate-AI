import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClientError } from "../../../services/api-client";
import { profileService } from "../../../services/profile-service";
import type { ProfilePayload, SkillInput } from "../../../types/profile";

export function useProfileData() {
  return useQuery({
    queryKey: ["profile", "details"],
    queryFn: async () => {
      try {
        return await profileService.getProfile();
      } catch (err) {
        if (err instanceof ApiClientError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    retry: false,
  });
}

export function useSkillsData() {
  return useQuery({
    queryKey: ["profile", "skills"],
    queryFn: profileService.getSkills,
    retry: false,
  });
}

export function useSaveProfileMutation(hasExistingProfile: boolean) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfilePayload) =>
      hasExistingProfile
        ? profileService.updateProfile(payload)
        : profileService.createProfile(payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "details"], updated);
      void queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function useReplaceSkillsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (skills: SkillInput[]) => profileService.replaceSkills(skills),
    onSuccess: (updated) => {
      queryClient.setQueryData(["profile", "skills"], updated);
    },
  });
}

