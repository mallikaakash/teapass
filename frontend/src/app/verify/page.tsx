"use client";

import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_TEAPASS_API_URL ?? "http://localhost:8000";

export default function VerifyPage() {
  const [alias, setAlias] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const value = alias.trim();
    if (!value) return;
    try {
      const response = await fetch(`${API}/v1/public/batches/${encodeURIComponent(value)}`);
      const body = await response.text();
      setResult(body);
      if (!response.ok) setError("No public record for that alias.");
    } catch {
      setError("Could not reach the TeaPass API. Is it running on port 8000?");
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "80px auto", padding: 24 }}>
      <h1 style={{ fontFamily: "var(--font-fraunces)" }}>Verify a batch</h1>
      <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="Public batch alias" style={{ flex: 1, minWidth: 200, padding: 10 }} />
        <button type="submit" style={{ padding: "10px 16px", borderRadius: 999, background: "#1e4d34", color: "#fff", border: 0 }}>Verify</button>
      </form>
      {error ? <p role="alert">{error}</p> : null}
      {result ? <pre style={{ marginTop: 16, padding: 16, background: "#f3ecdf", overflow: "auto", fontSize: 12 }}>{result}</pre> : null}
      <p><Link href="/">← Home</Link></p>
    </main>
  );
}
