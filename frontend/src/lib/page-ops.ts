import { tileFromInput } from "./detect";
import type { PageDocument, Tile } from "./schema";
import { normalizeLookId, parsePage } from "./schema";
import { LOOKS } from "./looks";

export type PageState = {
  username: string;
  draft: PageDocument;
  published: PageDocument | null;
  version: number;
};

export type PageBrief = {
  name: string;
  bio: string;
  look: string;
  links: string[];
};

function starterDocument(look: string, name: string, bio: string): PageDocument {
  const lookId = normalizeLookId(look);
  const meta = LOOKS[lookId];
  const tiles: Tile[] = [
    { id: "intro", type: "heading", text: "On the garden", size: "w" },
    ...["garden@example.com", "https://example.com"].map((link) => tileFromInput(link)),
  ];
  return {
    version: 2,
    profile: { name, bio },
    theme: {
      look: lookId,
      layout: "bento",
      preset: meta.defaultPreset,
      font: meta.defaultFont,
      motion: true,
      ambient: true,
    },
    tiles,
    badge: true,
  };
}

export function createPage(username: string, name: string, bio: string, look: string): PageState {
  const draft = starterDocument(look, name, bio);
  return { username, draft, published: draft, version: 1 };
}

export function importDocument(username: string, input: PageBrief | PageDocument): PageState {
  if ("version" in input) {
    const draft = parsePage(input);
    return { username, draft, published: draft, version: 1 };
  }
  const draft = starterDocument(input.look, input.name, input.bio);
  draft.tiles = [...draft.tiles, ...input.links.map((link) => tileFromInput(link))];
  return { username, draft, published: draft, version: 1 };
}

export function addTile(state: PageState, tile: Tile): PageState {
  return { ...state, draft: { ...state.draft, tiles: [...state.draft.tiles, tile] } };
}

export function addTiles(state: PageState, raw: string): PageState {
  const tile = tileFromInput(raw);
  return addTile(state, tile);
}

export function updateTile(state: PageState, id: string, patch: Partial<Tile>): PageState {
  const tiles = state.draft.tiles.map((tile) => (tile.id === id ? { ...tile, ...patch } as Tile : tile));
  return { ...state, draft: { ...state.draft, tiles } };
}

export function moveTile(state: PageState, from: number, to: number): PageState {
  const tiles = [...state.draft.tiles];
  const [item] = tiles.splice(from, 1);
  tiles.splice(to, 0, item);
  return { ...state, draft: { ...state.draft, tiles } };
}

export function removeTile(state: PageState, id: string): PageState {
  return { ...state, draft: { ...state.draft, tiles: state.draft.tiles.filter((t) => t.id !== id) } };
}

export function setTheme(state: PageState, theme: Partial<PageDocument["theme"]>): PageState {
  const next = { ...state.draft.theme, ...theme };
  if (theme.look) next.look = normalizeLookId(theme.look);
  return { ...state, draft: { ...state.draft, theme: next } };
}

export function setProfile(state: PageState, profile: Partial<PageDocument["profile"]>): PageState {
  return { ...state, draft: { ...state.draft, profile: { ...state.draft.profile, ...profile } } };
}

export function publish(state: PageState): PageState {
  return { ...state, published: state.draft, version: state.version + 1 };
}

export function saveDraft(state: PageState, baseVersion: number): PageState | "conflict" {
  if (baseVersion !== state.version) return "conflict";
  return { ...state, version: state.version + 1 };
}
