"use client";

import { useMemo, useState } from "react";
import { Job } from "@/lib/api";

type SortKey = "match_score" | "title" | "company" | "location";

export default function JobsTable({ jobs }: { jobs: Job[] }) {
  const [filter, setFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("match_score");
  const [asc, setAsc] = useState(false);

  const rows = useMemo(() => {
    const q = filter.toLowerCase();
    const filtered = jobs.filter((j) =>
      [j.title, j.company, j.location, ...j.matched_skills].some((v) => v?.toLowerCase().includes(q)),
    );
    return filtered.sort((a, b) => {
      const av = a[sortKey] ?? "";
      const bv = b[sortKey] ?? "";
      const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return asc ? cmp : -cmp;
    });
  }, [jobs, filter, sortKey, asc]);

  function sortBy(key: SortKey) {
    if (key === sortKey) setAsc(!asc);
    else {
      setSortKey(key);
      setAsc(key !== "match_score");
    }
  }

  const header = (key: SortKey, label: string) => (
    <th onClick={() => sortBy(key)} className="sortable">
      {label} {sortKey === key ? (asc ? "▲" : "▼") : ""}
    </th>
  );

  if (jobs.length === 0) return <p className="muted">No jobs found. Try a different location.</p>;

  return (
    <>
      <input className="filter" placeholder="Filter by title, company, location or skill" value={filter} onChange={(e) => setFilter(e.target.value)} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {header("match_score", "Match")}
              {header("title", "Title")}
              {header("company", "Company")}
              {header("location", "Location")}
              <th>Experience</th>
              <th>Matched skills</th>
              <th>Posted</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((j) => (
              <tr key={j.id}>
                <td>
                  <span className={`score ${scoreClass(j.match_score)}`}>{j.match_score ?? "–"}</span>
                </td>
                <td>
                  {j.apply_url ? (
                    <a href={j.apply_url} target="_blank" rel="noopener noreferrer">
                      {j.title}
                    </a>
                  ) : (
                    j.title
                  )}
                  {j.is_new && <span className="badge">new</span>}
                  {j.description && <div className="small muted">{j.description}</div>}
                </td>
                <td>{j.company}</td>
                <td>{j.location ?? "–"}</td>
                <td>{j.experience_required ?? "–"}</td>
                <td className="small">{j.matched_skills.join(", ")}</td>
                <td className="small">{j.posted_date ?? "–"}</td>
                <td className="small">{j.source ?? "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function scoreClass(score: number | null) {
  if (score == null) return "";
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}
