# DevCrew Skill Vault — Governance Decisions Needed

This document records the licensing and provenance policy decisions that require user authorization, the default behavior applied during the audit, and the concrete slot impact for each choice.

Until explicit user direction is provided, the **stricter reading** has been enforced across the vault: **no skill is selected unless its verified license is currently listed in `allowed_licenses`**.

---

## 1. Creative Commons Attribution-ShareAlike 4.0 (`CC-BY-SA-4.0`)

### Context
`trailofbits/skills.git` (98 security skills) is released under `CC-BY-SA-4.0`. In addition, `netresearch/docker-development-skill.git` contains dual licensing where executable code is MIT but core content/guidance is licensed under `CC-BY-SA-4.0`.

In previous iterations, skills from Trail of Bits (`differential-review`, `variant-analysis`, `sharp-edges`, `supply-chain-risk-auditor`, `agentic-actions-auditor`) were pulled through `antigravity-awesome` (an aggregator repo with an MIT root license) and marked selected, creating a contradiction with the reported quarantine of `trailofbits`.

### Default Applied
- **Strictly Disallowed & Excluded from `selected`**: All CC-BY-SA-4.0 skills have been removed from the 100 selected slots and placed in candidate / quarantine status.
- Replaced in Module 4 (Security) with dedicated MIT/Apache-2.0 alternatives: `secure-webapp` (OWASP Top 10), `shared-security-auth-security`, `security-auditor`, `security-review`, `vulnerability-scanner`, `web-security-testing`, `xss-html-injection`, and `sql-injection-testing`.
- Replaced in Module 7 (DevOps) with `docker-compose-patterns` (Apache-2.0).

### Impact Analysis
- **If Approved (add `CC-BY-SA-4.0` to `allowed_licenses`)**:
  - Unlocks **98 high-depth Trail of Bits security skills** and `docker-development`.
  - Trail of Bits skills can be reinstated to Module 4 (Security) slots.
  - *Risk / Obligation*: Vault redistributions must preserve attribution and inherit ShareAlike terms.
- **If Rejected (maintain current strict policy)**:
  - **Zero ShareAlike obligations**. 100% of the selected skills remain under permissive licenses (83 MIT, 16 Apache-2.0, 1 MPL-2.0).
  - All 15 Module 4 Security slots and 15 Module 7 DevOps slots remain 100% filled with vetted, compliant skills.

---

## 2. Mozilla Public License 2.0 (`MPL-2.0`)

### Context
`hashicorp/agent-skills.git` is licensed under `MPL-2.0` (weak copyleft: modifications to existing MPL files must be shared under MPL, but larger works combining MPL files with proprietary code do not become copylefted).

### Default Applied
- **Allowed**: `MPL-2.0` is currently included in `devcrew.config.yaml` (`allowed_licenses`).
- Currently **1 skill selected**: `terraform-policy` (Module 7, slot 92) for infrastructure policy-as-code. `terraform-stacks` is indexed as an alternate candidate.

### Impact Analysis
- **If Maintained Allowed (default)**:
  - 1 selected slot utilized (`terraform-policy`).
  - Safe for enterprise modular use under standard MPL file-level boundary terms.
- **If Disallowed (remove `MPL-2.0` from `allowed_licenses`)**:
  - `terraform-policy` will be moved to `_quarantine/`.
  - Slot 92 would be replaced by vetted candidate `azure-deployment-preflight` (MIT) or `devops-pipeline-builder` (MIT). Module 7 would remain at 15/15 target.

---

## 3. Unlicensed Upstream Repositories

### Context
Several high-utility source repositories lack an upstream `LICENSE` or `LICENSE.txt` file at their root:
1. `better-auth/skills` (6 authentication skills)
2. `mrgoonie/claudekit-skills` (45 development skills)
3. `jon23d/opencode-configs` (18 DevOps/testing skills)
4. `coreyx/modernstack-skills` (6 full-stack skills)

### Default Applied
- **Quarantined**: Under `on_unknown_license: quarantine`, all **75 packages** from these repositories are held in `DevCrew-Vault/_quarantine/`.
- None are selected. Each contains an automated `REPORT.md` and `.source.json`.

### Impact Analysis
- **If Upstream Maintainers Add an Open Source License (MIT/Apache-2.0)**:
  - Re-sync will automatically release all 75 skills into `DevCrew-Vault/skills/`.
  - In particular, official `better-auth-best-practices` and `better-auth-security-best-practices` could fill Module 1 slots 11 and 12 directly from the vendor.
- **If User Grants an Explicit Exception for In-House Use**:
  - These skills could be ingested for internal development.
- **If Left Unlicensed (default)**:
  - Safe legal isolation: zero unlicensed code is exposed in `DevCrew-Vault/skills/`.
  - All 100 vault slots remain fully satisfied by licensed alternatives.

---

## 4. Per-Skill License Exceptions (Folder-Level vs. Repo-Level)

### Context
In `anthropics/skills.git`, frontmatter metadata contains `license: Complete terms in LICENSE.txt`. The repository root has varied documentation licensing, but **every individual skill directory contains its own `LICENSE.txt` with full Apache-2.0 text**.

### Default Applied
- **Recognized as `Apache-2.0`**: Per-skill license discovery prioritizes the skill folder's own `LICENSE*` file ahead of frontmatter pointer text and repo root licenses.
- Affected selected skills (6 skills):
  - `mcp-builder` (Module 1, slot 14)
  - `frontend-design` (Module 2, slot 16)
  - `web-artifacts-builder` (Module 2, slot 17)
  - `theme-factory` (Module 2, slot 200)
  - `canvas-design` (Module 2, slot 200)
  - `webapp-testing` (Module 6, slot 80)

### Impact Analysis
- **If Accepted (default)**: All 6 Anthropic skills remain selected under verified Apache-2.0 terms.
- **If Rejected**: 6 slots across Modules 1, 2, and 6 would need to be replaced with community alternates.

---

## Summary of Decisions

| Decision Item | Default State | Slots Affected | Recommended Next Step |
|---|---|:---:|---|
| **CC-BY-SA-4.0** | Disallowed (Quarantined) | 0 selected (98 in quarantine) | Decide whether ShareAlike terms are acceptable for internal skills. |
| **MPL-2.0** | Allowed | 1 selected (`terraform-policy`) | Confirm MPL-2.0 file-level copyleft is acceptable for policy tooling. |
| **Unlicensed Repos** | Quarantined | 0 selected (75 in quarantine) | Open GitHub PRs/issues on upstream repos requesting MIT license files. |
| **Anthropic Apache-2.0** | Allowed | 6 selected | Confirm folder-level `LICENSE.txt` precedence is approved. |

