---
name: deployment-planning
description: Deployment strategy and CI/CD pipeline design guidelines. Load this skill when designing deployment workflows, writing CI/CD pipeline configuration, or advising on release strategy. Covers build-once/deploy-anywhere, environment promotion, rollback, and pipeline structure — all provider-agnostic.
license: MIT
compatibility: opencode
---

## Philosophy

The guiding principle is **build once, deploy anywhere**. The Docker image produced in CI is the deployment artefact. It is built exactly once, pushed to a container registry, and the same image digest is promoted through environments. No rebuilds per environment. No environment-specific build flags baked into the image. Runtime configuration is injected at deploy time, not build time.

This is what makes the system provider-agnostic: the image is the contract. Swap the hosting platform, and the image still works.

---

## The deployment pipeline

A standard pipeline has these stages in order. Fast stages first — fail fast, fail cheap.

```
Lint & Type-check  →  Unit Tests  →  Build Image  →  Integration Tests
      →  Push to Registry  →  Deploy to Staging  →  Smoke Tests
           →  [Manual or automatic approval gate]
                →  Deploy to Production  →  Health Verification  →  Done
```

**Stage rules:**
- Lint and type-check run in parallel with no network I/O — they must complete in under 60 seconds.
- Unit tests run before any Docker build. No point building a broken image.
- The image is built exactly once and tagged with the git SHA.
- Integration tests run against the built image, not against the source.
- Staging and production use the same image digest — no rebuild.
- The approval gate before production is **manual** by default. Automated promotion is acceptable only after the project has demonstrated reliable staging smoke tests for several sprints.

---

## Image tagging strategy

Tag images with the full git SHA, not a version number assigned at build time:

```
registry.example.com/myapp/api:a3f8c2d
```

Use the SHA as the primary identifier. Optionally add a `latest` or branch tag as a convenience alias, but never deploy using `latest`.

In CI:

```yaml
# GitHub Actions example
- name: Build and push
  env:
    SHA: ${{ github.sha }}
  run: |
    docker build -t registry.example.com/myapp/api:$SHA .
    docker push registry.example.com/myapp/api:$SHA
```

---

## Environment promotion

Environments are: `development` → `staging` → `production`.

**Development:** Continuous deployment from the main branch or feature branches. No approval gate. Used for integration testing.

**Staging:** Mirrors production configuration as closely as possible. Deployed automatically after CI passes on main. The smoke test suite runs against staging before the production gate opens.

**Production:** Deployed only after the staging smoke tests pass and a human approves (or after a configurable time window if the team opts into automated promotion).

Never use environment-specific build flags. Configuration differences between environments are supplied via environment variables or secrets at deploy time.

---

## Deployment strategy

**Default: Rolling update** with `maxUnavailable: 0`.

- Zero downtime: new pods start before old ones stop.
- Straightforward rollback: redeploy the previous image SHA.
- Appropriate for the vast majority of stateless services.

**Blue-green:** Two identical production environments; traffic switches atomically. Use when the application has a long startup time, when you need instant rollback, or when running two versions simultaneously is not safe. Cost: temporarily doubled infrastructure.

**Canary:** Route a small percentage of traffic to the new version before full rollout. Use only when you have meaningful traffic volume and a way to monitor error rates per version (e.g. per-pod metrics). Do not implement canary as a default — it adds operational complexity that is only worth it at scale.

**Recreate:** Stop all running instances, then start the new ones. Causes downtime. Only appropriate for non-critical batch jobs or stateful services where running two versions simultaneously would corrupt state.

Recommend **rolling update** unless the user has a specific reason to choose otherwise.

---

## Rollback strategy

Rollback is a redeployment of the previous image SHA. The pipeline must record the deployed SHA at each step so rollback is always a single command or button press:

```bash
# Example: roll back by redeploying the previous SHA
docker pull registry.example.com/myapp/api:$PREVIOUS_SHA
# update deployment to reference $PREVIOUS_SHA
```

Automated rollback on health check failure is desirable but optional. If implemented, the trigger must be a confirmed health check failure after the new version has been live for a configurable stabilisation window (e.g. 5 minutes), not a single failed request.

---

## Secrets in CI/CD

Secrets are never in source code, Dockerfiles, or committed manifest files. They are injected by the CI/CD system at deploy time.

For GitHub Actions, use encrypted repository or environment secrets:

```yaml
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

For Kubernetes, secrets are created out-of-band (manually, via a secrets operator, or via the CI pipeline using a secrets manager like HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault) and referenced in manifests. The manifest file itself contains only the Secret's shape, not its values.

**Rule:** If a secret appears in a pipeline YAML file in plain text, that is a critical security defect.

---

## Health verification after deploy

After every production deployment, the pipeline must verify that the new version is healthy before considering the deploy complete:

1. Wait for the rollout to finish (`kubectl rollout status` or equivalent).
2. Hit the `/health` endpoint on the new pods and confirm `200 OK`.
3. Check the application error rate for a stabilisation window (minimum 2 minutes).
4. Only mark the deploy as successful after the stabilisation window passes without errors.

If health verification fails, trigger rollback immediately and notify the team.

---

## CI/CD pipeline configuration guidelines

GitHub Actions is assumed as the default. The same principles apply to any CI system (GitLab CI, CircleCI, Buildkite, etc.).

**Structure:**

- One workflow file per concern: `ci.yml` (test and build), `deploy-staging.yml`, `deploy-production.yml`.
- Do not put all logic in one enormous workflow file.
- Use reusable workflows or composite actions for repeated steps.

**Performance:**

- Cache dependency installation between runs (`actions/cache` or native caching).
- Run independent jobs in parallel.
- Fail the pipeline at the earliest possible stage.

**Notifications:**

- Notify on deployment success and failure. Telegram, Slack, email — whatever the project uses. Failure notifications are more important than success.

---

## Dockerfile → registry → deploy: the invariant chain

This chain must never be broken:

1. Source code is tested.
2. The tested source produces exactly one Docker image.
3. That image is pushed to a registry with its git SHA as the tag.
4. The same image SHA is deployed to staging, then (on approval) to production.
5. Every environment variable and secret is injected at deploy time — nothing is baked in.

Any pipeline that rebuilds the image per environment, or injects environment-specific code at build time, violates this invariant and reduces confidence that what was tested is what was deployed.

---

## Checklist

Before finalising any deployment plan or pipeline:

- [ ] Image is built once and tagged with the git SHA
- [ ] Same image digest is deployed to all environments (no per-environment builds)
- [ ] No secrets in pipeline YAML files, Dockerfiles, or committed manifests
- [ ] Deployment strategy is documented and justified (default: rolling update)
- [ ] Rollback procedure is defined and executable in under 5 minutes
- [ ] Health verification step runs after every production deployment
- [ ] Production deployment requires either manual approval or a passed staging smoke test gate
- [ ] Pipeline fails fast: lint/test before build, build before deploy
- [ ] Notifications are configured for deployment failure
