import type { Tile } from "./schema";

export function tileLabel(tile: Tile): { title: string; subtitle?: string; href?: string } {
  switch (tile.type) {
    case "link":
      return { title: tile.title ?? tile.url, href: tile.url };
    case "social":
      return { title: tile.handle, subtitle: tile.platform, href: tile.platform === "email" ? `mailto:${tile.handle}` : undefined };
    case "text":
      return { title: tile.text };
    case "heading":
      return { title: tile.text };
    case "image":
      return { title: tile.caption ?? "Image", href: tile.url };
    case "video":
      return { title: tile.title ?? "Video", href: tile.url };
    case "music":
      return { title: tile.title ?? "Music", href: tile.url };
    case "repo":
      return { title: tile.repo, href: `https://github.com/${tile.repo}` };
    default:
      return { title: "Tile" };
  }
}
