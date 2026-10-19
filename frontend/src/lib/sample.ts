import type { PageDocument } from "./schema";

export const SAMPLE_USERNAME = "sonapur";

export const SAMPLE_PAGE: PageDocument = {
  version: 2,
  profile: {
    name: "Sonapur Tea Estate",
    bio: "First-flush Assam, picked at dawn, with a seal beside every lot.",
    location: "Dibrugarh, Assam",
  },
  theme: {
    look: "estate",
    layout: "bento",
    preset: "mist",
    font: "fraunces",
    motion: true,
    ambient: true,
  },
  tiles: [
    { id: "h1", type: "heading", text: "This season", size: "w" },
    {
      id: "lot",
      type: "text",
      text: "Lot DTE-2024-0512 · first flush",
      size: "w",
      look: "stamp",
    },
    {
      id: "mail",
      type: "social",
      platform: "email",
      handle: "garden@sonapur.example",
      size: "s",
    },
    {
      id: "repo",
      type: "repo",
      repo: "sonapur/flush",
      size: "w",
    },
    {
      id: "leaf",
      type: "image",
      src: "/garden/leaf.svg",
      caption: "Leaf photograph",
      size: "s",
    },
    {
      id: "video",
      type: "video",
      url: "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
      size: "w",
    },
    {
      id: "note",
      type: "text",
      text: "Plucked at first light. Withered on the loft. Rolled before noon.",
      size: "l",
    },
  ],
  badge: true,
  seo: { title: "Sonapur Tea Estate", description: "Assam garden page on TeaPass." },
};

export const SEALS = [
  {
    id: "harvest",
    title: "Harvest collection record",
    lines: ["Picker section 4B", "Signed at 06:12 IST", "Lot hash anchored"],
  },
  {
    id: "process",
    title: "Processing transformation",
    lines: ["Input 1,000 kg green leaf", "Output 240 kg made tea", "Mass balance verified"],
  },
  {
    id: "road",
    title: "Dispatch receipt",
    lines: ["Factory to warehouse", "Dual-signed custody", "Chain receipt stored"],
  },
  {
    id: "blend",
    title: "Blend integrity proof",
    lines: ["Inputs matched to issued notes", "Recipe ciphertext not disclosed", "Output lot issued"],
  },
  {
    id: "lab",
    title: "Lab attestation",
    lines: ["Pesticide residue pass", "Heavy metals pass", "Batch reference matched"],
  },
] as const;
