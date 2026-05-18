import type { NextConfig } from "next";

// Allow hot-reload (HMR) WebSocket connections from specific hosts when
// accessing the dev server from another machine on the local network.
// Set NEXT_ALLOWED_DEV_ORIGINS=192.168.x.x in .env (comma-separated for
// multiple hosts). Leave empty or unset to allow localhost only (default).
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
