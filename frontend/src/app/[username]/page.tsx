import { notFound } from "next/navigation";
import { PageView } from "@/components/page/PageView";
import { getPageByUsername } from "@/db";
import { RESERVED_USERNAMES } from "@/lib/schema";

export default async function PublicGardenPage({ params }: PageProps<"/[username]">) {
  const { username } = await params;
  if (RESERVED_USERNAMES.has(username.toLowerCase())) notFound();
  const row = getPageByUsername(username);
  if (!row?.published) notFound();
  return <PageView page={row.published} username={row.username} />;
}
