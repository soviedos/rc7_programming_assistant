import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    exclude: [".next/**", "node_modules/**"],
    setupFiles: ["./vitest.setup.ts"],
  },
});
