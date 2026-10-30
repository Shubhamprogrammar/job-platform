"use client";

import { useState } from "react";
import { Resume, uploadResume } from "@/lib/api";

export default function ResumeUpload({ onUploaded }: { onUploaded: (r: Resume) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      onUploaded(await uploadResume(file));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <form className="card upload" onSubmit={onSubmit}>
      <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button type="submit" disabled={!file || uploading}>
        {uploading ? "Reading resume…" : "Upload & analyze"}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
