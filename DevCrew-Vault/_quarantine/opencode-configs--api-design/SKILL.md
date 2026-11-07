---
name: api-design
description: REST API design principles and conventions. Load this skill when designing or implementing any REST API endpoint, resource, or response shape. Covers resource modelling, naming, versioning, error handling, and security.
license: MIT
compatibility: opencode
---

## Philosophy

A REST API is a product. Its consumers are developers, and their experience matters. A well-designed API is predictable, consistent, and unsurprising. Every decision should reduce the cognitive load on the caller.

Design the API before implementing it. Write out the resource model and endpoint shapes first. If the design feels awkward, the implementation will be worse.

## Resource modelling

Resources are nouns, not verbs. An endpoint represents a thing, not an action.

```
/users           ✓
/getUsers        ✗
/user/create     ✗
```

Use plural nouns for collections. Nest resources only when the child cannot exist without the parent and the relationship is permanent. Avoid nesting deeper than two levels — it creates brittle URLs.

```
/orders/{orderId}/items      ✓   (items belong to an order)
/users/{userId}/orders       ✓   (reasonable)
/users/{userId}/orders/{orderId}/items/{itemId}/notes    ✗   (too deep)
```

When an operation does not map cleanly to CRUD, use a sub-resource that names the action as a noun:

```
POST /payments/{id}/refund       ✓
POST /accounts/{id}/suspension   ✓
```

## HTTP methods

Use HTTP methods according to their semantics:

- `GET` — retrieve, never mutate, safe and idempotent
- `POST` — create a new resource or trigger an action
- `PUT` — replace a resource entirely, idempotent
- `PATCH` — partial update, send only the fields being changed
- `DELETE` — remove a resource, idempotent

Do not use `POST` for everything. Use `PATCH` for updates, not `PUT`, unless the client is sending a complete replacement.

## Naming conventions

Use `kebab-case` for URL path segments. Use `snake_case` for JSON field names.

```
GET /user-profiles/{id}
{ "first_name": "Jane", "last_name": "Smith" }
```

Be consistent across the entire API. If one endpoint uses `created_at`, every endpoint uses `created_at`.

## Status codes

Use the correct HTTP status code. Do not return `200` for errors.

| Scenario | Code |
|---|---|
| Successful GET, PATCH, PUT | 200 |
| Successful POST (created) | 201 |
| Successful DELETE or action with no body | 204 |
| Validation error | 400 |
| Missing or invalid auth token | 401 |
| Valid token, insufficient permissions | 403 |
| Resource not found | 404 |
| Method not allowed | 405 |
| Conflict (e.g. duplicate) | 409 |
| Unprocessable (semantic errors) | 422 |
| Rate limited | 429 |
| Server error | 500 |

Never return `200` with an `error` field in the body. The status code is the contract.

## Error responses

All error responses follow the same shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request body is invalid.",
    "details": [
      {
        "field": "email",
        "message": "Must be a valid email address."
      }
    ]
  }
}
```

- `code` is a machine-readable constant in `SCREAMING_SNAKE_CASE`. It never changes between API versions.
- `message` is a human-readable description. It may change.
- `details` is optional and used for field-level validation errors.

Never expose stack traces, internal error messages, or database errors in the response.

## Request and response design

Return only what the caller needs. Do not return entire database rows. Shape the response to the use case.

For collections, always return a wrapper object — never a bare array. This allows pagination and metadata to be added without a breaking change:

```json
{
  "data": [...],
  "pagination": {
    "total": 142,
    "page": 1,
    "per_page": 20,
    "next_cursor": "eyJpZCI6IjUwIn0="
  }
}
```

Use cursor-based pagination for large or frequently-updated collections. Use offset pagination only for small, stable datasets where jumping to a specific page is a user requirement.

For single resources:

```json
{
  "data": { ... }
}
```

Date and time fields are always ISO 8601 in UTC: `"2024-03-15T14:32:00Z"`. Never return timestamps as integers.

## Versioning

Version the API from day one. Use URL path versioning:

```
/v1/users
/v2/users
```

A new version is required when making a breaking change: removing a field, changing a field's type, changing a status code, or altering the meaning of an existing field. Adding new optional fields or new endpoints is non-breaking.

Maintain the previous version for a documented deprecation period. Include a `Deprecation` header on deprecated endpoints.

## Filtering, sorting, and searching

Use query parameters for filtering and sorting. Be explicit about what is supported — do not build a generic query engine.

```
GET /orders?status=pending&created_after=2024-01-01
GET /users?sort=created_at&order=desc
GET /products?q=wireless+headphones
```

## Security

- Authenticate every non-public endpoint. Use bearer tokens.
- Authorise at the resource level — verify the caller owns or has permission to access the specific resource, not just that they are logged in.
- Validate and sanitise all input. Never trust query params, path params, or request bodies.
- Rate limit all endpoints. Apply stricter limits to auth endpoints.
- Never include sensitive data (passwords, tokens, PII beyond what is necessary) in responses.
- Use HTTPS exclusively. Never serve API traffic over HTTP.

## Idempotency

`GET`, `PUT`, and `DELETE` must be idempotent. For `POST` endpoints that create resources or trigger side effects, support an `Idempotency-Key` header so clients can safely retry on network failure.

## Documentation

Every endpoint must be documented with its request shape, response shape, all possible status codes, and at least one example. Use OpenAPI (Swagger). The spec is the source of truth — generate docs from it, not the other way around.

The OpenAPI spec is also consumed by the frontend to generate TypeScript types via `openapi-typescript`. This means the spec must be accurate and up to date at all times — a stale or incorrect spec breaks the frontend's type safety. Treat any drift between the spec and the implementation as a critical defect.