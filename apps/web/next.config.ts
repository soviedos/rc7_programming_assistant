import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for the multi-stage Docker build: produces a self-contained
  // .next/standalone directory that can be run with `node server.js`
  // without needing node_modules in the final image.
  output: "standalone",
};

export default nextConfig;
