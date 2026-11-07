---
name: e2e-testing
description: End-to-end testing conventions using Playwright. Covers writing E2E tests, test execution, project setup, and failure reporting. Load when writing, running, or evaluating E2E tests.
license: MIT
compatibility: opencode
---

## Framework

Playwright is the E2E testing framework. No exceptions.

---

## When to write E2E tests

E2E tests are required for any task that introduces or modifies user-facing behaviour.
The implementing engineer writes them — not the QA agent.

**Write E2E tests when the task:**

- Adds or modifies an API endpoint (test the endpoint's request/response contract)
- Adds or modifies a UI page or component that involves user interaction (test the
  full flow a user would perform)
- Changes authentication or authorisation behaviour
- Modifies a multi-step workflow (checkout, onboarding, form submission)

**Do not write E2E tests when the task:**

- Is a pure refactor with no behaviour change (existing E2E tests cover it)
- Changes only internal logic with no externally observable effect
- Is a config-only change (env vars, build settings)

When in doubt, write the test. A missing E2E test is caught late; an unnecessary one
is a minor cost.

---

## Project setup

### First-time setup

If the project has no Playwright configuration, set it up before writing any tests:

1. Install Playwright:

   ```bash
   pnpm add -D @playwright/test
   pnpm exec playwright install chromium --with-deps
   ```

2. Create the config at the project root:

   ```typescript
   // playwright.config.ts
   import { defineConfig } from '@playwright/test'

   export default defineConfig({
     testDir: './e2e',
     fullyParallel: true,
     forbidOnly: !!process.env.CI,
     retries: process.env.CI ? 2 : 0,
     workers: process.env.CI ? 1 : undefined,
     reporter: 'html',
     use: {
       baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
       trace: 'on-first-retry',
       screenshot: 'only-on-failure',
     },
     webServer: {
       command: 'pnpm dev',
       url: 'http://localhost:3000',
       reuseExistingServer: !process.env.CI,
       timeout: 30_000,
     },
   })
   ```

   Adjust `baseURL`, `webServer.command`, and `webServer.url` to match the project.

3. Add the test script to `package.json`:

   ```json
   {
     "scripts": {
       "test:e2e": "playwright test"
     }
   }
   ```

4. Add to `.gitignore`:

   ```
   /test-results/
   /playwright-report/
   /blob-report/
   /playwright/.cache/
   ```

### Directory structure

```
e2e/
├── pages/                  # Page objects
│   ├── login.page.ts
│   └── dashboard.page.ts
├── fixtures/               # Shared test fixtures
│   └── auth.fixture.ts
├── helpers/                # Shared utilities
│   └── api.helper.ts
├── auth.spec.ts            # Test files grouped by feature
├── dashboard.spec.ts
└── checkout.spec.ts
```

Tests live in `e2e/` at the project root. If the project already uses a different
location (`tests/e2e/`, etc.), follow the existing convention.

---

## Writing E2E tests

### Test structure

Each test file covers one feature area. Tests within a file cover the user flows
for that feature.

```typescript
import { test, expect } from '@playwright/test'
import { LoginPage } from './pages/login.page'

test.describe('Login', () => {
  test('logs in with valid credentials and redirects to dashboard', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login('member@example.com', 'password123')

    await expect(page).toHaveURL(/.*dashboard/)
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('shows validation error for invalid credentials', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.goto()
    await loginPage.login('member@example.com', 'wrong-password')

    await expect(page.getByText('Invalid email or password')).toBeVisible()
    await expect(page).toHaveURL(/.*login/)
  })
})
```

### Page objects

Use page objects to encapsulate page-specific selectors and actions. This keeps tests
readable and makes selector changes a single-file fix.

```typescript
// e2e/pages/login.page.ts
import { type Page, type Locator } from '@playwright/test'

export class LoginPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitButton: Locator
  readonly errorMessage: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput = page.getByLabel('Email')
    this.passwordInput = page.getByLabel('Password')
    this.submitButton = page.getByRole('button', { name: 'Sign in' })
    this.errorMessage = page.getByRole('alert')
  }

  async goto() {
    await this.page.goto('/login')
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitButton.click()
  }
}
```

**Page object rules:**

- One page object per page or major component (modal, drawer, sidebar)
- Locators use accessible queries: `getByRole`, `getByLabel`, `getByText`,
  `getByPlaceholder`. Do not use CSS selectors or `data-testid` unless there is
  no accessible alternative.
- Actions (methods) represent what a user does, not how the DOM works:
  `login(email, password)` not `fillEmailInput(email)`
- Page objects never contain assertions — assertions live in the test

### Selectors — accessibility first

Follow the same philosophy as React Testing Library: query elements the way a user
finds them.

**Preferred (in order):**

1. `page.getByRole('button', { name: 'Submit' })` — role + accessible name
2. `page.getByLabel('Email address')` — form inputs by label
3. `page.getByText('Welcome back')` — visible text content
4. `page.getByPlaceholder('Search...')` — placeholder (less stable, but acceptable)

**Avoid:**

- `page.locator('.btn-primary')` — CSS class selectors break on styling changes
- `page.locator('[data-testid="submit"]')` — test IDs are a last resort
- `page.locator('#email')` — IDs are brittle and not user-visible

If no accessible selector exists, it usually means the UI has an accessibility gap.
Fix the UI first (add an `aria-label`, proper role, visible label), then write the
selector.

### Authentication in tests

Most E2E tests need an authenticated user. Use the project's seed data credentials
(documented in README per the `testing-best-practices` skill) and authenticate via
the API to avoid repeating the login UI flow in every test.

Create a shared auth fixture:

```typescript
// e2e/fixtures/auth.fixture.ts
import { test as base, type Page } from '@playwright/test'

type AuthFixtures = {
  authenticatedPage: Page
}

export const test = base.extend<AuthFixtures>({
  authenticatedPage: async ({ page }, use) => {
    // Authenticate via API — faster than UI login
    const response = await page.request.post('/api/auth/login', {
      data: { email: 'member@example.com', password: 'password123' },
    })
    const { token } = await response.json()

    // Set the auth cookie/header so subsequent navigation is authenticated
    await page.context().addCookies([{
      name: 'session',
      value: token,
      domain: 'localhost',
      path: '/',
    }])

    await use(page)
  },
})

export { expect } from '@playwright/test'
```

Adapt the auth mechanism to match the project (cookie, localStorage token, etc.).
Tests that need authentication import from this fixture instead of the base `test`.

### API endpoint tests

For backend tasks that add or modify API endpoints, write E2E tests that exercise
the endpoint's HTTP contract directly. These do not need a browser — use Playwright's
`request` context.

```typescript
import { test, expect } from '@playwright/test'

test.describe('POST /api/users', () => {
  test('creates a user and returns 201', async ({ request }) => {
    const response = await request.post('/api/users', {
      data: {
        email: `test-${Date.now()}@example.com`,
        name: 'Test User',
        password: 'secure-password-123',
      },
    })

    expect(response.status()).toBe(201)
    const body = await response.json()
    expect(body).toHaveProperty('id')
    expect(body.email).toContain('@example.com')
  })

  test('returns 400 for missing required fields', async ({ request }) => {
    const response = await request.post('/api/users', {
      data: { email: 'incomplete@example.com' },
    })

    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body).toHaveProperty('errors')
  })

  test('returns 409 for duplicate email', async ({ request }) => {
    // Uses seed data — member@example.com already exists
    const response = await request.post('/api/users', {
      data: {
        email: 'member@example.com',
        name: 'Duplicate',
        password: 'password123',
      },
    })

    expect(response.status()).toBe(409)
  })
})
```

**API test rules:**

- Test the happy path and at least one error case per endpoint
- Test authentication/authorisation: unauthenticated requests get 401, unauthorised
  get 403
- Use unique data (timestamps, UUIDs) to avoid collisions with seed data
- Verify response shapes, not just status codes — check that the body contains the
  expected fields
- Test idempotency where it matters (PUT, DELETE)

### What to test (and what not to)

**Do test:**

- Complete user flows: login → navigate → perform action → verify outcome
- Form submissions: valid input succeeds, invalid input shows errors
- Navigation: links and redirects go where they should
- API contracts: status codes, response shapes, error responses
- Auth boundaries: protected routes redirect unauthenticated users
- Empty states and loading states where they represent distinct behaviour

**Do not test:**

- Visual appearance (that is the screenshot step, not E2E)
- Implementation details (component internal state, Redux store shape)
- Third-party library behaviour (Mantine renders a modal correctly)
- Things already covered by unit tests (pure function logic)

### Test data

Follow the same factory philosophy as unit tests (see `testing-best-practices` skill).
For E2E tests that create data via the API, generate unique values to avoid collisions:

```typescript
const uniqueEmail = `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`
```

For tests that read data, rely on the project's seed data. If the seed data is
insufficient for a test scenario, extend the seed script rather than creating ad hoc
setup in the test.

### Waiting and timing

Never use `page.waitForTimeout()` (hard waits). Use Playwright's built-in auto-waiting:

- `await expect(locator).toBeVisible()` — waits for element to appear
- `await page.waitForURL(/pattern/)` — waits for navigation
- `await page.waitForResponse(url)` — waits for a specific network request
- `await expect(locator).toHaveText('...')` — waits for text to match

Playwright's auto-retry on assertions handles most timing issues. If a test is flaky,
the fix is better waiting logic, not `waitForTimeout`.

---

## Running E2E tests

Run the project's end-to-end test suite with:

```bash
pnpm test:e2e
```

If no `test:e2e` script exists in `package.json`, check for a Playwright config file (`playwright.config.ts` or `playwright.config.js`). If found, run:

```bash
pnpm exec playwright test
```

If no Playwright configuration exists at all, this is a gap. Report it — E2E tests should exist for any project with UI or API endpoints.

## What constitutes a passing E2E suite

- All tests in the Playwright suite pass with exit code 0
- No tests are skipped unless explicitly marked with a reason (`.skip('reason')`)
- No flaky test retries masking real failures — if a test required retries to pass, note it

## Interpreting failures

For each failing test, capture:
- The test name and file path
- The failure message and assertion that failed
- Any relevant screenshot or trace output from Playwright

Do not attempt to fix failing tests. Report them precisely so the engineer can address them.

## Environment

E2E tests typically need a running dev server. Check the Playwright config for `webServer` configuration. If it is configured, Playwright will start the server automatically. If not, the dev server must be started manually before running tests:

```bash
pnpm dev &
# Wait for server to be ready, then run tests
pnpm exec playwright test
```

After tests complete, clean up any background processes you started.
