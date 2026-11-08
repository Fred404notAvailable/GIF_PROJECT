# DevCrew Skill Vault — Governance Decisions Needed

This document records the licensing, provenance, and operational policy decisions that require user authorization, the default behavior applied during the audit, and the concrete slot impact for each choice.

Until explicit user direction is provided, the **stricter reading** has been enforced across the vault: **no skill or MCP server is selected unless its verified license is currently listed in `allowed_licenses`**.

---

## 1. Mozilla Public License 2.0 (`MPL-2.0`)

### Context & Cause
`hashicorp/agent-skills.git` and `io.github.hashicorp/terraform-mcp-server` are licensed under `MPL-2.0` (weak copyleft: file-level reciprocal obligations). In the initial repository setup commit `9d3f88e7868d048de347341d94f293fedcf90172` (Sun Nov 8 01:51:03 2026), `MPL-2.0` was inadvertently added to `devcrew.config.yaml` lines 146–151 without user confirmation. This caused `terraform-policy` (HashiCorp) to be selected for slot 92 and `hashicorp-terraform-mcp-server-mcp` to be selected.

### Correction Applied in Round 2
1. **Reverted `allowed_licenses` in `devcrew.config.yaml`**: `MPL-2.0` was removed. The current allowed list is strictly:
   ```yaml
   allowed_licenses:
     - MIT
     - Apache-2.0
     - BSD-3-Clause
     - CC-BY-4.0
   ```
2. **Reverted `terraform-policy` (HashiCorp)**: Status reverted to `unfilled`. Slot 92 is left unfilled. Module 7 selected count is 14/15; total vault selected skills count is 99/100 (shortfall: 1).
3. **Reverted `hashicorp-terraform-mcp-server-mcp`**: Status reverted from `selected` to `candidate`.

### Choices for the User
- **Option A: Allow MPL-2.0**
  - Add `MPL-2.0` to `allowed_licenses` in `devcrew.config.yaml`.
  - **Result**: Slot 92 becomes selected (`terraform-policy`, HashiCorp), bringing total selected skills to 100/100. `hashicorp-terraform-mcp-server-mcp` becomes eligible for selection in Module 7.
  - *Legal Scope*: Safe for modular use; modifications to HashiCorp's own policy files must remain under MPL-2.0, but calling code or adjacent modules are not copylefted.
- **Option B: Keep MPL-2.0 Disallowed (Current Default)**
  - Keep `MPL-2.0` out of `allowed_licenses`.
  - **Result**: Slot 92 remains unfilled (or can be filled from an allowed candidate such as `azure-deployment-preflight` or `terraform-skill`). Zero weak copyleft obligations in the vault.

---

## 2. Creative Commons Attribution-ShareAlike 4.0 (`CC-BY-SA-4.0`)

### Context
`trailofbits/skills.git` (98 security skills) is released under `CC-BY-SA-4.0`. In addition, `netresearch/docker-development-skill.git` contains dual licensing where executable code is MIT but core content/guidance is licensed under `CC-BY-SA-4.0`.

In previous iterations, skills from Trail of Bits (`differential-review`, `variant-analysis`, `sharp-edges`, `supply-chain-risk-auditor`, `agentic-actions-auditor`) were pulled through `antigravity-awesome` (an aggregator repo with an MIT root license) and marked selected, creating a contradiction with the reported quarantine of `trailofbits`.

### Default Applied
- **Strictly Disallowed & Excluded from `selected`**: All CC-BY-SA-4.0 skills have been removed from the selected slots and placed in candidate / quarantine status.
- Replaced in Module 4 (Security) with dedicated MIT/Apache-2.0 alternatives: `secure-webapp` (OWASP Top 10), `security-auditor`, `security-review`, `vulnerability-scanner`, `web-security-testing`, `xss-html-injection`, and `sql-injection-testing`.
- Replaced in Module 7 (DevOps) with `docker-compose-patterns` (Apache-2.0).

### Choices for the User
- **Option A: Approve `CC-BY-SA-4.0`**:
  - Add `CC-BY-SA-4.0` to `allowed_licenses` in `devcrew.config.yaml`.
  - Unlocks **98 high-depth Trail of Bits security skills** and `docker-development`.
  - *Risk / Obligation*: Vault redistributions must preserve attribution and inherit ShareAlike terms.
- **Option B: Maintain Current Disallowed Policy (Current Default)**:
  - **Zero ShareAlike obligations**. 100% of the selected skills remain under permissive licenses (81 MIT, 18 Apache-2.0).

---

## 3. Unlicensed Upstream Repositories

### Context
Several high-utility source repositories lack an upstream `LICENSE` or `LICENSE.txt` file at their root:
1. `better-auth/skills` (6 authentication skills, including Slot 11 `better-auth` and Slot 12 `better-auth-patterns`)
2. `mrgoonie/claudekit-skills` (45 development skills, including Slot 2 `backend-development`)
3. `coreyx/modernstack-skills` (6 full-stack skills, including Slot 28 `svelte`)
4. `jon23d/opencode-configs` (18 DevOps/testing skills)

### Default Applied
- **Quarantined**: Under `on_unknown_license: quarantine`, all **75 packages** from these repositories are held in `DevCrew-Vault/_quarantine/`.
- None are selected. Each contains an automated `REPORT.md` and `.source.json`.
- Slots 11, 12, 2, and 28 are maintained as unfilled or matched to allowed alternatives per Round 3 strict license rules.

### Choices for the User
- **Option A: Await Upstream Licensing (Current Default)**:
  - Keep quarantined until maintainers publish a standard open-source license.
- **Option B: In-House Private Exception**:
  - If licensed privately or for internal use, configure specific repository exceptions in `devcrew.config.yaml`.

---

## 4. MCP Servers Dropped Due to License Gate or Namespace Mismatch

### Context
In Round 3, a strict 3-tier license gate was enforced for all MCP servers:
1. Registry JSON payload `license` field
2. Repository metadata / seed lookup definition
3. Package manifest (`package.json` / `pyproject.toml`)

Servers whose license cannot be verified or is outside `allowed_licenses` (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `CC-BY-4.0`) are strictly demoted to candidate and omitted from `selected`.

### Dropped MCP Servers Register
- **`io.github.hashicorp/terraform-mcp-server`**:
  - *License*: `MPL-2.0` (weak copyleft).
  - *Action*: Demoted to candidate pending user approval of `MPL-2.0`.
- **`io.github.containers/kubernetes-mcp-server`**:
  - *Publisher Verification*: Mismatched namespace (`containers` organization does not represent upstream `kubernetes` / CNCF vendor).
  - *Action*: Demoted to community candidate. Leaves Module 7 with 0 selected servers (shortfall: -7).
- **Unlicensed Registry Packages (59,000+ candidates)**:
  - Over 59,000 registry package versions omit license declarations in their registry payloads and manifests.
  - *Action*: All held at candidate level; only 24 servers with verified allowed licenses and verified vendor/reference status are selected.

---

## Summary of Decisions

| Decision Item | Current State | Affected Items | Action Required |
|---|:---:|---|---|
| **MPL-2.0 License** | **Disallowed** | Slot 92 (`terraform-policy`), Terraform MCP server | Add `MPL-2.0` to `allowed_licenses` in `devcrew.config.yaml` to fill Slot 92 |
| **CC-BY-SA-4.0 License** | **Disallowed** | 98 Trail of Bits skills, `docker-development` | Add `CC-BY-SA-4.0` to `allowed_licenses` to unlock Trail of Bits |
| **Unlicensed Repositories** | **Quarantined** | `better-auth`, `claudekit`, `modernstack` (75 skills) | Await upstream licensing or grant private in-house exception |
| **MCP Server Approvals** | **4 Approved, 20 Pending** | 4 approved servers configured, 20 candidate servers | Review `MCP-APPROVALS-NEEDED.md` to approve remaining servers |
