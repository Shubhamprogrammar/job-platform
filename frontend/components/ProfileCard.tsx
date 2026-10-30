import { Profile } from "@/lib/api";

export default function ProfileCard({ profile }: { profile: Profile }) {
  return (
    <section className="card">
      <h2>{profile.name ?? "Candidate"}</h2>
      <p>
        <strong>{profile.total_experience_years} years</strong> · {profile.seniority}
        {profile.locations.length > 0 && <> · {profile.locations.join(", ")}</>}
      </p>
      {profile.job_titles.length > 0 && <p className="muted">Target roles: {profile.job_titles.join(", ")}</p>}
      <div className="chips">
        {profile.skills.map((s) => (
          <span key={s} className="chip">
            {s}
          </span>
        ))}
      </div>
      {profile.experience.length > 0 && (
        <details>
          <summary>Experience ({profile.experience.length})</summary>
          <ul>
            {profile.experience.map((x, i) => (
              <li key={i}>
                <strong>{x.role}</strong> at {x.company}{" "}
                <span className="muted">
                  ({x.start ?? "?"} – {x.end ?? "?"})
                </span>
                <div className="small">{x.summary}</div>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
