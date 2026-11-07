---
name: javascript-application-design
description: JavaScript and TypeScript application structure, tooling, and conventions. Load this skill when starting a new project, adding dependencies, configuring tooling, or making architectural decisions in any JavaScript or TypeScript codebase. Covers pnpm, ESM, strict TypeScript, ESLint, Prettier, and per-application-type conventions for React SPA, Next.js, REST APIs, and CLI tools.
license: MIT
compatibility: opencode
---

## Non-negotiable defaults

These apply to every JavaScript or TypeScript project without exception.

**Package manager: pnpm — always.** Never use npm or yarn. Never run `npm install`, `yarn add`, or `npx`. The correct commands are `pnpm install`, `pnpm add`, and `pnpm dlx`. If a `package-lock.json` or `yarn.lock` exists in a project you are working on, flag it.

**Runtime: Node.js.** Do not introduce Bun or Deno unless explicitly instructed.

**Module system: ESM only.** Every project uses `"type": "module"` in `package.json`. Never use `require()`, `module.exports`, or `.cjs` files. If a dependency forces CommonJS interop, use dynamic `import()` and document why.

**Language: TypeScript with strict mode.** Every project has a `tsconfig.json` with `"strict": true`. No `any`. No `@ts-ignore` without a comment explaining why and a ticket to fix it. No `as SomeType` casts unless genuinely necessary, and never `as any`.

---

## Project initialisation

When creating a new project:

1. Create `package.json` with `"type": "module"` and `"engines": { "node": ">=20" }`
2. Install TypeScript and configure `tsconfig.json` with strict mode (see below)
3. Install and configure ESLint and Prettier (see below)
4. Create `.nvmrc` or `.node-version` with the target Node.js version
5. Create `.gitignore` that excludes `node_modules`, `dist`, `.env`, and build artefacts
6. Add a `pnpm-lock.yaml` to git — never `.gitignore` the lockfile

Never commit `node_modules`. Never commit `.env` files. Always commit lockfiles.

---

## TypeScript configuration

Base `tsconfig.json` for all projects:

```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "dist"
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

For Next.js projects, let `create-next-app` generate the tsconfig and extend it rather than replacing it. Always verify `"strict": true` is present.

For projects that use a bundler (Vite, tsup), set `"noEmit": true` in tsconfig — the bundler handles output, not `tsc`. Keep a separate `tsconfig.build.json` without `noEmit` if type declarations need to be emitted for a library.

**Strict mode means:**
- `strictNullChecks`: always handle `null` and `undefined` explicitly
- `noImplicitAny`: every parameter and variable must have an inferable or explicit type
- `strictFunctionTypes`: no unsafe function type variance
- No exceptions. If a third-party type is wrong, use a type assertion with a comment, not a global `any`.

---

## ESLint and Prettier

### Prettier

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2
}
```

Save as `.prettierrc.json`. Add `.prettierignore` to exclude `dist`, `node_modules`, and generated files.

Install:
```
pnpm add -D prettier
```

Add to `package.json` scripts:
```json
"format": "prettier --write .",
"format:check": "prettier --check ."
```

### ESLint

Use the flat config format (`eslint.config.js`) — not the legacy `.eslintrc` format.

Install base dependencies:
```
pnpm add -D eslint @eslint/js typescript-eslint eslint-config-prettier
```

Base `eslint.config.js`:
```js
import eslint from '@eslint/js'
import tseslint from 'typescript-eslint'
import prettier from 'eslint-config-prettier'

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  prettier,
  {
    languageOptions: {
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
)
```

Add to `package.json` scripts:
```json
"lint": "eslint .",
"lint:fix": "eslint . --fix"
```

For React projects, additionally install:
```
pnpm add -D eslint-plugin-react eslint-plugin-react-hooks eslint-plugin-jsx-a11y
```

---

## Dependency management

**Production vs development dependencies matter.** Type definitions, test frameworks, linters, bundlers, and build tools are always `devDependencies`. Never install them as production dependencies.

```
pnpm add express          # production dependency
pnpm add -D @types/express vitest typescript eslint  # dev dependencies
```

**Pin major versions, not exact versions.** Use `^` (caret) ranges in `package.json`. The lockfile pins the exact version — that is its job. Do not use `--save-exact` as a default.

**Before adding any dependency, ask:**
1. Is this already provided by the runtime, standard library, or an existing dependency?
2. Is this dependency actively maintained?
3. What is its size impact? Use `pnpm why` to understand the dependency tree.
4. Can this be a `devDependency` instead?

Never add a dependency to solve a problem that can be solved with 5–10 lines of code. Never add a dependency for a single utility function (no `lodash` for `_.isEqual`, no `left-pad` equivalents).

---

## Scripts convention

Every project has a consistent set of scripts in `package.json`:

```json
{
  "scripts": {
    "build": "...",
    "dev": "...",
    "start": "node dist/index.js",
    "test": "vitest",
    "test:run": "vitest run --watch=false",
    "lint": "eslint .",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "typecheck": "tsc --noEmit"
  }
}
```

`test` runs in watch mode. `test:run` runs once (for CI). Always have a `typecheck` script separate from `build` so types can be verified without emitting output.

---

## Testing

Use **Vitest** for all unit and integration tests across all application types. Do not use Jest. Vitest is faster, has native ESM support, and has a compatible API.

```
pnpm add -D vitest @vitest/coverage-v8
```

`vitest.config.ts`:
```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
})
```

For React component testing, add `@vitest/browser` or use `vitest` with `jsdom` and `@testing-library/react`:
```
pnpm add -D @testing-library/react @testing-library/user-event jsdom
```

---

## Per application type

### React SPA

**Bundler: Vite**

```
pnpm create vite@latest my-app -- --template react-ts
```

Key Vite conventions:
- Environment variables are prefixed with `VITE_` to be exposed to the client
- Never put secrets in `VITE_` prefixed variables — they are bundled into the client
- Use `vite.config.ts`, not `.js`
- Path aliases go in both `vite.config.ts` and `tsconfig.json`

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': '/src' },
  },
})
```

Source structure:
```
src/
  components/     # Shared/reusable components
  features/       # Feature-scoped components, hooks, utils
  hooks/          # Shared custom hooks
  lib/            # Third-party wrappers and utilities
  pages/          # Route-level components
  types/          # Shared TypeScript types
  main.tsx        # Entry point
```

**API type generation**

The frontend must never hand-write types for API requests or responses. Types are generated from the backend's OpenAPI spec using `openapi-typescript` and consumed via `openapi-fetch`.

Install:
```
pnpm add openapi-fetch
pnpm add -D openapi-typescript
```

Add a generation script to `package.json`:
```json
"generate:api": "openapi-typescript ../../openapi.yaml -o src/lib/api/schema.d.ts"
```

Adjust the path to wherever the OpenAPI spec lives in the monorepo. Use `openapi-fetch` with the generated schema for all API calls:

```ts
// src/lib/api/client.ts
import createClient from 'openapi-fetch'
import type { paths } from './schema.d.ts'

export const apiClient = createClient<paths>({ baseUrl: import.meta.env.VITE_API_BASE_URL })
```

```ts
// Usage — fully type-safe request and response
const { data, error } = await apiClient.GET('/users/{id}', {
  params: { path: { id: userId } },
})
```

Rules:
- Run `pnpm generate:api` whenever the OpenAPI spec changes. Never edit `schema.d.ts` by hand — it is a generated file.
- Add `src/lib/api/schema.d.ts` to `.prettierignore` and `.eslintignore`.
- All API calls in the frontend go through the typed client. No raw `fetch` calls to backend endpoints.
- If `VITE_API_BASE_URL` is not set, the client should default to the local dev server URL.

---

### Next.js / SSR

Use the App Router. Do not use the Pages Router for new projects.

```
pnpm dlx create-next-app@latest my-app --typescript --eslint --app --src-dir --import-alias "@/*"
```

Key conventions:
- Server Components are the default — only add `'use client'` when you need interactivity, browser APIs, or React hooks
- Never fetch data in a Client Component that could be fetched in a Server Component
- Co-locate route-specific components inside the `app/` directory. Shared components go in `src/components/`
- Use `next/font` for fonts. Never load fonts from a CDN in `<head>`
- Environment variables without `NEXT_PUBLIC_` prefix are server-only. Never expose server secrets with `NEXT_PUBLIC_`

Source structure:
```
src/
  app/            # App Router routes and layouts
  components/     # Shared UI components
  features/       # Feature-scoped logic
  lib/            # Utilities and third-party wrappers
  types/          # Shared TypeScript types
```

---

### REST API (Express / Fastify / Hono)

**No bundler.** Compile with `tsc` directly. Set `"module": "NodeNext"` and `"moduleResolution": "NodeNext"` in `tsconfig.json`.

**Framework preference order:** Hono > Fastify > Express.
- Hono: lightweight, modern, excellent TypeScript support, works on edge runtimes too
- Fastify: high performance, good plugin ecosystem, more opinionated
- Express: only if maintaining an existing codebase or the team is already deeply familiar

Structure:
```
src/
  routes/         # Route handlers grouped by resource
  middleware/     # Express/Fastify middleware
  services/       # Business logic (injectable)
  repositories/   # Data access layer (injectable)
  lib/            # Utilities, third-party wrappers
  types/          # Shared TypeScript types
  app.ts          # App setup (no listen() call — for testing)
  server.ts       # Entry point (calls app.listen())
```

Keep `app.ts` and `server.ts` separate. `app.ts` exports the configured app without starting it — this makes the app importable in tests without binding a port.

All dependencies (database client, config, external services) are injected into routes and services. Nothing is imported and used directly inside a handler.

Use `zod` for request validation at every route boundary. Never trust `req.body`, `req.params`, or `req.query` without parsing through a schema first.

```ts
import { z } from 'zod'

const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(1).max(100),
})

app.post('/users', async (req, res) => {
  const body = CreateUserSchema.parse(req.body) // throws ZodError on invalid input
  // ...
})
```

---

### CLI tools

**Bundler: tsup**

```
pnpm add -D tsup
```

`tsup.config.ts`:
```ts
import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm'],
  target: 'node20',
  clean: true,
  dts: true,
})
```

Add a shebang to the entry file and mark it as executable:
```ts
#!/usr/bin/env node
```

Set `"bin"` in `package.json`:
```json
{
  "bin": {
    "my-cli": "./dist/index.js"
  }
}
```

Use **commander** or **citty** for argument parsing. Do not build your own argument parser.

Keep CLI entry point thin — parse arguments, then delegate to injectable service functions that can be unit tested without spawning a process.

---

## Environment variables

Use `zod` to validate environment variables at startup. Never scatter `process.env.SOMETHING` calls throughout the codebase. Define all env vars in one place and export a validated config object.

```ts
// src/lib/env.ts
import { z } from 'zod'

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
})

export const env = EnvSchema.parse(process.env)
```

Import `env` from this module everywhere. If a required variable is missing, the app fails at startup with a clear error — not at runtime when the variable is first used.

Use `.env` for local development, `.env.example` (committed, no real values) as documentation, and `.env.test` for test-specific overrides. Never commit `.env`.