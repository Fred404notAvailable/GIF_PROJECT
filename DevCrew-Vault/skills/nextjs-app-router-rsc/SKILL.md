---
name: nextjs-app-router-rsc
description: >
  Guides building Next.js 14+ App Router applications using React Server
  Components (RSC). Use when starting a new Next.js project with App Router,
  migrating from Pages Router, adding RSC to an existing app, or optimizing
  bundle size by moving rendering server-side. Invoke when you need to implement
  streaming, Server Actions, nested layouts, or the metadata API. Do not use
  for purely static sites (prefer static export) or when the Pages Router
  migration is not justified.
license: MIT
compatibility:
  - claude-3-5-sonnet
  - gpt-4o
metadata:
  origin: authored
  review_status: needs-human-review
allowed-tools:
  - read_file
  - write_file
  - run_command
---

# Next.js 14+ App Router & React Server Components Guide

## When to Use / When Not to Use

### Use When
- Starting a **new Next.js project** that will use the App Router (`app/` directory).
- **Migrating from Pages Router** (`pages/`) to App Router.
- Adding **React Server Components** to an existing Next.js app to reduce client bundle size.
- Implementing **streaming UI** with Suspense boundaries for progressive loading.
- Using **Server Actions** for form mutations without a separate API route.
- Leveraging the **Metadata API** for SEO-critical pages.

### Do NOT Use When
- The site is **fully static** with no dynamic data — use Next.js static export (`output: 'export'`).
- The team is on a **Pages Router project** and migration is not justified by complexity/timeline.
- You only need a **single-page application** with no SSR requirements — Vite + React may be simpler.
- The project must support **React < 18** (RSC requires React 18+).

---

## Procedure

### 1. Bootstrap the Project

```bash
npx create-next-app@latest my-app \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"
cd my-app
```

The critical flag is `--app`, which scaffolds the `app/` directory (App Router).

### 2. Understand `app/` Directory Conventions

| File | Purpose |
|---|---|
| `layout.tsx` | Persistent UI wrapper for a segment and its children; never re-renders on navigation |
| `page.tsx` | UI unique to a route; makes the route publicly accessible |
| `loading.tsx` | Instant loading state shown while the segment streams in (wraps page in Suspense automatically) |
| `error.tsx` | Error boundary for a segment (`'use client'` required) |
| `not-found.tsx` | Rendered when `notFound()` is thrown within the segment |
| `route.ts` | API route handler (replaces `pages/api/`) |
| `template.tsx` | Like layout, but re-renders on navigation (creates new instance) |

**Nesting example:**
```
app/
  layout.tsx          ← root layout (required, wraps everything)
  page.tsx            ← "/"
  dashboard/
    layout.tsx        ← dashboard shell (sidebar, nav)
    page.tsx          ← "/dashboard"
    settings/
      page.tsx        ← "/dashboard/settings"
      loading.tsx     ← streaming skeleton for settings
      error.tsx       ← error boundary for settings
```

### 3. Server vs. Client Component Decision Tree

```
Does the component need:
  ├─ useState / useReducer / useContext?         → Client Component ('use client')
  ├─ useEffect / lifecycle methods?              → Client Component ('use client')
  ├─ Browser APIs (window, document, localStorage)? → Client Component ('use client')
  ├─ Event handlers (onClick, onChange)?         → Client Component ('use client')
  ├─ 3rd-party library that uses hooks/browser APIs? → Client Component ('use client')
  └─ None of the above?                          → Server Component (default, no directive needed)
```

> **Key insight:** Keep the `'use client'` boundary as **deep in the tree as possible**. A server component can import and render a client component, but a client component cannot import a server component (it can receive one as `children`).

### 4. Data Fetching in Server Components

Server components can be `async` and `await` data directly:

```typescript
// app/products/page.tsx  — Server Component (default)
import { db } from '@/lib/db';

export default async function ProductsPage() {
  // This runs on the server — DB access is fine here
  const products = await db.product.findMany({ orderBy: { name: 'asc' } });

  return (
    <ul>
      {products.map(p => <li key={p.id}>{p.name}</li>)}
    </ul>
  );
}
```

**Fetch caching options:**

| Option | Behavior |
|---|---|
| `fetch(url)` | Cached indefinitely (default, `force-cache`) |
| `fetch(url, { cache: 'no-store' })` | Always fresh — equivalent to SSR |
| `fetch(url, { next: { revalidate: 60 } })` | ISR — revalidate every 60 seconds |
| `fetch(url, { next: { tags: ['products'] } })` | On-demand revalidation via `revalidateTag('products')` |

### 5. Placing `'use client'` Boundaries

**Correct pattern — push client boundary down:**
```typescript
// app/products/page.tsx  — Server Component
import ProductList from './ProductList';
import FilterBar from './FilterBar'; // Client Component

export default async function ProductsPage() {
  const products = await fetchProducts(); // server-side fetch
  return (
    <>
      <FilterBar />          {/* client component */}
      <ProductList products={products} />  {/* server component receiving data as props */}
    </>
  );
}
```

**Wrong pattern — `'use client'` too high:**
```typescript
'use client'; // ❌ Now the entire page is a client bundle
import ProductList from './ProductList';
// fetchProducts() can no longer be async/await on the server
```

### 6. Streaming with Suspense

Wrap slow data fetches in `<Suspense>` to stream UI progressively:

```typescript
// app/dashboard/page.tsx
import { Suspense } from 'react';
import RecentOrders from './RecentOrders';  // slow DB query
import QuickStats from './QuickStats';      // fast query

export default function DashboardPage() {
  return (
    <main>
      <QuickStats />  {/* renders immediately */}
      <Suspense fallback={<OrdersSkeleton />}>
        <RecentOrders />  {/* streams in when ready */}
      </Suspense>
    </main>
  );
}
```

Alternatively, create `loading.tsx` in the route folder for automatic Suspense wrapping.

### 7. Server Actions for Mutations

Server Actions let you call server-side functions directly from forms or client components — no separate API route needed:

```typescript
// app/cart/actions.ts
'use server';

import { revalidateTag } from 'next/cache';

export async function addToCart(productId: string) {
  await db.cart.addItem(productId);
  revalidateTag('cart'); // invalidate cached cart data
}
```

```typescript
// app/products/AddToCartButton.tsx
'use client';

import { addToCart } from '@/app/cart/actions';

export function AddToCartButton({ productId }: { productId: string }) {
  return (
    <form action={addToCart.bind(null, productId)}>
      <button type="submit">Add to Cart</button>
    </form>
  );
}
```

### 8. Route Handlers (API Routes)

```typescript
// app/api/products/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  const products = await fetchProducts();
  return NextResponse.json(products);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const product = await createProduct(body);
  return NextResponse.json(product, { status: 201 });
}
```

### 9. Metadata API for SEO

```typescript
// app/products/[id]/page.tsx
import type { Metadata } from 'next';

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const product = await fetchProduct(params.id);
  return {
    title: product.name,
    description: product.description,
    openGraph: { images: [product.imageUrl] },
  };
}
```

### 10. Environment Variables Convention

| Variable prefix | Available in |
|---|---|
| `NEXT_PUBLIC_*` | Browser + Server |
| (no prefix) | Server only — never exposed to client |

Always put secrets (DB URLs, API keys) without `NEXT_PUBLIC_`.

---

## Checklist

- [ ] `layout.tsx` exists at root with `<html>` and `<body>` tags
- [ ] No `useState` / `useEffect` in Server Components (no `'use client'` directive on them)
- [ ] `'use client'` boundaries placed as deep in the component tree as possible
- [ ] Server-only code (DB, secrets) never imported into Client Components
- [ ] Caching strategy defined per `fetch()` call or route segment
- [ ] Slow data fetches wrapped in `<Suspense>` with a `fallback`
- [ ] `loading.tsx` created for routes with async data
- [ ] `error.tsx` created for routes that may throw (and marked `'use client'`)
- [ ] Server Actions marked `'use server'` at the top of the file or function
- [ ] No secrets in `NEXT_PUBLIC_*` env vars
- [ ] `generateMetadata` exported from dynamic pages for SEO
- [ ] No waterfall fetching — parallel fetches with `Promise.all` where possible

---

## Common Pitfalls

| Pitfall | Example | Fix |
|---|---|---|
| **`use client` on everything** | Adding `'use client'` to page.tsx "just in case" | Only add when hooks or browser APIs are needed |
| **Server-only imports in Client Components** | Importing `db` from a client component | Use Server Actions or API routes for data mutation from client |
| **Waterfall fetching** | `await fetchUser()` then `await fetchPosts(userId)` sequentially | Use `Promise.all([fetchUser(), fetchPosts()])` or parallel `fetch` calls |
| **Missing Suspense** | Async server component with no `loading.tsx` or `<Suspense>` | Wrap in `<Suspense fallback={...}>` or add `loading.tsx` |
| **`params` not awaited** | `params.id` accessed before awaiting in Next.js 15 | `const { id } = await params` in Next.js 15+ |
| **Mutation without revalidation** | Server Action saves data but old cache serves stale UI | Call `revalidatePath()` or `revalidateTag()` after mutation |

---

## Worked Example: Product Listing with Filter and Add-to-Cart

**Goal:** Server-rendered product list, client-side filter, Server Action for add-to-cart.

```
app/
  products/
    page.tsx           ← async server component, fetches all products
    FilterBar.tsx      ← 'use client' — manages filter state
    ProductCard.tsx    ← server component — renders a single product
    AddToCartButton.tsx ← 'use client' — calls Server Action
    actions.ts         ← 'use server' — addToCart Server Action
    loading.tsx        ← skeleton while products load
```

```typescript
// app/products/page.tsx
import { Suspense } from 'react';
import FilterBar from './FilterBar';
import ProductCard from './ProductCard';
import { fetchProducts } from '@/lib/products';

export default async function ProductsPage() {
  const products = await fetchProducts();

  return (
    <div>
      <FilterBar />
      <Suspense fallback={<p>Loading products...</p>}>
        <div className="grid grid-cols-3 gap-4">
          {products.map(p => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      </Suspense>
    </div>
  );
}
```

See `references/deep-dive.md` for detailed reference material.
