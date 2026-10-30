const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Experience {
  company: string;
  role: string;
  start: string | null;
  end: string | null;
  summary: string;
}

export interface Profile {
  name: string | null;
  email: string | null;
  total_experience_years: number;
  seniority: string;
  job_titles: string[];
  skills: string[];
  experience: Experience[];
  locations: string[];
}

export interface Resume {
  id: number;
  file_name: string;
  profile: Profile;
  created_at: string;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string | null;
  employment_type: string | null;
  experience_required: string | null;
  salary: string | null;
  description: string | null;
  apply_url: string | null;
  source: string | null;
  posted_date: string | null;
  match_score: number | null;
  matched_skills: string[];
  is_new: boolean;
  created_at: string;
}

export interface SearchResponse {
  query: string;
  new_jobs: number;
  duplicates_rejected: number;
  jobs: Job[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function uploadResume(file: File): Promise<Resume> {
  const form = new FormData();
  form.append("file", file);
  return request("/api/resumes", { method: "POST", body: form });
}

export function searchJobs(resumeId: number, location: string | null, maxJobs: number): Promise<SearchResponse> {
  return request(`/api/resumes/${resumeId}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ location: location || null, max_jobs: maxJobs }),
  });
}
