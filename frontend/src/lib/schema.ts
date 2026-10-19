import { z } from "zod";

export const PICKER_LOOKS = ["estate", "harvest", "loft", "road", "cup"] as const;
export const LOOK_IDS = [...PICKER_LOOKS, "plain"] as const;
export type LookId = (typeof LOOK_IDS)[number];

const retiredLooks: Record<string, LookId> = { garden: "estate" };

export const tileSize = z.enum(["s", "w", "t", "l"]);
export const layout = z.enum(["bento", "list", "canvas"]);

const pos = z.object({
  x: z.number(),
  y: z.number(),
  w: z.number(),
  h: z.number(),
  r: z.number().min(-15).max(15).optional(),
  z: z.number().optional(),
});

const focus = z.object({ x: z.number().min(0).max(100), y: z.number().min(0).max(100) });

const baseTile = z.object({
  id: z.string().min(1),
  size: tileSize.default("s"),
  color: z.string().optional(),
  pos: pos.optional(),
  focus: focus.optional(),
  zoom: z.number().min(1).max(3).optional(),
});

export const tileSchema = z.discriminatedUnion("type", [
  baseTile.extend({ type: z.literal("link"), url: z.string().url(), title: z.string().optional() }),
  baseTile.extend({ type: z.literal("social"), platform: z.string(), handle: z.string() }),
  baseTile.extend({ type: z.literal("text"), text: z.string(), look: z.literal("stamp").optional() }),
  baseTile.extend({ type: z.literal("heading"), text: z.string() }),
  baseTile.extend({ type: z.literal("image"), src: z.string(), url: z.string().url().optional(), caption: z.string().optional() }),
  baseTile.extend({ type: z.literal("video"), url: z.string().url(), title: z.string().optional() }),
  baseTile.extend({ type: z.literal("music"), url: z.string().url(), title: z.string().optional() }),
  baseTile.extend({ type: z.literal("repo"), repo: z.string(), title: z.string().optional() }),
]);

export type Tile = z.infer<typeof tileSchema>;

export const pageSchema = z.object({
  version: z.literal(2),
  profile: z.object({
    name: z.string(),
    bio: z.string(),
    avatar: z.string().optional(),
    location: z.string().optional(),
  }),
  theme: z.object({
    look: z.string(),
    layout: layout,
    preset: z.string(),
    font: z.string(),
    photos: z.enum(["natural", "mono", "dither", "ascii"]).optional(),
    motion: z.boolean().default(true),
    ambient: z.boolean().default(true),
  }),
  tiles: z.array(tileSchema),
  badge: z.boolean().default(true),
  seo: z.object({ title: z.string().optional(), description: z.string().optional() }).optional(),
});

export type PageDocument = z.infer<typeof pageSchema>;

export function normalizeLookId(id: string): LookId {
  const mapped = retiredLooks[id] ?? id;
  return (LOOK_IDS.includes(mapped as LookId) ? mapped : "plain") as LookId;
}

export function parsePage(input: unknown): PageDocument {
  const parsed = pageSchema.parse(input);
  return {
    ...parsed,
    theme: { ...parsed.theme, look: normalizeLookId(parsed.theme.look) },
  };
}

export const usernameSchema = z
  .string()
  .min(3)
  .max(30)
  .regex(/^[a-zA-Z0-9_-]+$/);

export const RESERVED_USERNAMES = new Set([
  "edit",
  "login",
  "new",
  "api",
  "demo",
  "explore",
  "verify",
  "_next",
  "favicon.ico",
]);
