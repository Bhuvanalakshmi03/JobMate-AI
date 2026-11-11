import { useState } from "react";

import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type { JobSearchParams } from "../../../types/job";
import { JobCard } from "../components/JobCard";
import { JobFilters } from "../components/JobFilters";
import {
  useCalculateJobMatchMutation,
  useJobSearch,
  useRecommendedJobs,
  useSavedJobs,
  useToggleSaveJobMutation,
} from "../hooks/useJobs";

type JobsTab = "discover" | "recommended" | "saved";

export function JobsPage() {
  const [activeTab, setActiveTab] = useState<JobsTab>("discover");
  const [searchParams, setSearchParams] = useState<JobSearchParams>({ limit: 10 });
  const [matchingJobId, setMatchingJobId] = useState<string | null>(null);

  const searchQuery = useJobSearch(searchParams, activeTab === "discover");
  const recommendedQuery = useRecommendedJobs(activeTab === "recommended");
  const savedQuery = useSavedJobs(activeTab === "saved");

  const matchMutation = useCalculateJobMatchMutation();
  const saveMutation = useToggleSaveJobMutation();

  const handleCalculateMatch = (jobId: string) => {
    setMatchingJobId(jobId);
    void matchMutation
      .mutateAsync(jobId)
      .catch(() => {
        // Displayed via matchMutation.error
      })
      .finally(() => setMatchingJobId(null));
  };

  const handleToggleSave = (jobId: string, isSaved: boolean) => {
    void saveMutation.mutateAsync({ jobId, isSaved }).catch(() => {
      // Displayed via saveMutation.error
    });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Job Discovery & Matching
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Live web-search job discovery powered by OpenAI with explainable weighted and semantic
            profile matching.
          </p>
        </div>

        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1">
          {(
            [
              ["discover", "Discover"],
              ["recommended", "Recommended"],
              ["saved", "Saved"],
            ] as const
          ).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                activeTab === tab
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {activeTab === "discover" && (
        <div className="space-y-4">
          <JobFilters
            initialParams={searchParams}
            isSearching={searchQuery.isFetching}
            onSearch={(nextParams) => setSearchParams(nextParams)}
          />

          {searchQuery.isPending && (
            <StateNotice
              title="Loading job listings..."
              description="Querying discovered opportunities and match scores."
              tone="info"
            />
          )}

          {searchQuery.error && (
            <StateNotice
              title="Job search failed"
              description={searchQuery.error.message}
              tone="error"
            />
          )}

          {matchMutation.error && (
            <StateNotice
              title="Match scoring failed"
              description={matchMutation.error.message}
              tone="error"
            />
          )}

          {saveMutation.error && (
            <StateNotice
              title="Could not update saved jobs"
              description={saveMutation.error.message}
              tone="error"
            />
          )}

          {searchQuery.data && (
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{searchQuery.data.total} job(s) found</span>
              <div className="flex items-center gap-2">
                <StatusBadge label={`Source: ${searchQuery.data.source}`} tone="info" />
                {searchQuery.data.cached && <StatusBadge label="Cached" tone="neutral" />}
              </div>
            </div>
          )}

          {!searchQuery.isPending && !searchQuery.error && searchQuery.data?.items.length === 0 && (
            <StateNotice
              title="No jobs found yet"
              description="Enter a target role or keywords above and click Discover Jobs to run a live OpenAI web search."
              tone="empty"
            />
          )}

          <div className="space-y-3">
            {searchQuery.data?.items.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isMatching={matchingJobId === job.id}
                isSaving={saveMutation.isPending}
                onCalculateMatch={handleCalculateMatch}
                onToggleSave={handleToggleSave}
              />
            ))}
          </div>
        </div>
      )}

      {activeTab === "recommended" && (
        <div className="space-y-4">
          {recommendedQuery.isPending && (
            <StateNotice
              title="Computing personalized job matches..."
              description="Evaluating your verified skills, projects, and preferences against discovered jobs."
              tone="info"
            />
          )}

          {recommendedQuery.error && (
            <StateNotice
              title="Unable to compute recommendations"
              description={recommendedQuery.error.message}
              tone="error"
            />
          )}

          {!recommendedQuery.isPending &&
            !recommendedQuery.error &&
            recommendedQuery.data?.items.length === 0 && (
              <StateNotice
                title="No jobs to rank yet"
                description="Run a job discovery search first so JobMate AI can score and rank opportunities for your profile."
                tone="empty"
              />
            )}

          <div className="space-y-3">
            {recommendedQuery.data?.items.map(({ job }) => (
              <JobCard
                key={job.id}
                job={job}
                isMatching={matchingJobId === job.id}
                isSaving={saveMutation.isPending}
                onCalculateMatch={handleCalculateMatch}
                onToggleSave={handleToggleSave}
              />
            ))}
          </div>
        </div>
      )}

      {activeTab === "saved" && (
        <div className="space-y-4">
          {savedQuery.isPending && (
            <StateNotice
              title="Loading saved jobs..."
              description="Fetching your shortlisted opportunities."
              tone="info"
            />
          )}

          {savedQuery.error && (
            <StateNotice
              title="Unable to load saved jobs"
              description={savedQuery.error.message}
              tone="error"
            />
          )}

          {!savedQuery.isPending && !savedQuery.error && savedQuery.data?.items.length === 0 && (
            <StateNotice
              title="No saved jobs"
              description="Bookmark interesting jobs from Discover or Recommended to track them here."
              tone="empty"
            />
          )}

          <div className="space-y-3">
            {savedQuery.data?.items.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                isMatching={matchingJobId === job.id}
                isSaving={saveMutation.isPending}
                onCalculateMatch={handleCalculateMatch}
                onToggleSave={handleToggleSave}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
