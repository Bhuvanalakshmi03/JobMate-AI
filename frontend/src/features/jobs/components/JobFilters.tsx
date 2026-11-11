import { Search } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { JobSearchParams } from "../../../types/job";

interface JobFiltersProps {
  initialParams: JobSearchParams;
  isSearching: boolean;
  onSearch: (params: JobSearchParams) => void;
}

export function JobFilters({ initialParams, isSearching, onSearch }: JobFiltersProps) {
  const [query, setQuery] = useState(initialParams.q ?? "");
  const [location, setLocation] = useState(initialParams.location ?? "");
  const [workMode, setWorkMode] = useState(initialParams.work_mode ?? "");
  const [experienceLevel, setExperienceLevel] = useState(initialParams.experience_level ?? "");
  const [skills, setSkills] = useState(initialParams.skills ?? "");
  const [refresh, setRefresh] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearch({
      q: query.trim() || undefined,
      location: location.trim() || undefined,
      work_mode: workMode || undefined,
      experience_level: experienceLevel || undefined,
      skills: skills.trim() || undefined,
      refresh,
      limit: 10,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-2xs"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="job-q" className="block text-xs font-medium text-slate-700">
            Role or keywords
          </label>
          <input
            id="job-q"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Backend Engineer Intern"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="job-location" className="block text-xs font-medium text-slate-700">
            Location
          </label>
          <input
            id="job-location"
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Bengaluru, Remote"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="job-work-mode" className="block text-xs font-medium text-slate-700">
            Work mode
          </label>
          <select
            id="job-work-mode"
            value={workMode}
            onChange={(e) => setWorkMode(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            <option value="">Any</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">Onsite</option>
          </select>
        </div>

        <div>
          <label htmlFor="job-exp-level" className="block text-xs font-medium text-slate-700">
            Experience level
          </label>
          <select
            id="job-exp-level"
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          >
            <option value="">Any</option>
            <option value="intern">Intern</option>
            <option value="entry_level">Entry Level</option>
            <option value="junior">Junior</option>
            <option value="mid_level">Mid Level</option>
          </select>
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex-1">
          <label htmlFor="job-skills" className="block text-xs font-medium text-slate-700">
            Skills filter (comma-separated)
          </label>
          <input
            id="job-skills"
            type="text"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Python, FastAPI, React"
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <label className="inline-flex items-center gap-2 pb-2 text-xs font-medium text-slate-700">
          <input
            type="checkbox"
            checked={refresh}
            onChange={(e) => setRefresh(e.target.checked)}
          />
          Force fresh OpenAI web search
        </label>

        <button
          type="submit"
          disabled={isSearching}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          <Search className="h-4 w-4" aria-hidden="true" />
          {isSearching ? "Searching..." : "Discover Jobs"}
        </button>
      </div>
    </form>
  );
}
