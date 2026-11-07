# DevCrew Vault — Coverage Report

Generated: `2026-11-07T19:24:31Z`

| Module | Selected | Target | Shortfall | Candidates | Alternates |
|--------|----------|--------|-----------|------------|------------|
| 1. Modern Backend & API Development | 15 | 15 | ✅ 0 | 779 | 4 |
| 2. Frontend & UI Engine Frameworks | 15 | 15 | ✅ 0 | 785 | 1 |
| 3. Database, Vector & Storage Management | 15 | 15 | ✅ 0 | 379 | 1 |
| 4. Security, Auditing & SecOps | 15 | 15 | ✅ 0 | 188 | 1 |
| 5. AI Architecture, LLM & Prompt Engineering | 15 | 15 | ✅ 0 | 1134 | 3 |
| 6. Testing, QA & Reliability Engineering | 10 | 10 | ✅ 0 | 264 | 1 |
| 7. DevOps, Containers & Cloud Automation | 15 | 15 | ✅ 0 | 524 | 1 |

**Total shortfall:** 0 skill(s)


## Module 1: Modern Backend & API Development

### Selected

- `api-design-principles` — Master REST and GraphQL API design principles to build intuitive, scalable, and 
- `architecture-patterns` — Master proven backend architecture patterns including Clean Architecture, Hexago
- `microservices-patterns` — Master microservices architecture patterns including service boundaries, inter-s
- `dotnet-backend-patterns` — Master C#/.NET patterns for building production-grade APIs, MCP servers, and ent
- `nodejs-backend-patterns` — Comprehensive guidance for building scalable, maintainable, and production-ready
- `fastapi-templates` — Create production-ready FastAPI projects with async patterns, dependency injecti
- `workflow-orchestration-patterns` — Master workflow orchestration architecture with Temporal, covering fundamental d
- `event-store-design` — Design and implement event stores for event-sourced systems. Use when building e
- `hono` — Build ultra-fast web APIs and full-stack apps with Hono — runs on Cloudflare Wor
- `cloudflare` — Discover and choose Cloudflare products for apps, APIs, AI agents, storage, netw
- `stripe-best-practices` — Guides Stripe integration decisions across development and test environment plan
- `mcp-builder` — Guide for creating high-quality MCP (Model Context Protocol) servers that enable
- `convex` — Convex reactive backend expert: schema design, TypeScript functions, real-time s
- `database-design` — Database design principles and decision-making. Schema design, indexing strategy
- `nodejs-best-practices` — Node.js development principles and decision-making. Framework selection, async p

### Alternates

- `api-security` _(alternate)_
- `api-security-testing` _(alternate)_
- `aws-serverless-eda` _(alternate)_
- `canvas-design` _(alternate)_

### ⚠️ Unfilled Pinned Slots

- Slot 11: `better-auth-best-practices` (from `better-auth`)
- Slot 12: `better-auth-security-best-practices` (from `better-auth`)
- Slot 15: `backend-development` (from `claudekit`)

## Module 2: Frontend & UI Engine Frameworks

### Selected

- `frontend-design` — Guidance for distinctive, intentional visual design when building new UI or resh
- `web-artifacts-builder` — Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts 
- `react-best-practices` — Comprehensive performance optimization guide for React and Next.js applications,
- `next-dev-loop` — Verify Next.js runtime behavior after editing app code. Use this skill to confir
- `tailwind-design-system` — Build production-ready design systems with Tailwind CSS, including design tokens
- `react-native-best-practices` — Provides React Native performance optimization guidelines for FPS, TTI, bundle s
- `frontend-patterns` — Frontend development patterns for React, Next.js, state management, performance 
- `web-ui-shadcn-ui` — shadcn/ui component library patterns, CLI usage, theming, customization
- `angular-best-practices` — Angular performance optimization and best practices guide. Use when writing, rev
- `ui-visual-validator` — Rigorous visual validation expert specializing in UI testing, design system comp
- `canvas-design` — Create beautiful visual art in .png and .pdf documents using design philosophy. 
- `theme-factory` — Toolkit for styling artifacts with a theme. These artifacts can be slides, docs,
- `web-styling-tailwind` — Tailwind CSS v4 - utility-first CSS framework with CSS-first configuration
- `web-tooling-storybook` — Storybook patterns - CSF 3.0, args, controls, autodocs, play functions, interact
- `frameworks-on-cloudflare` — Build, migrate, and deploy web-framework applications on Cloudflare Workers. Use

### Alternates

- `convex` _(alternate)_

### ⚠️ Unfilled Pinned Slots

- Slot 25: `server-actions` (from `szum-tech`)
- Slot 26: `react-19-compiler` (from `szum-tech`)
- Slot 27: `tailwind-css-4` (from `szum-tech`)
- Slot 28: `storybook-testing` (from `szum-tech`)
- Slot 29: `svelte` (from `modernstack`)

## Module 3: Database, Vector & Storage Management

### Selected

- `supabase-postgres-best-practices` — Postgres performance optimization and best practices from Supabase. Use this ski
- `supabase` — Use when doing ANY task involving Supabase.
- `neon-postgres` — Guides and best practices for working with Neon Serverless Postgres. Covers setu
- `neon-postgres-branches` — Choose and create the right Neon branch type for testing and development. Use wh
- `prisma-postgres-setup` — Obtain or reuse a Prisma Postgres database and connect an application. Use when 
- `prisma-cli` — Prisma ORM 7 CLI reference for existing Prisma 7 applications or explicitly sele
- `firebase-basics` — Provides foundational Firebase CLI setup, CLI installation, version checks (`fir
- `sql-optimization-patterns` — Diagnose slow SQL with query plans, preserve query results, and verify indexing 
- `database-migration` — Master database schema and data migrations across ORMs (Sequelize, TypeORM, Pris
- `postgresql-table-design` — Use this skill when designing or reviewing a PostgreSQL-specific schema. Covers 
- `clickhouse-best-practices` — MUST USE when reviewing ClickHouse schemas, queries, or configurations. Contains
- `vector-index-tuning` — Optimize vector index performance for latency, recall, and memory. Use when tuni
- `similarity-search-patterns` — Implement efficient similarity search with vector databases. Use when building s
- `hybrid-search-implementation` — Combine vector and keyword search for improved retrieval. Use when implementing 
- `embedding-strategies` — Guide to selecting and optimizing embedding models for vector search application

### Alternates

- `database-design` _(alternate)_

## Module 4: Security, Auditing & SecOps

### Selected

- `security-audit` — Comprehensive security auditing workflow covering web application testing, API s
- `differential-review` — Security-focused code review for PRs, commits, and diffs.
- `codeql` — Comprehensive guide for setting up and configuring CodeQL code scanning via GitH
- `variant-analysis` — Find similar vulnerabilities and bugs across codebases using pattern-based analy
- `sharp-edges` — Review misuse-prone security APIs, configuration defaults, cryptographic interfa
- `supply-chain-risk-auditor` — Identifies dependencies at heightened risk of exploitation or takeover. Use when
- `agentic-actions-auditor` — Audits GitHub Actions workflows for security vulnerabilities in AI agent integra
- `firebase-security-rules-auditor` — Audits Firebase (Firestore, Cloud Storage) security rules for vulnerabilities, p
- `stride-analysis-patterns` — Apply STRIDE methodology to systematically identify threats. Use when analyzing 
- `api-security` — Authorized security assessment of REST, GraphQL, WebSocket, and SOAP APIs: disco
- `api-security-testing` — API security testing workflow for REST and GraphQL APIs covering authentication,
- `semgrep-rule-creator` — Creates custom Semgrep rules for detecting security vulnerabilities, bug pattern
- `solidity-security` — Master smart contract security best practices, vulnerability prevention, and sec
- `redis-security` — Redis security guidance covering authentication (requirepass and ACL users), TLS
- `spring-security` — Configure, test and review Spring Security 6/7 in Spring Boot 3/4 apps: Security

### Alternates

- `python-project-rules` _(alternate)_

### ⚠️ Unfilled Pinned Slots

- Slot 46: `secauditor` (from `secauditor`)
- Slot 48: `secure-webapp` (from `secure-webapp`)
- Slot 49: `owasp-audit` (from `cybersecurity-skills`)
- Slot 50: `insecure-defaults` (from `trailofbits`)
- Slot 52: `semgrep` (from `trailofbits`)
- Slot 54: `sarif-parsing` (from `trailofbits`)

## Module 5: AI Architecture, LLM & Prompt Engineering

### Selected

- `prompt-engineering-patterns` — Master advanced prompt engineering techniques to maximize LLM performance, relia
- `rag-implementation` — RAG (Retrieval-Augmented Generation) implementation workflow covering embedding 
- `langchain-architecture` — Master the LangChain framework for building sophisticated LLM applications with 
- `langgraph-fundamentals` — INVOKE THIS SKILL when writing ANY LangGraph code. Covers StateGraph, state sche
- `langgraph-persistence` — INVOKE THIS SKILL when your LangGraph needs to persist state, remember conversat
- `langgraph-human-in-the-loop` — INVOKE THIS SKILL when implementing human-in-the-loop patterns, pausing for appr
- `langchain-fundamentals` — Create LangChain agents with create_agent, define tools, and use middleware for 
- `langchain-rag` — INVOKE THIS SKILL when building ANY retrieval-augmented generation (RAG) system.
- `langchain-middleware` — INVOKE THIS SKILL when you need human-in-the-loop approval, custom middleware, o
- `deep-agents-core` — INVOKE THIS SKILL when building ANY Deep Agents application. Covers create_deep_
- `deep-agents-memory` — INVOKE THIS SKILL when your Deep Agent needs memory, persistence, or filesystem 
- `autonomous-agent-patterns` — Design patterns for building autonomous coding agents, inspired by [Cline](https
- `agent-memory-systems` — Design tenant-scoped memory, retrieval and retention for agents. Use when planni
- `langfuse` — Expert in Langfuse - the open-source LLM observability platform. Covers tracing,
- `llm-evaluation` — Master comprehensive evaluation strategies for LLM applications, from automated 

### Alternates

- `dispatching-parallel-agents` _(alternate)_
- `pytest-rules` _(alternate)_
- `receiving-code-review` _(alternate)_

## Module 6: Testing, QA & Reliability Engineering

### Selected

- `test-driven-development` — Use a failing behavioral test to guide a feature or bug fix, then implement and 
- `systematic-debugging` — Use when encountering any bug, test failure, or unexpected behavior, before prop
- `verification-before-completion` — Claiming work is complete without verification is dishonesty, not efficiency. Us
- `requesting-code-review` — Use when completing tasks, implementing major features, or before merging to ver
- `webapp-testing` — Toolkit for interacting with and testing local web applications using Playwright
- `e2e-testing` — End-to-end testing workflow with Playwright for browser automation, visual regre
- `observability-engineer` — Build production-ready monitoring, logging, and tracing systems. Implements comp
- `dispatching-parallel-agents` — Use when facing 2+ independent tasks that can be worked on without shared state 
- `receiving-code-review` — Code review requires technical evaluation, not emotional performance.
- `temporal-python-testing` — Comprehensive testing approaches for Temporal workflows using pytest, progressiv

### Alternates

- `pytest-rules` _(alternate)_

### ⚠️ Unfilled Pinned Slots

- Slot 81: `web-testing` (from `claudekit`)
- Slot 82: `testing-perf` (from `orchestkit`)
- Slot 84: `testing-best-practices` (from `opencode-configs`)

## Module 7: DevOps, Containers & Cloud Automation

### Selected

- `docker-development` — Use when working with ANY Docker task: writing Dockerfiles, configuring docker-c
- `kubernetes-skill` — Prevent Kubernetes hallucinations by diagnosing and fixing failure modes: insecu
- `terraform-skill` — Terraform infrastructure as code best practices
- `application-performance-performance-optimization` — Optimize end-to-end application performance with profiling, observability, and b
- `bash-linux` — Bash/Linux terminal patterns. Critical commands, piping, error handling, scripti
- `aws-cdk-development` — AWS Cloud Development Kit (CDK) expert for building cloud infrastructure with Ty
- `aws-serverless` — Specialized skill for building production-ready serverless applications on AWS. 
- `aws-serverless-eda` — AWS serverless and event-driven architecture expert based on Well-Architected Fr
- `azure-devops` — Set up Azure Pipelines for CI/CD, configure build and release pipelines, manage 
- `devops-deploy` — DevOps e deploy de aplicacoes — Docker, CI/CD com GitHub Actions, AWS Lambda, SA
- `docker-build-strategies` — Use this skill when writing, reviewing, or optimizing Dockerfiles, even if the u
- `docker-compose-patterns` — Use this skill when creating, modifying, or debugging Docker Compose configurati
- `infra-ci-cd-github-actions` — GitHub Actions, pipelines, deployment
- `terraform-policy` — Write, test, or convert Terraform Policy files (.policy.hcl, .policytest.hcl, Se
- `extension-to-functions-codebase` — Skill for converting an installed Firebase Extension (or extension source) into 

### Alternates

- `python-project-rules` _(alternate)_

### ⚠️ Unfilled Pinned Slots

- Slot 86: `docker` (from `docker-skills`)
- Slot 88: `dockerfile-best-practices` (from `opencode-configs`)
- Slot 89: `kubernetes-manifests` (from `opencode-configs`)
- Slot 92: `terraform` (from `hashicorp`)
- Slot 93: `aws` (from `aws-skills`)
- Slot 94: `devops-deployment` (from `orchestkit`)
- Slot 95: `ansible` (from `blastum-skills`)
- Slot 96: `github-cli` (from `blastum-skills`)
- Slot 97: `q24-github-actions-generator` (from `q24-devops`)
- Slot 98: `q24-helm-generator` (from `q24-devops`)
