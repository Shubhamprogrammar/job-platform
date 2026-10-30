"use client";

import { useState } from "react";
import JobsTable from "@/components/JobsTable";
import ProfileCard from "@/components/ProfileCard";
import ResumeUpload from "@/components/ResumeUpload";
import { Resume, SearchResponse, searchJobs } from "@/lib/api";

export default function Home() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [location, setLocation] = useState("");
  const [maxJobs, setMaxJobs] = useState(15);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onUploaded(r: Resume) {
    setResume(r);
    setResult(null);
    setLocation(r.profile.locations[0] ?? "");
  }

  async function onSearch() {
    if (!resume) return;
    setSearching(true);
    setError(null);
    try {
      setResult(await searchJobs(resume.id, location.trim(), maxJobs));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSearching(false);
    }
  }

  return (
    <main className="container">
      <h1>Job Finder</h1>
      <p className="muted">Upload your resume. We pull out your skills and experience, then search the web for matching jobs.</p>

      <ResumeUpload onUploaded={onUploaded} />

      {resume && (
        <>
          <ProfileCard profile={resume.profile} />

          <section className="card search-bar">
            <label>
              Location
              <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Pune, Remote" />
            </label>
            <label>
              Max jobs
              <input
                type="number"
                min={1}
                max={30}
                value={maxJobs}
                onChange={(e) => setMaxJobs(Math.min(30, Math.max(1, Number(e.target.value) || 1)))}
              />
            </label>
            <button onClick={onSearch} disabled={searching}>
              {searching ? "Searching the web…" : "Find jobs"}
            </button>
          </section>
          {searching && <p className="muted">Web search can take up to a minute.</p>}
          {error && <p className="error">{error}</p>}
        </>
      )}

      {result && (
        <section>
          <p className="summary">
            <strong>{result.new_jobs}</strong> new jobs saved · <strong>{result.duplicates_rejected}</strong> duplicates
            rejected (already in database)
          </p>
          <p className="muted small">Query: {result.query}</p>
          <JobsTable jobs={result.jobs} />
        </section>
      )}
    </main>
  );
}
