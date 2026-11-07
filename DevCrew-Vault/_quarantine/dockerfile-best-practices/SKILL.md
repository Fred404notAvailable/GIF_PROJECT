---
name: dockerfile-best-practices
description: Dockerfile authoring guidelines for production-grade, provider-agnostic container images. Load this skill when creating or reviewing any Dockerfile. Covers image selection, multi-stage builds, layer caching, security hardening, and size optimisation.
license: MIT
compatibility: opencode
---

## Philosophy

Docker is the portability layer. A well-written Dockerfile means the application runs identically on a developer's laptop, in CI, and in any cloud environment — no vendor lock-in, no surprises. The image is a first-class artefact. Treat it with the same care as application code.

The goal is the smallest, most secure image that still runs the application correctly. Every byte added to a production image is a byte that must be pulled, stored, and scanned. Every tool left in the image is an attack surface.

---

## Base image selection

Always pin to a specific image digest or version tag — never `latest`. `latest` is a liability: it changes without warning and breaks reproducible builds.

```dockerfile
# ✓ Pinned version
FROM node:22.12-alpine3.21

# ✗ Floating tag — do not use
FROM node:lts
FROM node:latest
```

**Preference order for base images (smallest attack surface first):**

1. **Distroless** (`gcr.io/distroless/*`) — no shell, no package manager, minimal OS. Best for compiled languages or self-contained runtimes.
2. **Alpine** (`alpine:3.x`) — tiny footprint (~5 MB), full shell, widely supported. Good default for most Node.js and Python services.
3. **Debian Slim** (`debian:bookworm-slim`) — larger than Alpine but better glibc compatibility. Use when Alpine causes native module issues.
4. **Full Debian/Ubuntu** — last resort. Only when the application genuinely requires a full OS environment.

Never use a full Debian or Ubuntu image in production without documenting why no smaller alternative was viable.

---

## Multi-stage builds

Use multi-stage builds for every image that has a build step. The final stage must contain only what the runtime needs.

```dockerfile
# Stage 1: dependencies
FROM node:22.12-alpine3.21 AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# Stage 2: build
FROM deps AS builder
COPY . .
RUN pnpm build

# Stage 3: production runtime — only artefacts, no dev tools
FROM node:22.12-alpine3.21 AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser

COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --chown=appuser:appgroup package.json ./

USER appuser
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

The `builder` and `deps` stages never ship. The `runner` stage contains no compilers, test frameworks, or dev dependencies.

---

## Layer caching

Docker rebuilds every layer after the first change. Structure your Dockerfile so that the most stable files come first and the most volatile files come last.

```dockerfile
# ✓ Dependencies copied and installed before source — cache is preserved when source changes
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .

# ✗ Source copied first — cache busted on every change
COPY . .
RUN pnpm install
```

**Rules:**
- Copy lockfiles and manifests (`package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `go.mod`, etc.) before copying source.
- Install dependencies in a dedicated layer separate from the build step.
- `.dockerignore` must exclude `node_modules`, `.git`, build output, and local env files so that irrelevant changes do not bust the cache.

---

## `.dockerignore`

Every service must have a `.dockerignore` adjacent to its `Dockerfile`. At minimum:

```
node_modules
.git
.gitignore
*.log
.env
.env.*
dist
build
coverage
.DS_Store
```

Do not rely on the application's `.gitignore` for this. Be explicit.

---

## Non-root user

The process inside the container must never run as root. Create a dedicated system user in the final stage and switch to it before the `CMD`.

```dockerfile
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser
USER appuser
```

Use fixed UIDs/GIDs so that file permissions are predictable when volumes are mounted.

---

## Secrets

Never pass secrets as build arguments or bake them into images.

```dockerfile
# ✗ Never do this
ARG API_KEY
ENV API_KEY=$API_KEY
```

Secrets are supplied at runtime via environment variables, mounted secret files, or a secrets manager. The image must function without any secret present at build time — it only needs secrets at runtime.

For build-time secrets (e.g. private registry auth, private npm packages), use BuildKit secret mounts:

```dockerfile
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    pnpm install --frozen-lockfile
```

---

## Health checks

Every production Dockerfile must include a `HEALTHCHECK`. This integrates with Docker Compose, Kubernetes liveness probes, and any orchestrator.

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
```

Use `wget` (available in Alpine) or `curl`. Do not add extra tools just for the health check — prefer the runtime's own binary where possible.

---

## Signal handling and process management

Node.js, Python, and most interpreted runtimes do not forward OS signals when launched as PID 1 inside a container. Use `CMD` in exec form (JSON array) to avoid shell wrapping, and add signal handling in the application itself.

```dockerfile
# ✓ Exec form — process receives signals directly
CMD ["node", "dist/index.js"]

# ✗ Shell form — signals go to /bin/sh, not the app
CMD node dist/index.js
```

For applications that genuinely need a process supervisor, use `tini` as the entrypoint:

```dockerfile
RUN apk add --no-cache tini
ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/index.js"]
```

---

## Image size audit

After writing a Dockerfile, verify the image size is reasonable for the stack:

| Stack | Target production image size |
|---|---|
| Node.js (Alpine) | < 200 MB |
| Python (Alpine or slim) | < 200 MB |
| Go (distroless or scratch) | < 50 MB |
| Java (JRE only) | < 250 MB |

If the image significantly exceeds these targets, investigate: leftover build tools, unnecessary OS packages, or missing `--no-cache` on `apk add`.

---

## Checklist

Before finalising any Dockerfile:

- [ ] Base image is pinned to a specific version, not `latest`
- [ ] Multi-stage build separates build tools from the runtime image
- [ ] Dependency files are copied before source code (cache-friendly ordering)
- [ ] `.dockerignore` exists and excludes `node_modules`, `.git`, env files
- [ ] Process runs as a non-root user with a fixed UID/GID
- [ ] No secrets in `ARG`, `ENV`, or baked into any layer
- [ ] `HEALTHCHECK` instruction is present
- [ ] `CMD` uses exec form (JSON array)
- [ ] Image size is within target range for the stack
