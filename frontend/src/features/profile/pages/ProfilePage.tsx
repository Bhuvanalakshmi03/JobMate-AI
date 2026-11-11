import { useEffect, useState, type FormEvent } from "react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { ExperienceLevel, ProfilePayload, WorkMode } from "../../../types/profile";
import { useAuth } from "../../authentication/hooks/useAuth";
import { SkillsManager } from "../components/SkillsManager";
import {
  useProfileData,
  useReplaceSkillsMutation,
  useSaveProfileMutation,
  useSkillsData,
} from "../hooks/useProfile";

const WORK_MODES: WorkMode[] = ["remote", "hybrid", "onsite"];
const EXPERIENCE_LEVELS: { value: ExperienceLevel; label: string }[] = [
  { value: "student", label: "Student" },
  { value: "intern", label: "Intern" },
  { value: "entry_level", label: "Entry Level" },
  { value: "junior", label: "Junior" },
  { value: "mid_level", label: "Mid Level" },
  { value: "senior", label: "Senior" },
];

function parseCommaTags(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ProfilePage() {
  const { user } = useAuth();
  const profileQuery = useProfileData();
  const skillsQuery = useSkillsData();

  const hasExistingProfile = Boolean(profileQuery.data);
  const saveProfileMutation = useSaveProfileMutation(hasExistingProfile);
  const replaceSkillsMutation = useReplaceSkillsMutation();

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [timezone, setTimezone] = useState(user?.timezone ?? "UTC");
  const [headline, setHeadline] = useState("");
  const [summary, setSummary] = useState("");
  const [location, setLocation] = useState("");
  const [university, setUniversity] = useState("");
  const [degree, setDegree] = useState("");
  const [graduationYear, setGraduationYear] = useState("");
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>("student");
  const [targetRolesInput, setTargetRolesInput] = useState("");
  const [preferredLocationsInput, setPreferredLocationsInput] = useState("");
  const [workModes, setWorkModes] = useState<WorkMode[]>([]);
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [aiConsentGiven, setAiConsentGiven] = useState(false);
  const [notificationConsent, setNotificationConsent] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    const profile = profileQuery.data;
    if (profile) {
      setFullName(profile.full_name);
      setTimezone(profile.timezone);
      setHeadline(profile.headline ?? "");
      setSummary(profile.summary ?? "");
      setLocation(profile.location ?? "");
      setUniversity(profile.university ?? "");
      setDegree(profile.degree ?? "");
      setGraduationYear(profile.graduation_year ? String(profile.graduation_year) : "");
      setExperienceLevel(profile.experience_level ?? "student");
      setTargetRolesInput(profile.target_roles.join(", "));
      setPreferredLocationsInput(profile.preferred_locations.join(", "));
      setWorkModes(profile.work_mode_preferences);
      setLinkedinUrl(profile.linkedin_url ?? "");
      setGithubUrl(profile.github_url ?? "");
      setPortfolioUrl(profile.portfolio_url ?? "");
      setAiConsentGiven(profile.ai_consent_given);
      setNotificationConsent(profile.notification_consent);
    } else if (user) {
      setFullName(user.full_name);
      setTimezone(user.timezone || "UTC");
    }
  }, [profileQuery.data, user]);

  const toggleWorkMode = (mode: WorkMode) => {
    setWorkModes((prev) =>
      prev.includes(mode) ? prev.filter((item) => item !== mode) : [...prev, mode]
    );
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!fullName.trim()) {
      setValidationError("Full name is required.");
      return;
    }

    const parsedYear = graduationYear.trim() ? Number(graduationYear.trim()) : null;
    if (parsedYear !== null && (Number.isNaN(parsedYear) || parsedYear < 1970 || parsedYear > 2050)) {
      setValidationError("Graduation year must be between 1970 and 2050.");
      return;
    }

    const payload: ProfilePayload = {
      full_name: fullName.trim(),
      timezone: timezone.trim() || "UTC",
      headline: headline.trim() || null,
      summary: summary.trim() || null,
      location: location.trim() || null,
      university: university.trim() || null,
      degree: degree.trim() || null,
      graduation_year: parsedYear,
      experience_level: experienceLevel,
      target_roles: parseCommaTags(targetRolesInput),
      preferred_locations: parseCommaTags(preferredLocationsInput),
      work_mode_preferences: workModes,
      linkedin_url: linkedinUrl.trim() || null,
      github_url: githubUrl.trim() || null,
      portfolio_url: portfolioUrl.trim() || null,
      ai_consent_given: aiConsentGiven,
      notification_consent: notificationConsent,
    };

    await saveProfileMutation.mutateAsync(payload);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Career Profile & Preferences
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Your verified career foundation used for job matching, tailored documents, and mock
            interviews.
          </p>
        </div>
        {profileQuery.data && (
          <StatusBadge
            label={profileQuery.data.profile_verified ? "Verified Profile" : "Profile Active"}
            tone={profileQuery.data.profile_verified ? "success" : "info"}
          />
        )}
      </header>

      {profileQuery.isPending && (
        <StateNotice
          title="Loading career profile..."
          description="Retrieving your saved profile and placement preferences."
          tone="info"
        />
      )}

      {profileQuery.error && (
        <StateNotice
          title="Unable to load career profile"
          description={profileQuery.error.message}
          tone="error"
        />
      )}

      {!profileQuery.isPending && !profileQuery.error && !profileQuery.data && (
        <StateNotice
          title="Create your career profile"
          description="You have not saved a career profile yet. Fill in your education, target roles, and consent preferences below."
          tone="empty"
        />
      )}

      {!profileQuery.isPending && !profileQuery.error && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card
            title="Identity, Education & Preferences"
            subtitle="All timestamps and reminder schedules respect your configured timezone."
            action={
              <button
                type="submit"
                disabled={saveProfileMutation.isPending}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
              >
                {saveProfileMutation.isPending
                  ? "Saving..."
                  : hasExistingProfile
                    ? "Save Profile"
                    : "Create Profile"}
              </button>
            }
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="profile-full-name" className="block text-xs font-medium text-slate-700">
                  Full name
                </label>
                <input
                  id="profile-full-name"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="profile-timezone" className="block text-xs font-medium text-slate-700">
                  IANA Timezone
                </label>
                <input
                  id="profile-timezone"
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="e.g. UTC, Asia/Kolkata, America/New_York"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="profile-headline" className="block text-xs font-medium text-slate-700">
                  Headline
                </label>
                <input
                  id="profile-headline"
                  type="text"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g. Final-year CS student building distributed backend systems"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="profile-summary" className="block text-xs font-medium text-slate-700">
                  Career summary
                </label>
                <textarea
                  id="profile-summary"
                  rows={3}
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="profile-university" className="block text-xs font-medium text-slate-700">
                  University / Institution
                </label>
                <input
                  id="profile-university"
                  type="text"
                  value={university}
                  onChange={(e) => setUniversity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="profile-degree" className="block text-xs font-medium text-slate-700">
                  Degree / Major
                </label>
                <input
                  id="profile-degree"
                  type="text"
                  value={degree}
                  onChange={(e) => setDegree(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="profile-grad-year"
                  className="block text-xs font-medium text-slate-700"
                >
                  Graduation year
                </label>
                <input
                  id="profile-grad-year"
                  type="number"
                  min={1970}
                  max={2050}
                  value={graduationYear}
                  onChange={(e) => setGraduationYear(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="profile-experience-level"
                  className="block text-xs font-medium text-slate-700"
                >
                  Experience level
                </label>
                <select
                  id="profile-experience-level"
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value as ExperienceLevel)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  {EXPERIENCE_LEVELS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label htmlFor="profile-location" className="block text-xs font-medium text-slate-700">
                  Current location
                </label>
                <input
                  id="profile-location"
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="profile-target-roles"
                  className="block text-xs font-medium text-slate-700"
                >
                  Target job roles (comma-separated)
                </label>
                <input
                  id="profile-target-roles"
                  type="text"
                  value={targetRolesInput}
                  onChange={(e) => setTargetRolesInput(e.target.value)}
                  placeholder="Backend Engineer, Software Intern"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label
                  htmlFor="profile-preferred-locations"
                  className="block text-xs font-medium text-slate-700"
                >
                  Preferred job locations (comma-separated)
                </label>
                <input
                  id="profile-preferred-locations"
                  type="text"
                  value={preferredLocationsInput}
                  onChange={(e) => setPreferredLocationsInput(e.target.value)}
                  placeholder="Bengaluru, Hyderabad, Remote"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <span className="block text-xs font-medium text-slate-700">Work mode preferences</span>
                <div className="mt-2 flex flex-wrap gap-3">
                  {WORK_MODES.map((mode) => (
                    <label
                      key={mode}
                      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5 text-sm capitalize text-slate-700"
                    >
                      <input
                        type="checkbox"
                        checked={workModes.includes(mode)}
                        onChange={() => toggleWorkMode(mode)}
                      />
                      {mode}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label htmlFor="profile-github" className="block text-xs font-medium text-slate-700">
                  GitHub URL
                </label>
                <input
                  id="profile-github"
                  type="url"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/username"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label htmlFor="profile-linkedin" className="block text-xs font-medium text-slate-700">
                  LinkedIn URL
                </label>
                <input
                  id="profile-linkedin"
                  type="url"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://linkedin.com/in/username"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="sm:col-span-2">
                <label
                  htmlFor="profile-portfolio"
                  className="block text-xs font-medium text-slate-700"
                >
                  Portfolio URL
                </label>
                <input
                  id="profile-portfolio"
                  type="url"
                  value={portfolioUrl}
                  onChange={(e) => setPortfolioUrl(e.target.value)}
                  placeholder="https://portfolio.example.com"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:col-span-2">
                <label className="flex items-start gap-2.5 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={aiConsentGiven}
                    onChange={(e) => setAiConsentGiven(e.target.checked)}
                    className="mt-1"
                  />
                  <span>
                    I consent to sending my verified career profile and resume excerpts to configured
                    AI providers for analysis, matching, and coaching.
                  </span>
                </label>
                <label className="flex items-start gap-2.5 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={notificationConsent}
                    onChange={(e) => setNotificationConsent(e.target.checked)}
                    className="mt-1"
                  />
                  <span>Allow deadline and interview reminder notifications.</span>
                </label>
              </div>
            </div>

            {validationError && (
              <div className="mt-4">
                <StateNotice title="Validation error" description={validationError} tone="error" />
              </div>
            )}

            {saveProfileMutation.error && (
              <div className="mt-4">
                <StateNotice
                  title="Failed to save career profile"
                  description={saveProfileMutation.error.message}
                  tone="error"
                />
              </div>
            )}

            {saveProfileMutation.isSuccess && !saveProfileMutation.error && (
              <div className="mt-4">
                <StateNotice
                  title="Profile saved"
                  description="Your career profile and preferences have been updated."
                  tone="info"
                />
              </div>
            )}
          </Card>
        </form>
      )}

      <SkillsManager
        skills={skillsQuery.data?.skills ?? []}
        isLoading={skillsQuery.isPending}
        loadError={skillsQuery.error}
        isSaving={replaceSkillsMutation.isPending}
        saveError={replaceSkillsMutation.error}
        saveSucceeded={replaceSkillsMutation.isSuccess}
        onSave={(skills) => replaceSkillsMutation.mutateAsync(skills)}
      />
    </div>
  );
}

