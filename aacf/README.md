<!-- ═══ AACF VERSION CHECK — AGENTS READ FIRST ═══
This file belongs to a downloaded snapshot of the ATEXIS AI Framework, version 2.0.0.
Before relying on it, verify the snapshot is current:
1. Call the aacf_fetch MCP tool (endpoint http://10.117.139.1:8200/mcp, streamable-http,
   header 'Authorization: Bearer <key>' or 'X-Api-Key: <key>'):
   aacf_fetch({"path": "VERSION"})
2. If the returned version differs from 2.0.0, this snapshot is OUTDATED. Fetch ALL
   framework files fresh via aacf_fetch (start with aacf_fetch({"path": "", "list_dir": true})
   and walk the tree), or ask the user to re-download the framework ZIP from the IdAI
   portal (/propose/framework). Do not mix files from different versions.
3. If you CANNOT reach the aacf_fetch MCP, you MUST tell the user: you cannot reach the
   AACF MCP and may be working with an outdated version of the framework. Then proceed
   with this file as-is.
Verify once per session, not per file.
═══ -->

# ATEXIS AI-Assisted Coding Framework (AACF)

The AACF is the single source of truth for AI-assisted ("vibe coding") development at ATEXIS. It
provides the **guardrails**, a **unified UX design framework**, **security + governance + compliance
controls** (ISO/IEC 27001, GDPR, Secure SDLC), a roster of **specialized agents**, and approved
templates, rules, styles, and prompts — so every project builds on approved components and standards,
not from scratch.

**Start here:** [`AGENTS.md`](AGENTS.md) — the tool-agnostic entry point every AI coding agent reads.

## Directory Structure

```
aacf/
├── AGENTS.md            # ← tool-agnostic entry point (open AGENTS.md standard)
├── rules/               # Hard Rules (HR0–HR21), global/security/AI-safety + language rules (.mdc)
├── agents/              # Specialized agent definitions (planner, reviewers, prompt engineer, hardening)
├── governance/          # Compliance control catalogue, deterministic guardrails, review guidelines, tiers
├── styles/              # Unified design system: tokens, branding, UI kit
├── prompts/             # Approved system prompts and templates
├── templates/           # Project scaffolding templates
└── docs/                # Project & security context, state-of-the-art research
```

## What's inside

| Need | Go to |
|------|-------|
| The non-negotiable engineering rules | [`rules/atexis-hard-rules.md`](rules/atexis-hard-rules.md) (HR0–HR21) |
| Safety for AI-generated code | [`rules/ai-output-safety.mdc`](rules/ai-output-safety.mdc) |
| A unified, consistent UX | [`styles/design-system.md`](styles/design-system.md) |
| Security / governance / compliance controls | [`governance/security-governance-compliance.md`](governance/security-governance-compliance.md) |
| Deterministic enforcement (hooks, gates) | [`governance/guardrails.md`](governance/guardrails.md) |
| Specialized agents & how they compose | [`agents/README.md`](agents/README.md) |
| The research this is built on | [`docs/STATE_OF_THE_ART.md`](docs/STATE_OF_THE_ART.md) |

## Usage

Content is served read-only via the `aacf_fetch` MCP tool; all tiers have access. IdAI imports the
governance/rules docs as reference documents (`POST /idai/reference/import-aacf`). The framework repo
is the golden-path starter — pull it to build on approved components. Framework maintainers update
content via the AACF admin surface in the admin console.

## Versioning

All changes are tracked via git; content versions follow semver. See [`CHANGELOG.md`](CHANGELOG.md).
**Current version: 2.0.0**
