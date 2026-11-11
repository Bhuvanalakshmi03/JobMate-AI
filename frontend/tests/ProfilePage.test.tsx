import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "../src/features/authentication/hooks/useAuth";
import { ProfilePage } from "../src/features/profile/pages/ProfilePage";
import { ApiClientError } from "../src/services/api-client";
import { authService } from "../src/services/auth-service";
import { profileService } from "../src/services/profile-service";

function renderProfilePage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AuthProvider>
          <ProfilePage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("ProfilePage", () => {
  it("shows empty state when no profile exists and creates profile + saves skills", async () => {
    vi.spyOn(authService, "getMe").mockResolvedValue({
      id: "u-1",
      email: "alex@university.edu",
      full_name: "Alex Student",
      oauth_provider: "google",
      timezone: "UTC",
      created_at: "2026-11-11T12:00:00Z",
      is_demo_auth: false,
    });
    vi.spyOn(profileService, "getProfile").mockRejectedValue(
      new ApiClientError({ status: 404, code: "NOT_FOUND", message: "Career profile not found." })
    );
    vi.spyOn(profileService, "getSkills").mockResolvedValue({ skills: [], total: 0 });

    const createSpy = vi.spyOn(profileService, "createProfile").mockResolvedValue({
      id: "p-1",
      user_id: "u-1",
      full_name: "Alex Student",
      email: "alex@university.edu",
      timezone: "Asia/Kolkata",
      headline: "Backend Engineer Intern",
      target_roles: ["Backend Engineer"],
      preferred_locations: ["Remote"],
      work_mode_preferences: ["remote"],
      ai_consent_given: true,
      notification_consent: false,
      profile_verified: false,
      created_at: "2026-11-11T12:00:00Z",
      updated_at: "2026-11-11T12:00:00Z",
    });

    const skillsSpy = vi.spyOn(profileService, "replaceSkills").mockResolvedValue({
      skills: [
        {
          id: "s-1",
          name: "Python",
          normalized_name: "python",
          category: "language",
          proficiency: "advanced",
          is_verified: true,
          source: "manual",
          created_at: "2026-11-11T12:00:00Z",
          updated_at: "2026-11-11T12:00:00Z",
        },
      ],
      total: 1,
    });

    renderProfilePage();

    await waitFor(() => {
      expect(screen.getByText("Create your career profile")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Headline"), {
      target: { value: "Backend Engineer Intern" },
    });
    fireEvent.change(screen.getByLabelText("IANA Timezone"), {
      target: { value: "Asia/Kolkata" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create Profile" }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(screen.getByLabelText("Skill name"), { target: { value: "Python" } });
    fireEvent.click(screen.getByRole("button", { name: "Add skill" }));
    fireEvent.click(screen.getByRole("button", { name: "Save Skills" }));

    await waitFor(() => {
      expect(skillsSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Skills updated")).toBeInTheDocument();
    });
  });
});

