---
name: tdd
description: Test-driven development workflow and discipline. Load this skill before writing any new code or modifying existing behaviour. Covers the red-green-refactor cycle, test design, triangulation, and TDD pitfalls to avoid.
license: MIT
compatibility: opencode
---

## What TDD is

TDD is a development discipline, not a testing strategy. The goal is not test coverage — it is to let tests drive the design of the code. Tests written after the fact verify behaviour. Tests written first shape the interface, reveal design problems early, and give you confidence to refactor.

## The cycle

Follow this cycle without skipping steps:

**Red** — Write a single failing test for the next smallest piece of behaviour. Run it and confirm it fails for the right reason. A test that fails because of a compile error or missing import is not a meaningful red — fix that first before calling it red.

**Green** — Write the minimum code required to make the test pass. Do not write more than is needed. If the simplest implementation feels wrong, that is information — note it, but still write the simplest thing first.

**Refactor** — With tests green, clean up both the production code and the test. Remove duplication, improve names, simplify structure. Run tests again after each change. Do not add new behaviour during refactor.

Repeat. Each cycle should take minutes, not hours.

## Starting a new feature

Before writing any code, write a failing test for the smallest observable behaviour of the feature. If you cannot write a test because you do not know what the interface should look like, that is a signal to think about the interface first. Sketch it, then write the test.

Do not write a test for an entire feature at once. Write a test for one specific input and its expected output.

## Triangulation

When the correct implementation is not obvious, use triangulation: write multiple tests with different inputs that all point toward the same general behaviour. Let the tests force the general solution to emerge rather than assuming it upfront.

Example: if you are implementing a function that formats a name, do not write one test for "John Smith" and assume the implementation is correct. Write tests for empty strings, single names, names with middle initials, names with extra whitespace. Let the tests drive out the edge cases.

## What makes a good first test

- Tests a single, specific behaviour
- Has a clear, descriptive name that explains what is being tested and under what conditions
- Follows the Arrange / Act / Assert structure — setup, call, verify, in that order
- Has one logical assertion (this does not mean one `expect` call — it means one concept being verified)
- Is fast and has no side effects on other tests

## Test naming

Name tests as sentences: `it('returns an empty array when no items match the filter')` not `it('test filter')`. The name should be readable as a specification. A failing test name should tell you exactly what broke without reading the test body.

## What not to do

- Do not write tests after the code is written and call it TDD. That is testing, not test-driven development.
- Do not write multiple tests before going green. Write one, make it pass, then write the next.
- Do not test implementation details. Test inputs and outputs. If a refactor breaks a test without changing behaviour, the test was wrong.
- Do not mock everything. Mocks are appropriate at true boundaries (network, database, filesystem, clock). Mocking internal collaborators couples tests to implementation.
- Do not skip the refactor step. Green without refactor accumulates debt.
- Do not write tests that test the framework or language. Test your logic.

## When to deviate

TDD is the default. The permitted exceptions are narrow. Do not expand them with your own judgment.

Deviate only when ALL of the following are true:
- You are exploring an unfamiliar API or problem space — spike first (without tests), learn, then **delete the spike** and TDD the real solution from scratch
- You are writing a true one-off throwaway script — meaning it will never be run again and has no correctness requirements beyond "it ran once"
- You are fixing a pure environment or configuration issue with no logical behaviour of your own to test (e.g. fixing a missing environment variable, updating a config file value)

**These are not valid reasons to skip TDD:**
- "This is just scaffolding" — scaffolding produces components and routes that have observable behaviour. Test them.
- "This is a simple task" — simplicity does not exempt code from tests. A simple component still has a test: does it render what it should?
- "The user didn't ask for tests" — the user does not need to ask. Tests are part of every task.
- "Setting up the project structure first" — if you are creating files that will be shipped, write a test first. Set up the test infrastructure as the first act of project creation.
- "Tests would be excessive for this" — this reasoning is always wrong. If the code has observable behaviour, it has a test.

When deviating, state explicitly which permitted exception applies and why.