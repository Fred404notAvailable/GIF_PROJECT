# Svelte 5 and SvelteKit Development Skill

A Kiro Agent Skill for building reactive web applications with Svelte 5 and SvelteKit, featuring runes, component composition, state management, and type-safe client-server communication.

## Overview

This skill provides comprehensive guidance for developing modern web applications with Svelte 5 and SvelteKit. It covers the new runes system, migration from Svelte 4, reactive state management, component patterns, forms with validation, animations, and remote functions for seamless client-server communication.

## When to Use

This skill activates when you need to:

- Write Svelte 5 components using runes ($state, $derived, $effect, $props)
- Migrate existing Svelte 4 code to Svelte 5
- Implement reactive state and derived values
- Build forms with Shadcn components and validation
- Manage complex state with classes and state machines
- Use remote functions for type-safe API calls
- Work with animations, transitions, and third-party libraries
- Optimize performance and implement best practices

## What's Included

### SKILL.md
The main skill file with core runes, migration best practices, state management patterns, remote functions, and key conventions.

### references/
Complete documentation covering all aspects of Svelte 5 and SvelteKit:
- `overview.md` - Runes, migration guide, UI/styling, project structure
- `reactivity_deep_dive.md` - How reactivity works, signals, derived state, effects
- `templating_and_components.md` - Template logic, data binding, snippets, context API
- `advanced_state_management.md` - State in functions/classes, avoiding effects
- `animations_and_integrations.md` - Transitions, FLIP animations, third-party libraries
- `remote_functions.md` - Complete guide to query, form, command, and prerender

### assets/
Example templates ready to use in your project:
- `counter.svelte.example.ts` - State management with classes
- `component.example.svelte` - Complete Svelte 5 component with runes
- `remote-functions.example.ts` - All remote function types with validation
- `form.example.svelte` - Form with Shadcn components and Zod validation

## Quick Start

1. Create a new SvelteKit project:
   ```bash
   pnpm create svelte@latest my-app
   cd my-app
   pnpm install
   ```

2. Start using Svelte 5 runes in your components:
   ```svelte
   <script lang="ts">
     let count = $state(0);
     let doubled = $derived(count * 2);
   </script>
   
   <button onclick={() => count++}>
     Count: {count} (doubled: {doubled})
   </button>
   ```

3. For remote functions, enable the experimental feature:
   ```js
   // svelte.config.js
   export default {
     kit: {
       experimental: {
         remoteFunctions: true
       }
     }
   };
   ```

## Core Concepts

### Svelte 5 Runes

Runes are the new way to declare reactive state in Svelte 5:

- `$state`: Reactive state variables
- `$derived`: Computed values (replaces `$:`)
- `$effect`: Side effects (use sparingly)
- `$props`: Component props (replaces `export let`)
- `$bindable`: Two-way bindable props
- `$inspect`: Debug reactive state

### Migration from Svelte 4

Key changes when migrating:

- Replace `export let` with `$props()`
- Replace `$:` reactive statements with `$derived`
- Replace `on:click` with `onclick`
- Use TypeScript interfaces for props
- Update HTML element references with generic typing

### State Management

For complex state, use classes in `.svelte.ts` files:

```typescript
class Counter {
  count = $state(0);
  
  increment = () => {
    this.count++;
  }
}

export const counter = new Counter();
```

### Remote Functions

Type-safe client-server communication:

- `query`: Read data from server
- `form`: Handle form submissions
- `command`: Programmatic writes
- `prerender`: Static data at build time

All with automatic TypeScript types and validation.

## Key Features

### Reactivity

- Signals-based reactivity system
- Deep reactivity with proxies
- Lazy-evaluated derived values
- Automatic dependency tracking

### Component Composition

- Snippets for reusable markup
- Context API for prop drilling
- Module context for shared state
- Special Svelte elements

### Forms

- Shadcn components for UI
- Zod validation schemas
- Progressive enhancement
- Field-level reactivity with proxies

### Performance

- Compile-time optimizations
- Minimal runtime overhead
- Efficient updates with signals
- SSR and SSG support

### Enhanced Images

- Automatic format generation (avif, webp)
- Responsive sizes
- Build-time optimization
- Simple `<enhanced:img>` syntax

## Best Practices

1. **Use runes correctly**: `$state` for reactive values, `$derived` for computed values
2. **Avoid effects**: Use derived state instead of effects for state synchronization
3. **Type your props**: Always use TypeScript interfaces with `$props`
4. **Validate remote functions**: Use Zod or Valibot for argument validation
5. **Progressive enhancement**: Use `form` over `command` when possible
6. **Optimize images**: Always use `?enhanced` for image imports
7. **Use pnpm**: Preferred package manager for Svelte projects

## Common Patterns

### Reactive State

```typescript
let count = $state(0);
let doubled = $derived(count * 2);
```

### Component Props

```typescript
interface Props {
  title: string;
  count?: number;
}
let { title, count = 0 }: Props = $props();
```

### Remote Query

```typescript
// data.remote.ts
export const getPosts = query(async () => {
  return await db.sql`SELECT * FROM posts`;
});

// +page.svelte
{#each await getPosts() as post}
  <article>{post.title}</article>
{/each}
```

### Form Submission

```svelte
<form {...createPost}>
  <input name="title" />
  <button>Submit</button>
</form>
```

## Official Resources

- [Svelte 5 Documentation](https://svelte.dev/docs/svelte)
- [SvelteKit Documentation](https://svelte.dev/docs/kit)
- [Svelte 5 Migration Guide](https://svelte.dev/docs/svelte/v5-migration-guide)
- [Shadcn Svelte](https://shadcn-svelte.com)
- [Tailwind CSS](https://tailwindcss.com)

## License

This skill is provided as-is for use with Kiro AI assistant.
