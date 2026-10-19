/** Enrichment runs after detection; public render reads cache only. */

export type EnrichedLink = { title?: string; image?: string };
export type EnrichedRepo = { description?: string; stars?: number };

export async function enrichTile(_tile: unknown): Promise<unknown> {
  return _tile;
}
