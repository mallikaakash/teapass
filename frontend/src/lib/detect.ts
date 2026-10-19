import type { Tile } from "./schema";

const VIDEO_HOSTS = ["youtube.com", "youtu.be", "vimeo.com"];
const MUSIC_HOSTS = ["spotify.com", "music.apple.com", "soundcloud.com"];
const SOCIAL_HOSTS: Record<string, string> = {
  "twitter.com": "x",
  "x.com": "x",
  "instagram.com": "instagram",
  "github.com": "github",
  "linkedin.com": "linkedin",
};

function id() {
  return `t_${Math.random().toString(36).slice(2, 10)}`;
}

function isEmail(raw: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw);
}

function isImagePath(raw: string) {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(raw) || raw.startsWith("/");
}

function parseRepo(raw: string) {
  const trimmed = raw.replace(/^https?:\/\/github\.com\//, "").replace(/\/$/, "");
  const match = /^([A-Za-z0-9_-]+)\/([A-Za-z0-9_.-]+)$/.exec(trimmed);
  if (!match) return null;
  if (match[1].includes(".")) return null;
  return `${match[1]}/${match[2]}`;
}

function hostOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function tileFromInput(raw: string): Tile {
  const value = raw.trim();
  if (!value) return { id: id(), type: "text", text: "", size: "w" };

  if (isEmail(value)) {
    return { id: id(), type: "social", platform: "email", handle: value, size: "w" };
  }
  if (isImagePath(value)) {
    return { id: id(), type: "image", src: value, size: "w" };
  }
  const repo = parseRepo(value);
  if (repo) {
    return { id: id(), type: "repo", repo, size: "w" };
  }
  if (/^https?:\/\//i.test(value)) {
    const host = hostOf(value);
    if (host && VIDEO_HOSTS.some((h) => host.endsWith(h))) {
      return { id: id(), type: "video", url: value, size: "w" };
    }
    if (host && MUSIC_HOSTS.some((h) => host.endsWith(h))) {
      return { id: id(), type: "music", url: value, size: "w" };
    }
    if (host) {
      for (const [domain, platform] of Object.entries(SOCIAL_HOSTS)) {
        if (host.endsWith(domain)) {
          const path = new URL(value).pathname.replace(/^\//, "").split("/")[0];
          if (path) return { id: id(), type: "social", platform, handle: path, size: "s" };
        }
      }
    }
    return { id: id(), type: "link", url: value, size: "w" };
  }
  return { id: id(), type: "text", text: value, size: "w" };
}
