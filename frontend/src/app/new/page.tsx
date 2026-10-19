import Link from "next/link";
import { redirect } from "next/navigation";
import { createPage } from "@/lib/page-ops";
import { PICKER_LOOKS } from "@/lib/schema";
import { RESERVED_USERNAMES, usernameSchema } from "@/lib/schema";
import { upsertPage, getPageByUserId } from "@/db";
import { getSessionUserId, SESSION_COOKIE } from "@/lib/session";
import { cookies } from "next/headers";
import { LOOKS } from "@/lib/looks";

async function createGarden(formData: FormData) {
  "use server";
  const name = String(formData.get("name") ?? "").trim();
  const bio = String(formData.get("bio") ?? "").trim();
  const username = String(formData.get("username") ?? "").trim();
  const look = String(formData.get("look") ?? "estate");
  const parsed = usernameSchema.safeParse(username);
  if (!parsed.success || RESERVED_USERNAMES.has(username.toLowerCase()) || !name) {
    redirect("/new?error=1");
  }
  const jar = await cookies();
  let userId = jar.get(SESSION_COOKIE)?.value;
  if (!userId) {
    userId = `user_${crypto.randomUUID()}`;
    jar.set(SESSION_COOKIE, userId, { httpOnly: true, sameSite: "lax", path: "/" });
  }
  const state = createPage(parsed.data, name, bio || "A garden on TeaPass.", look);
  upsertPage(userId, parsed.data, JSON.stringify(state.draft), JSON.stringify(state.published), 1, true);
  redirect("/edit");
}

export default async function NewGardenPage({ searchParams }: PageProps<"/new">) {
  const userId = await getSessionUserId();
  if (userId && getPageByUserId(userId)) redirect("/edit");
  const { error, look } = await searchParams;
  const defaultLook = PICKER_LOOKS.includes(look as (typeof PICKER_LOOKS)[number]) ? look : "estate";
  return (
    <main style={{ maxWidth: 480, margin: "80px auto", padding: 24, fontFamily: "var(--font-source)" }}>
      <h1 style={{ fontFamily: "var(--font-fraunces)" }}>Start a garden page</h1>
      {error ? <p role="alert">Check the garden address and name.</p> : null}
      <form action={createGarden} style={{ display: "grid", gap: 12 }}>
        <label>
          Garden name
          <input name="name" required style={{ width: "100%", padding: 10 }} />
        </label>
        <label>
          Address
          <input name="username" required placeholder="sonapur" style={{ width: "100%", padding: 10 }} />
        </label>
        <label>
          Bio
          <textarea name="bio" rows={3} style={{ width: "100%", padding: 10 }} />
        </label>
        <label>
          Look
          <select name="look" defaultValue={defaultLook} style={{ width: "100%", padding: 10 }}>
            {PICKER_LOOKS.map((id) => (
              <option key={id} value={id}>{LOOKS[id].label}</option>
            ))}
          </select>
        </label>
        <button type="submit" style={{ padding: "12px 16px", borderRadius: 999, background: "#1e4d34", color: "#fff", border: 0 }}>
          Create and open studio
        </button>
      </form>
      <p><Link href="/">← Back</Link></p>
    </main>
  );
}
