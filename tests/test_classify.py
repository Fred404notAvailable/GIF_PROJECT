"""
test_classify.py — Tests for catalog.py classification logic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from catalog import classify_skill, _DEFAULT_MODULES, _build_default_catalog


@pytest.fixture()
def catalog():
    return _build_default_catalog()


def test_classify_backend(catalog):
    mid, score = classify_skill(
        slug="fastapi-templates",
        name="fastapi-templates",
        description="Use when you need a FastAPI backend REST API service template.",
        body="FastAPI, REST, Pydantic, Python backend patterns.",
        catalog=catalog,
        source_name="wshobson-agents",
    )
    assert mid == 1, f"Expected module 1 (Backend), got {mid}"
    assert score > 0


def test_classify_security(catalog):
    mid, score = classify_skill(
        slug="owasp-top10-auditor",
        name="owasp-top10-auditor",
        description="Use when auditing web apps for OWASP Top 10 vulnerabilities. Trigger: security audit.",
        body="OWASP, XSS, SQLI, CSRF, security vulnerabilities.",
        catalog=catalog,
    )
    assert mid == 4, f"Expected module 4 (Security), got {mid}"


def test_classify_ai(catalog):
    mid, score = classify_skill(
        slug="langgraph-fundamentals",
        name="langgraph-fundamentals",
        description="Use when building LangGraph agent workflows with LLM nodes.",
        body="LangGraph, LangChain, agent, LLM, RAG, memory.",
        catalog=catalog,
        source_name="langchain-skills",
    )
    assert mid == 5, f"Expected module 5 (AI/LLM), got {mid}"


def test_classify_database(catalog):
    mid, score = classify_skill(
        slug="prisma-postgres-setup",
        name="prisma-postgres-setup",
        description="Use when setting up Prisma ORM with PostgreSQL database.",
        body="Prisma, PostgreSQL, database schema, migrations.",
        catalog=catalog,
        source_name="prisma",
    )
    assert mid == 3, f"Expected module 3 (Database), got {mid}"


def test_classify_devops(catalog):
    mid, score = classify_skill(
        slug="terraform-skill",
        name="terraform-skill",
        description="Use when deploying cloud infrastructure with Terraform. Activate for IaC.",
        body="Terraform, HashiCorp, AWS, GCP, infrastructure as code, Helm.",
        catalog=catalog,
        source_name="hashicorp",
    )
    assert mid == 7, f"Expected module 7 (DevOps), got {mid}"


def test_classify_testing(catalog):
    mid, score = classify_skill(
        slug="test-driven-development",
        name="test-driven-development",
        description="Use when practicing TDD, writing unit tests, and debugging code.",
        body="TDD, unit tests, pytest, jest, red-green-refactor.",
        catalog=catalog,
        source_name="obra-superpowers",
    )
    assert mid == 6, f"Expected module 6 (Testing), got {mid}"


def test_classify_frontend(catalog):
    mid, score = classify_skill(
        slug="react-best-practices",
        name="react-best-practices",
        description="Use when building React UI components and frontend applications.",
        body="React, Next.js, Tailwind CSS, shadcn, component architecture.",
        catalog=catalog,
        source_name="vercel-agent-skills",
    )
    assert mid == 2, f"Expected module 2 (Frontend), got {mid}"


def test_vendor_bonus_raises_score(catalog):
    """Vendor-published sources get a scoring bonus."""
    _, score_vendor = classify_skill(
        slug="supabase",
        name="supabase",
        description="Use when working with Supabase postgres database.",
        body="Supabase, postgres, database.",
        catalog=catalog,
        source_name="supabase",  # vendor
    )
    _, score_anon = classify_skill(
        slug="supabase",
        name="supabase",
        description="Use when working with Supabase postgres database.",
        body="Supabase, postgres, database.",
        catalog=catalog,
        source_name="some-random-aggregator",
    )
    assert score_vendor > score_anon

