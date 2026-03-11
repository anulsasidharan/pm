import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.test.ts", "**/*.test.tsx"],
    coverage: {
      provider: "v8",
      include: ["app/**/*.ts", "app/**/*.tsx"],
      thresholds: {
        lines: 80,
        statements: 80,
        functions: 80,
        branches: 80
      }
    }
  }
});