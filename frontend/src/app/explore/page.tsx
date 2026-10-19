import Link from "next/link";

export default function ExplorePage() {
  return (
    <main style={{ maxWidth: 720, margin: "80px auto", padding: 24, lineHeight: 1.6 }}>
      <h1 style={{ fontFamily: "var(--font-fraunces)" }}>Explore the technology</h1>
      <p>
        TeaPass pairs a garden page product with a confidential traceability ledger. Public pages show what you publish;
        batch proofs and lab evidence are verified against the API without exposing private blend recipes.
      </p>
      <ul>
        <li>FastAPI ledger with signed events and Midnight Compact proofs</li>
        <li>Public verification at <code>/v1/public/batches/&lt;alias&gt;</code></li>
        <li>Client-side signing via the TeaPass SDK</li>
      </ul>
      <p>
        <Link href="/verify">Verify a batch</Link> · <Link href="/demo">Demo garden</Link> · <Link href="/">Home</Link>
      </p>
    </main>
  );
}
