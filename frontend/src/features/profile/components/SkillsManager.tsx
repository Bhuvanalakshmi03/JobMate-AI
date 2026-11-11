import { Plus, Trash2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Card } from "../../../components/ui/Card";
import { StateNotice } from "../../../components/ui/StateNotice";
import { StatusBadge } from "../../../components/ui/StatusBadge";
import type {
  SkillCategory,
  SkillInput,
  SkillProficiency,
  UserSkill,
} from "../../../types/profile";

interface SkillsManagerProps {
  skills: UserSkill[];
  isLoading: boolean;
  loadError: Error | null;
  isSaving: boolean;
  saveError: Error | null;
  saveSucceeded: boolean;
  onSave: (skills: SkillInput[]) => Promise<unknown>;
}

const CATEGORIES: SkillCategory[] = ["technical", "language", "framework", "tool", "soft"];
const PROFICIENCIES: SkillProficiency[] = ["beginner", "intermediate", "advanced", "expert"];

export function SkillsManager({
  skills,
  isLoading,
  loadError,
  isSaving,
  saveError,
  saveSucceeded,
  onSave,
}: SkillsManagerProps) {
  const [draftSkills, setDraftSkills] = useState<SkillInput[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState<SkillCategory>("technical");
  const [proficiency, setProficiency] = useState<SkillProficiency>("intermediate");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setDraftSkills(
      skills.map((s) => ({
        name: s.name,
        category: s.category,
        proficiency: s.proficiency,
        years_experience: s.years_experience ?? null,
        is_verified: s.is_verified,
      }))
    );
  }, [skills]);

  const handleAddSkill = (e: FormEvent) => {
    e.preventDefault();
    const cleaned = name.trim();
    if (!cleaned) {
      setValidationError("Enter a skill name before adding.");
      return;
    }

    const exists = draftSkills.some(
      (item) => item.name.toLowerCase() === cleaned.toLowerCase() && item.category === category
    );
    if (exists) {
      setValidationError(`"${cleaned}" is already listed under ${category}.`);
      return;
    }

    setValidationError(null);
    setDraftSkills((prev) => [
      ...prev,
      {
        name: cleaned,
        category,
        proficiency,
        is_verified: true,
      },
    ]);
    setName("");
  };

  const handleRemove = (index: number) => {
    setDraftSkills((prev) => prev.filter((_, idx) => idx !== index));
  };

  return (
    <Card
      title="Skills Inventory"
      subtitle="Technical, framework, tool, language, and soft skills used for job matching."
      action={
        <button
          type="button"
          onClick={() => void onSave(draftSkills)}
          disabled={isSaving || isLoading}
          className="rounded-lg bg-indigo-600 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
        >
          {isSaving ? "Saving skills..." : "Save Skills"}
        </button>
      }
    >
      {isLoading && (
        <StateNotice
          title="Loading skills..."
          description="Fetching your saved skill profile."
          tone="info"
        />
      )}

      {loadError && (
        <StateNotice
          title="Failed to load skills"
          description={loadError.message}
          tone="error"
        />
      )}

      {!isLoading && !loadError && (
        <div className="space-y-4">
          <form onSubmit={handleAddSkill} className="grid gap-3 sm:grid-cols-4">
            <div className="sm:col-span-2">
              <label htmlFor="skill-name" className="block text-xs font-medium text-slate-700">
                Skill name
              </label>
              <input
                id="skill-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Python, React, PostgreSQL"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="skill-category" className="block text-xs font-medium text-slate-700">
                Category
              </label>
              <select
                id="skill-category"
                value={category}
                onChange={(e) => setCategory(e.target.value as SkillCategory)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end gap-2">
              <div className="flex-1">
                <label
                  htmlFor="skill-proficiency"
                  className="block text-xs font-medium text-slate-700"
                >
                  Level
                </label>
                <select
                  id="skill-proficiency"
                  value={proficiency}
                  onChange={(e) => setProficiency(e.target.value as SkillProficiency)}
                  className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none"
                >
                  {PROFICIENCIES.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="submit"
                aria-label="Add skill"
                className="inline-flex h-9.5 items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                Add
              </button>
            </div>
          </form>

          {validationError && (
            <p role="alert" className="text-xs font-medium text-rose-700">
              {validationError}
            </p>
          )}

          {saveError && (
            <StateNotice
              title="Unable to save skills"
              description={saveError.message}
              tone="error"
            />
          )}

          {saveSucceeded && !saveError && (
            <StateNotice
              title="Skills updated"
              description="Your skills list has been saved to your verified profile."
              tone="info"
            />
          )}

          {draftSkills.length === 0 ? (
            <StateNotice
              title="No skills added yet"
              description="Add your programming languages, frameworks, tools, or soft skills above and click Save Skills."
              tone="empty"
            />
          ) : (
            <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200">
              {draftSkills.map((item, idx) => (
                <li
                  key={`${item.category}-${item.name.toLowerCase()}`}
                  className="flex items-center justify-between gap-3 px-4 py-2.5 text-sm"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-slate-900">{item.name}</span>
                    <StatusBadge label={item.category} tone="neutral" />
                    <StatusBadge label={item.proficiency} tone="info" />
                  </div>
                  <button
                    type="button"
                    aria-label={`Remove ${item.name}`}
                    onClick={() => handleRemove(idx)}
                    className="rounded p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

