import Link from "next/link";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/session";

async function signIn(formData: FormData) {
  "use server";
  const next = String(formData.get("next") ?? "/edit");
  const jar = await cookies();
  if (!jar.get(SESSION_COOKIE)?.value) {
    jar.set(SESSION_COOKIE, `user_${crypto.randomUUID()}`, { httpOnly: true, sameSite: "lax", path: "/" });
  }
  redirect(next.startsWith("/") ? next : "/edit");
}

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const { next } = await searchParams;
  return (
    <main style={{ maxWidth: 420, margin: "100px auto", padding: 24 }}>
      <h1>Studio sign-in</h1>
      <p>Local demo sign-in creates a browser session. OIDC wiring comes later.</p>
      <form action={signIn}>
        <input type="hidden" name="next" value={typeof next === "string" ? next : "/edit"} />
        <button type="submit" style={{ padding: "12px 18px", borderRadius: 999, background: "#1e4d34", color: "#fff", border: 0 }}>
          Continue
        </button>
      </form>
      <p><Link href="/">← Back</Link></p>
    </main>
  );
}
