import type { LookId } from "./schema";

export const ROTATING_WORDS = ["proof", "a leaf", "a lot", "a seal", "a name"];

export type LookMeta = {
  id: LookId;
  label: string;
  sentence: string;
  defaultPreset: string;
  defaultFont: string;
};

export const LOOKS: Record<LookId, LookMeta> = {
  estate: {
    id: "estate",
    label: "Estate",
    sentence: "Layered hills, a cream sky, and a leaf tag on every link.",
    defaultPreset: "mist",
    defaultFont: "fraunces",
  },
  harvest: {
    id: "harvest",
    label: "Harvest",
    sentence: "Cane baskets and paper lot labels for every paste.",
    defaultPreset: "basket",
    defaultFont: "newsreader",
  },
  loft: {
    id: "loft",
    label: "Loft",
    sentence: "Withering trays and process cards on the factory floor.",
    defaultPreset: "steam",
    defaultFont: "literata",
  },
  road: {
    id: "road",
    label: "Road",
    sentence: "Tea chests, warehouses, and stenciled dispatch links.",
    defaultPreset: "chest",
    defaultFont: "libre",
  },
  cup: {
    id: "cup",
    label: "Cup",
    sentence: "A packet, a poured cup, and passport lines for each tile.",
    defaultPreset: "cup",
    defaultFont: "fraunces",
  },
  plain: {
    id: "plain",
    label: "Plain",
    sentence: "Quiet fallback when a look is unknown.",
    defaultPreset: "paper",
    defaultFont: "source",
  },
};
