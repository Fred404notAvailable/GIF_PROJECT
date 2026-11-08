---
name: svelte
description: Build reactive web applications with Svelte 5 and SvelteKit. Covers runes ($state, $derived, $effect, $props), component composition, reactivity patterns, state management, forms, animations, and remote functions for type-safe client-server communication.
---

# Svelte 5 and SvelteKit Development

Use this skill when building or troubleshooting Svelte 5 applications with SvelteKit.

## When to Use

Activate this skill when:
- Writing Svelte 5 components with runes
- Migrating from Svelte 4 to Svelte 5
- Implementing reactive state and derived values
- Building forms with validation
- Managing complex state with classes
- Using remote functions for client-server communication
- Working with animations and transitions
- Integrating third-party libraries

## Svelte 5 Runes

### Core Runes

- `$state`: Declare reactive state
  ```typescript
  let count = $state(0);
  let user = $state({ name: '', email: '' });
  let fileInput = $state<HTMLInputElement>();
  ```

- `$derived`: Compute derived values (replaces `$:`)
  ```typescript
  let doubled = $derived(count * 2);
  let fullName = $derived(`${user.firstName} ${user.lastName}`);
  ```

- `$effect`: Manage side effects (use sparingly)
  ```typescript
  $effect(() => {
    console.log(`Count is now ${count}`);
    return () => { /* cleanup */ };
  });
  ```

- `$props`: Declare component props (replaces `export let`)
  ```typescript
  interface Props {
    optionalProp?: number;
    requiredProp: string;
  }
  let { optionalProp = 42, requiredProp }: Props = $props();
  ```

- `$bindable`: Create two-way bindable props
  ```typescript
  let { bindableProp = $bindable() } = $props();
  ```

## Migration Best Practices

### Component Props Pattern

Always use TypeScript interfaces with `$props`:

```typescript
// ✅ Correct
interface Props {
  value: string;
  error?: ErrorType | null;
  onOptionChange?: (value: string) => void;
}
let { value, error = null, onOptionChange = () => {} }: Props = $props();

// ❌ Wrong - causes prop mismatch errors
export let value: string;
export let error: ErrorType | null = null;
```

### Event Handlers

```typescript
// ✅ Svelte 5
<button onclick={handleClick}>Click me</button>

// ❌ Svelte 4
<button on:click={handleClick}>Click me</button>
```

### HTML Element References

```typescript
// ✅ Correct
let fileInput = $state<HTMLInputElement>();
fileInput?.click();

// ❌ Wrong
let fileInput: HTMLInputElement = $state();
```

## State Management

### Classes for Complex State

```typescript
// counter.svelte.ts
class Counter {
  count = $state(0);
  
  increment = () => {
    this.count++;
  }
}

export const counter = new Counter();
```

### Avoid Effects for State Sync

```typescript
// ✅ Use derived state
let doubled = $derived(count * 2);

// ❌ Don't use effects for state sync
let doubled = $state(0);
$effect(() => { doubled = count * 2; });
```

## Remote Functions

Type-safe client-server communication:

### Query (Read Data)

```typescript
// data.remote.ts
import { query } from '$app/server';
import * as v from 'valibot';

export const getPosts = query(async () => {
  return await db.sql`SELECT * FROM posts`;
});

export const getPost = query(v.string(), async (slug) => {
  return await db.sql`SELECT * FROM posts WHERE slug = ${slug}`;
});
```

```svelte
<!-- +page.svelte -->
<script>
  import { getPosts } from './data.remote';
</script>

{#each await getPosts() as post}
  <article>{post.title}</article>
{/each}
```

### Form (Write Data)

```typescript
// data.remote.ts
import { form } from '$app/server';

export const createPost = form(async (data) => {
  const title = data.get('title');
  await db.sql`INSERT INTO posts (title) VALUES (${title})`;
  redirect(303, '/posts');
});
```

```svelte
<form {...createPost}>
  <input name="title" />
  <button>Create</button>
</form>
```

### Command (Programmatic Writes)

```typescript
// likes.remote.ts
import { command } from '$app/server';
import * as v from 'valibot';

export const addLike = command(v.string(), async (id) => {
  await db.sql`UPDATE items SET likes = likes + 1 WHERE id = ${id}`;
});
```

```svelte
<button onclick={() => addLike(item.id)}>Like</button>
```

## Forms with Shadcn

```typescript
// Define schema
const formSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

// Use in component
import * as Form from '$lib/components/ui/form';
import { formFieldProxy, superForm } from 'sveltekit-superforms';

const form = superForm(data.form, {
  validators: zodClient(formSchema)
});
const email = formFieldProxy(form, 'email');
```

```svelte
<form method="POST" use:enhance>
  <Form.Field {form} name="email">
    <Form.Control let:attrs>
      <Form.Label>Email</Form.Label>
      <Input {...attrs} bind:value={$email} />
    </Form.Control>
    <Form.FieldErrors />
  </Form.Field>
  <Form.Button>Submit</Form.Button>
</form>
```

## Enhanced Images

```typescript
// Import with ?enhanced
import heroImage from '$lib/assets/images/hero.png?enhanced';
```

```svelte
<enhanced:img
  src={heroImage}
  alt="Hero"
  class="h-64 w-full object-cover"
  sizes="(min-width: 768px) 100vw, 50vw"
/>
```

## Key Conventions

- Use `pnpm` for package management
- Embrace Svelte's simplicity
- Avoid over-engineering with effects
- Use Tailwind CSS v4 for styling
- Use Shadcn components for UI
- Implement proper TypeScript types
- Follow SvelteKit's file-based routing

## References

See `references/` folder for detailed documentation on:
- Reactivity deep dive
- Templating and components
- Advanced state management
- Animations and integrations
- Remote functions

## Official Documentation

- [Svelte 5 Migration Guide](https://svelte.dev/docs/svelte/v5-migration-guide)
- [SvelteKit Documentation](https://svelte.dev/docs/kit)
- [Shadcn Svelte](https://shadcn-svelte.com)
