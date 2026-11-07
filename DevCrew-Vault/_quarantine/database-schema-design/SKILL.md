---
name: database-schema-design
description: PostgreSQL schema design principles using Prisma. Load this skill when designing or modifying database schemas, writing migrations, or modelling data relationships. Covers naming, normalisation, indexing, constraints, and Prisma-specific conventions.
license: MIT
compatibility: opencode
---

## Philosophy

The schema is the foundation. A poor schema creates problems that no amount of application code can fully fix. Take time to model data correctly upfront. Changing a schema after data is in production is expensive — design with that cost in mind.

The schema should reflect the domain, not the application's current UI or API shape. Model what is true about the business, not what one screen happens to need.

## Naming conventions

Use `snake_case` for all table and column names. Prisma maps these to `camelCase` in the application layer — do not fight this mapping.

Tables are named in the singular: `user`, `order`, `product`. Not `users`, `orders`, `products`. Prisma generates the plural for relation fields automatically.

Primary keys are always named `id`.

Foreign keys are named `{relation_name}_id`: `user_id`, `order_id`, `product_id`.

Timestamp columns are always named `created_at` and `updated_at`. Every table has both. Use `@default(now())` and `@updatedAt` in Prisma schema.

Boolean columns are prefixed with `is_` or `has_`: `is_active`, `is_deleted`, `has_verified_email`.

```prisma
model User {
  id                String    @id @default(cuid())
  email             String    @unique
  is_active         Boolean   @default(true)
  has_verified_email Boolean  @default(false)
  created_at        DateTime  @default(now())
  updated_at        DateTime  @updatedAt
}
```

## Primary keys

Use `cuid()` or `uuid()` for primary keys — never auto-incrementing integers for externally exposed resources. Sequential integer IDs leak information (record count, creation order) and are trivial to enumerate.

Use `cuid()` as the default. Use `uuid()` when interoperability with external systems requires UUID format.

```prisma
id String @id @default(cuid())
```

## Normalisation

Normalise to third normal form by default. Denormalise deliberately and document why.

Do not store derived data unless there is a measured performance requirement. A column that can be computed from other columns is a source of inconsistency.

Do not store comma-separated values or JSON arrays where a relation table is appropriate. If you need to query into it, it should be a proper relation.

```prisma
// Bad — cannot query or constrain tags
model Post {
  tags String // "typescript,react,testing"
}

// Good
model Post {
  tags PostTag[]
}

model PostTag {
  id      String @id @default(cuid())
  post    Post   @relation(fields: [post_id], references: [id])
  post_id String
  tag     String
}
```

## Relationships

Define all foreign key constraints explicitly. Prisma enforces these at the schema level and generates them in migrations.

Choose cascade behaviour deliberately:

- `onDelete: Cascade` — use when child records have no meaning without the parent (e.g. order items when an order is deleted)
- `onDelete: Restrict` — use when deleting a parent with children should be an error (e.g. deleting a user with active orders)
- `onDelete: SetNull` — use when the child can exist without the parent (e.g. a post whose author was deleted)

Document the chosen cascade behaviour with a comment when it is not obvious.

Many-to-many relationships use an explicit join table with its own `id`, `created_at`, and any relationship-specific metadata. Do not use Prisma's implicit many-to-many unless the relationship has no metadata and will never need any.

```prisma
// Explicit join table — preferred
model UserRole {
  id         String   @id @default(cuid())
  user       User     @relation(fields: [user_id], references: [id])
  user_id    String
  role       Role     @relation(fields: [role_id], references: [id])
  role_id    String
  granted_at DateTime @default(now())
  granted_by String

  @@unique([user_id, role_id])
}
```

## Constraints

Use database constraints to enforce invariants — do not rely solely on application-layer validation.

- `@unique` for fields that must be unique
- `@@unique([a, b])` for composite uniqueness
- `@default` for fields with sensible defaults
- Enum types for fields with a fixed set of valid values

```prisma
enum OrderStatus {
  PENDING
  CONFIRMED
  SHIPPED
  DELIVERED
  CANCELLED
}

model Order {
  status OrderStatus @default(PENDING)
}
```

Use Prisma's `@@check` (via raw SQL in migrations) for invariants that cannot be expressed in the Prisma schema directly, such as `end_date > start_date`.

## Indexing

Index foreign key columns. Prisma does not do this automatically.

Index columns that appear in `WHERE` clauses in common queries. Index columns used in `ORDER BY` for large tables.

Use composite indexes when queries filter on multiple columns together. Column order in a composite index matters — put the most selective column first.

```prisma
model Order {
  user_id    String
  status     OrderStatus
  created_at DateTime

  @@index([user_id])
  @@index([status, created_at])
}
```

Do not over-index. Every index slows down writes. Add indexes when you have a query that needs them, not speculatively.

## Soft deletes

Use soft deletes sparingly and deliberately. They add complexity to every query (every `WHERE` clause must exclude deleted records) and make constraints harder to reason about.

When you do use soft deletes:

```prisma
model User {
  deleted_at DateTime?
}
```

Consider a partial unique index in a raw migration to allow re-use of unique fields (e.g. email) after soft deletion:

```sql
CREATE UNIQUE INDEX user_email_active_unique
ON "user" (email)
WHERE deleted_at IS NULL;
```

## Migrations

Every schema change is a migration. Never modify the database directly in production.

Migrations are irreversible by default — write them as if you cannot roll back. For destructive changes (dropping a column, changing a type), use a multi-step process:
1. Add the new column / structure
2. Deploy application code that writes to both old and new
3. Backfill the new column
4. Deploy application code that reads from the new column only
5. Drop the old column in a subsequent migration

Never rename a column in a single migration with live traffic. Add the new column, migrate data, drop the old column across multiple deployments.

Keep migrations small and focused. One concern per migration.

## Prisma-specific conventions

Define all relations explicitly with `@relation` naming when there are multiple relations between the same two models.

Use `select` in Prisma queries — never return entire records when only a subset of fields is needed. This is especially important for tables with large text or JSON columns.

```typescript
// Bad — fetches everything including large fields
const user = await prisma.user.findUnique({ where: { id } })

// Good
const user = await prisma.user.findUnique({
  where: { id },
  select: { id: true, email: true, name: true }
})
```

Use Prisma's `$transaction` for any operation that must be atomic. Never perform multi-step mutations outside a transaction.

```typescript
await prisma.$transaction([
  prisma.order.update({ where: { id }, data: { status: 'CONFIRMED' } }),
  prisma.inventory.decrement({ where: { product_id }, data: { quantity: 1 } }),
])
```