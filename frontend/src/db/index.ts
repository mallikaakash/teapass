import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { eq } from "drizzle-orm";
import fs from "node:fs";
import path from "node:path";
import { parsePage } from "@/lib/schema";
import { SAMPLE_PAGE, SAMPLE_USERNAME } from "@/lib/sample";
import * as schema from "./schema";

const globalForDb = globalThis as unknown as { teapassSqlite?: Database.Database };

function databasePath() {
  return process.env.TEAPASS_SQLITE_PATH ?? path.join(process.cwd(), "data", "teapass.sqlite");
}

export function getDb() {
  if (!globalForDb.teapassSqlite) {
    const file = databasePath();
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const sqlite = new Database(file);
    sqlite.exec(`
      CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        username TEXT NOT NULL UNIQUE,
        draft TEXT NOT NULL,
        published TEXT,
        version INTEGER NOT NULL DEFAULT 1,
        published_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS enrich_cache (
        key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        expires_at INTEGER NOT NULL
      );
    `);
    globalForDb.teapassSqlite = sqlite;
    seedSample(sqlite);
  }
  return drizzle(globalForDb.teapassSqlite, { schema });
}

function seedSample(sqlite: Database.Database) {
  const row = sqlite.prepare("SELECT id FROM pages WHERE username = ?").get(SAMPLE_USERNAME);
  if (row) return;
  const now = new Date().toISOString();
  sqlite
    .prepare(
      `INSERT INTO pages (user_id, username, draft, published, version, published_at, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .run("demo-user", SAMPLE_USERNAME, JSON.stringify(SAMPLE_PAGE), JSON.stringify(SAMPLE_PAGE), 1, now, now, now);
}

export type StoredPage = {
  userId: string;
  username: string;
  draft: ReturnType<typeof parsePage>;
  published: ReturnType<typeof parsePage> | null;
  version: number;
};

function rowToStored(row: typeof schema.pages.$inferSelect): StoredPage {
  return {
    userId: row.userId,
    username: row.username,
    draft: parsePage(JSON.parse(row.draft)),
    published: row.published ? parsePage(JSON.parse(row.published)) : null,
    version: row.version,
  };
}

export function getPageByUsername(username: string): StoredPage | null {
  const db = getDb();
  const row = db.select().from(schema.pages).where(eq(schema.pages.username, username)).get();
  return row ? rowToStored(row) : null;
}

export function getPageByUserId(userId: string): StoredPage | null {
  const db = getDb();
  const row = db.select().from(schema.pages).where(eq(schema.pages.userId, userId)).get();
  return row ? rowToStored(row) : null;
}

export function upsertPage(
  userId: string,
  username: string,
  draft: string,
  published: string | null,
  version: number,
  publishNow = false,
) {
  const db = getDb();
  const now = new Date().toISOString();
  const existing = getPageByUserId(userId);
  if (!existing) {
    db.insert(schema.pages).values({
      userId,
      username,
      draft,
      published,
      version,
      publishedAt: publishNow ? now : null,
      createdAt: now,
      updatedAt: now,
    }).run();
    return;
  }
  db.update(schema.pages)
    .set({
      username,
      draft,
      published,
      version,
      publishedAt: publishNow ? now : existing.published ? now : null,
      updatedAt: now,
    })
    .where(eq(schema.pages.userId, userId))
    .run();
}
