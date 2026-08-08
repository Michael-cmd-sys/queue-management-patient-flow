---
name: octane-tailwind
description: Scaffold, style, build, and verify a production-grade OctaneJS project with Tailwind CSS v4
---

# OctaneJS + Tailwind CSS — A Complete Project Setup

Octane is React's programming model, compiled ahead-of-time from `.tsrx`
(template syntax) or `.tsx` (JSX). This skill produces a **complete, verified
project scaffold** that wires Octane to Tailwind CSS v4, the Vite build
pipeline, and a healthcare-grade design system. Use it whenever you are
spinning up a new Octane app or re-scaffolding one.

> **Status:** Octane is alpha software. Pin versions and validate with
> `tsrx-tsc` + `vite build` before every commit.

## 1. Prerequisites

- **Node.js 22.22.2+** (the project requires 22.22.2 or newer).
- **npm 11+** (or pnpm/yarn — npm is the default below).
- Octane is React-shaped but uses its own compiler; do **not** install
  `react`/`react-dom` — `octane` ships its own runtime.

## 2. Dependency manifest

```jsonc
// package.json
{
  "name": "patient-queue-dashboard",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "typecheck": "tsrx-tsc --noEmit -p tsconfig.json"
  },
  "dependencies": {
    "@octanejs/vite-plugin": "^0.1.30",
    "octane": "^0.1.30"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.1.0",
    "@tsrx/prettier-plugin": "^0.3.118",
    "@tsrx/typescript-plugin": "^0.3.118",
    "tailwindcss": "^4.1.0",
    "typescript": "~5.9.3", // @tsrx/typescript-plugin peer: ^5.9.3
    "vite": "^8.2.1"
  }
}
```

Install order matters: install the plugin **before** running the Vite build so
`octane()` and `tailwindcss()` resolve from `node_modules`.

```bash
npm install
```

## 3. TypeScript config

Octane needs two things: a JSX import source pointing at `octane`, and
permission to import `.tsrx` files with their extensions. The
`@tsrx/typescript-plugin` gives editors syntax awareness, but the compiler
itself (installed by the `vite-plugin`) does the real work.

```jsonc
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "moduleSuffixes": { "/": ["", ".ts", ".tsx", ".tsrx", ".js", ".jsx"] },
    "allowImportingTsExtensions": true,
    "strict": true,
    "jsx": "react-jsx",
    "jsxImportSource": "octane",
    "types": ["vite/client"],
    "lib": ["DOM", "ES2022"],
    "skipLibCheck": true,
    "esModuleInterop": true,
    "noEmit": true,
    "isolatedModules": true,
    "resolveJsonModule": true
  },
  "include": ["src", "vite.config.ts"],
  "exclude": ["node_modules", "dist"]
}
```

Key points:

- `jsxImportSource: "octane"` routes JSX to Octane's runtime.
- `allowImportingTsExtensions + moduleSuffixes` lets `import "./App.tsrx"`
  resolve (TS does **not** auto-resolve `.tsrx` otherwise — always import
  with the explicit `.tsrx` extension).
- `tsrx-tsc` (from `@tsrx/typescript-plugin`) is the typecheck entrypoint,
  **not** plain `tsc`.

## 4. Vite + plugin config

The Vite plugin composes with Tailwind's Vite plugin. List `octane()` first so
its compiler runs before CSS tooling inspects the graph.

```ts
// vite.config.ts
import { defineConfig } from "vite";
import { octane } from "@octanejs/vite-plugin";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [octane(), tailwindcss()],
  build: { target: "esnext" },
});
```

Optional `octane.config.ts` (routing, SSR, deferred hydration). Omit it for a
client-only SPA — the plugin compiles Octane source and leaves Vite's default
behavior intact.

## 5. HTML entry

Use an id the rest of the project owns. Octane does **not** require
`type="module"`-linked CSS because styles travel through the JS graph (see 6.3).

```html
<!-- index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Patient Queue Flow Analytics</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

## 6. Tailwind CSS v4 — the Octane-aware way

### 6.1 The CSS entry (`src/styles.css`)

Import Tailwind, declare the design system in a `@theme` block, and **scan the
`.tsrx` files** with `@source`. `.tsrx` is not in Vite's default source set,
so explicit `@source` is mandatory or utility classes inside components will
be stripped.

```css
@import "tailwindcss";

@theme {
  /* Typography */
  --font-family-body: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-family-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  --font-size-base: 1rem;
  --font-weight-regular: 400;
  --font-weight-semibold: 600;

  /* Clinical + medical accent palette (cool greys, emerald) */
  --color-surface-900: hsl(220 26% 10%);
  --color-surface-800: hsl(218 20% 18%);
  --color-surface-700: hsl(217 15% 30%);
  --color-surface-500: hsl(215 11% 50%);
  --color-surface-200: hsl(214 15% 90%);
  --color-primary-600: hsl(156 58% 54%);  /* medical emerald */
  --color-success: hsl(155 55% 45%);
  --color-danger: hsl(0 85% 55%);
}

@source "./src/**/*.{ts,tsrx,html}";
@source "./index.html";

@layer base {
  html { font-family: var(--font-family-body); }
  body { @apply bg-surface-900 text-surface-200 antialiased; margin: 0; }
}

@layer components {
  /* reusable component-level primitives */
}

@layer utilities {
  /* project-specific utilities that compose Tailwind primitives */
}
```

### 6.2 Import the stylesheet in the client entry

```ts
// src/main.ts
import "./styles.css";
import { createRoot } from "octane";
import { App } from "./App.tsrx";

const container = document.getElementById("app");
if (!container) throw new Error("Missing #app element");
const root = createRoot(container);
root.render(App, { title: "Patient Queue Flow Analytics" });
```

### 6.3 Gotchas verified against Octane 0.1.30

- The `@tailwindcss/vite` plugin and `@octanejs/vite-plugin` both transform the
  build; list `octane()` first.
- Pass `target: "esnext"` to Vite's build so the emitter doesn't down-level
  the Octane-compiled output.

## 7. Octane `.tsrx` idioms — write good components

### 7.1 Component shape

```tsrx
// src/App.tsrx
import { useState } from "octane";

interface Props {
  title: string;
}

export function App(props: Props) @{
  const [count, setCount] = useState(0);

  <main>
    <h1>{props.title}</h1>
    <p>{"Button pressed " + count + " times"}</p>
    <button onClick={() => setCount((c) => c + 1)}>{"Add one"}</button>
  </main>
}
```

Rules:

- `@{ ... }` is shorthand for `return <final-jsx>`.
- **Text holes render `string` fast paths.** For non-string values, build a
  string: `'Items: ' + count` or a template literal — do **not** use
  `value as string`, which is a `TS2352` error (number→string is not an allowed
  cast). Bare `{number}` also typechecks because Octane's children type is
  `unknown`, but the string form is explicit and avoids surprising SSR output.
- Always import `.tsrx` with the **explicit extension**.
- `children: unknown` is the typed children slot — name it `props.children`.

### 7.2 Lists, conditions, and refs (idiomatic, not React-shaped)

```tsrx
import { useRef, useEffect, useState } from "octane";

export function RoiCanvas() @{
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [points, setPoints] = useState<Array<{ x: number; y: number }>>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    // ...draw loop...
    return () => { /* cleanup */ };
  }, [points]);

  <canvas ref={canvasRef} width={640} height={400} class="roi-canvas" />
}
```

- **Refs attach directly**: `ref={myRef}` (there is **no** `forwardRef`).
- **Event names are native**: `onInput` (not `onChange`) for text fields,
  `onClick`, `onSubmit`, `onFocus`.
- **Lists** use `@for (const x of items; key x.id) { ... } @empty { ... }`.
- **Conditions** use `@if (cond) { ... } @else { ... }`.
- **Effects** infer dependencies from referenced props/state; `[]` = mount only;
  `null` = every render. A bare body (no second arg) infers deps automatically.

### 7.3 Async / loading / errors

```tsrx
import { Suspense, use, useSyncExternalStore } from "octane";

function AsyncContent(props: { data: Promise<User> }) @{
  const user = use(props.data); // suspends until resolved
  <h2>{user.name}</h2>
}

export function Page(props) @{
  <ErrorBoundary fallback={<p>{"Could not load user."}</p>}>
    <Suspense fallback={<p>{"Loading…"}</p>}>
      <AsyncContent data={props.data} />
    </Suspense>
  </ErrorBoundary>
}
```

## 8. Design-system checklist (apply before shipping)

Taken from *Refactoring UI* — apply mechanically:

1. **Personality**: calm + professional, clinical. Cool-tinted greys, low
   saturation, sharp medical accent (emerald) for "go / in-queue".
2. **Scales** (define as tokens in `@theme`):
   - Spacing: Tailwind's own scale (4, 8, 12, 16, 24, 32, 48…).
   - Type: 12 / 14 / 16 / 18 / 20 / 24 / 30 / 36 px.
   - Font weights: 400 regular, 600/700 emphasis.
   - Radii: sm(4) / md(8) / lg(12).
3. **Hierarchy**: one primary action per region (`btn-primary`), rest
   `btn-ghost` or text. Emphasize by de-emphasizing the surroundings.
4. **Contrast**: body text ≥ 4.5:1 against background. Prefer dark-on-light
   cards over white-on-emerald.
5. **Accessibility**: `aria-label`, `role="status"`, `aria-live="polite"` for
   live telemetry, keyboard-focusable controls. Don't rely on color alone
   (pair status badges with an icon or text).

## 9. Verification workflow

```bash
npm run typecheck   # tsrx-tsc — catches .tsrx typing + missing extensions
npm run build       # vite build — end-to-end compile, catches Tailwind class stripping
npm run dev         # vite dev — HMR for iteration
```

If `vite build` drops a Tailwind utility that *is* present in a `.tsrx` file,
the likely cause is an incomplete `@source` glob — add the directory to
`@source` in `styles.css`. If `tsrx-tsc` reports `Cannot find module
'./Foo.tsrx'`, the import is missing its `.tsrx` extension.

## 10. Project layout (outcome of this skill)

```
dashboard/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── .prettierrc
└── src/
    ├── main.ts
    ├── App.tsrx
    ├── styles.css
    └── components/
        ├── RoiCanvas.tsrx
        └── QueueTelemetry.tsrx
```

Commit only the source; `node_modules`, `dist`, and lockfiles generated by
your local package manager are gitignored (add a `.gitignore` per the root
repo conventions).
