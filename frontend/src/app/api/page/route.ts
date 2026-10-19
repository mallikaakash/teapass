import { NextResponse } from "next/server";
import { getPageByUserId, upsertPage } from "@/db";
import { parsePage } from "@/lib/schema";
import { getSessionUserId } from "@/lib/session";

export async function GET() {
  const userId = await getSessionUserId();
  if (!userId) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const row = getPageByUserId(userId);
  if (!row) return NextResponse.json({ error: "not_found" }, { status: 404 });
  return NextResponse.json({
    username: row.username,
    draft: row.draft,
    published: row.published,
    version: row.version,
  });
}

export async function PUT(request: Request) {
  const userId = await getSessionUserId();
  if (!userId) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const row = getPageByUserId(userId);
  if (!row) return NextResponse.json({ error: "not_found" }, { status: 404 });
  const body = await request.json();
  const draft = parsePage(body.draft);
  const baseVersion = Number(body.baseVersion);
  const shouldPublish = Boolean(body.publish);
  if (baseVersion !== row.version) return NextResponse.json({ error: "conflict" }, { status: 409 });
  const nextVersion = row.version + 1;
  const published = shouldPublish ? draft : row.published;
  upsertPage(userId, row.username, JSON.stringify(draft), published ? JSON.stringify(published) : null, nextVersion, shouldPublish);
  return NextResponse.json({
    username: row.username,
    draft,
    published,
    version: nextVersion,
  });
}
