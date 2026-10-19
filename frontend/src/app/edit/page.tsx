import { redirect } from "next/navigation";
import { Studio } from "@/components/studio/Studio";
import { getPageByUserId } from "@/db";
import { getSessionUserId } from "@/lib/session";

export default async function EditPage() {
  const userId = await getSessionUserId();
  if (!userId) redirect("/login?next=/edit");
  const row = getPageByUserId(userId);
  if (!row) redirect("/new");
  return (
    <Studio
      initial={{
        username: row.username,
        draft: row.draft,
        published: row.published,
        version: row.version,
      }}
    />
  );
}
