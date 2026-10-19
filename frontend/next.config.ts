import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: false,
  serverExternalPackages: ["better-sqlite3"],
  // No turbopack.rules for "*.css": routing every stylesheet through the
  // Tailwind loader also swallowed "*.module.css", so all CSS Module class
  // mappings came back undefined and module styles never applied (the page
  // rendered unstyled, with absolutely-positioned pieces piling up).
  // Tailwind v4 runs through PostCSS instead — see postcss.config.mjs.
};

export default nextConfig;
