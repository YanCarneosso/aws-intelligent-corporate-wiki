import eslint from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.es2022 },
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "public/**",
      "eslint.config.mjs",
      "vite.config.js",
      "vite.config.d.ts",
    ],
  },
);
