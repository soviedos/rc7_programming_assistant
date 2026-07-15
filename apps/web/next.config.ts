import type { NextConfig } from "next";

// Allow hot-reload (HMR) WebSocket connections from specific hosts when running
// `next dev` from another machine on the local network.
//
// Only takes effect outside Docker: the `web` container serves the standalone
// production build (`node server.js`), where allowedDevOrigins is inert, and it
// has no env_file — so setting NEXT_ALLOWED_DEV_ORIGINS in .env does nothing.
// To use it, export it in the shell running `next dev` (comma-separated hosts).
const allowedDevOrigins = process.env.NEXT_ALLOWED_DEV_ORIGINS
  ? process.env.NEXT_ALLOWED_DEV_ORIGINS.split(",").map((h) => h.trim()).filter(Boolean)
  : [];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for the multi-stage Docker build: produces a self-contained
  // .next/standalone directory that can be run with `node server.js`
  // without needing node_modules in the final image.
  output: "standalone",
  ...(allowedDevOrigins.length > 0 && { allowedDevOrigins }),
};

export default nextConfig;
