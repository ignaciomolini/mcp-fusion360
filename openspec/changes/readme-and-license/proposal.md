# Proposal: README and LICENSE

## Intent

`mcp-fusion360` has no `README.md` and no `LICENSE` file at the project root. A peer review against three comparable Fusion 360 MCP servers (Joe-Spencer, AuraFriday, ArchimedesCrypto) flagged both gaps as blockers for going public — a fresh clone leaves the user with no install steps, no tool reference, and ambiguous legal status. The previous change (`face-index-and-runtime-coverage`, archived 2026-06-24) explicitly deferred this work ("README/LICENSE work (separate change)"); this proposal closes that deferral.

Two deliverables, two new files at the project root: a `README.md` that documents install, configuration, architecture, and the 11 MCP tools; and a `LICENSE` that names the legal terms before any external contribution is invited.

## Scope

### In Scope
- `README.md` at project root, English, ~150–250 lines, 12 sections
- `LICENSE` at project root — **MIT or Apache-2.0** (decision required; see Open Questions)
- License copyright line (e.g. `Copyright (c) 2026 <holder>`)

### Out of Scope
- Any code change in Component A (Python add-in) or Component B (TS MCP server) — frozen after `face-index-and-runtime-coverage`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS` (follow-up change)
- CI/CD, GitHub Actions, Docker, issue/PR templates
- Translations (English only) and visual assets (logos, banners, badges beyond an optional license/version badge)

## Capabilities

### New Capabilities
None — documentation files are not behavioral contracts and do not introduce new spec-level requirements.

### Modified Capabilities
None — no spec-level requirements change.

## Approach

**`README.md` — 12 sections in order**: (1) title + one-line description · (2) optional license/version badge · (3) "What it does" (1–2 paragraphs: value proposition + target user: AI agents driving Fusion 360 via MCP) · (4) Architecture (Component A = Fusion add-in + local HTTP server, Component B = stdio MCP wrapper, bridge = JSON-RPC 2.0 over `127.0.0.1:9876`) · (5) Tools list (11 tools grouped by 4 capabilities) · (6) Install (clone → `npm install` in `mcp-server/` → copy `Fusion360MCP/` into Fusion's AddIns folder) · (7) Configuration (working MCP client JSON for Claude Desktop, Cursor, OpenCode) · (8) Usage (one concrete tool-call example) · (9) Development (project layout: `Fusion360MCP/`, `mcp-server/`, `openspec/`) · (10) Testing (Vitest for Component B; `openspec/changes/.../manual-test-checklist.md` for Component A) · (11) License (link to `LICENSE`) · (12) Acknowledgments (credit Joe-Spencer, AuraFriday, ArchimedesCrypto as prior art).

**Tool list (11 tools, drawn from `openspec/specs/`)**:

| Capability | Tools |
|------------|-------|
| `parameter-management` | `get_active_design_parameters`, `update_user_parameter` |
| `design-introspection` | `get_body_info`, `get_document_info`, `list_bodies`, `list_features`, `list_sketches` |
| `cutout-modeling` | `create_circular_cutout`, `create_rectangular_cutout`, `create_slot_cutout` |
| `geometry-analysis` | `measure_clearance` |

**`LICENSE`**: unmodified SPDX text, with the holder name from Open Question 2. Format: `Copyright (c) 2026 <holder>. Licensed under <SPID>.` — the holder name is the only project-specific line.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | New | Entry point for new users and contributors |
| `LICENSE` | New | Legal terms for reuse and contribution |

No other files touched. No `openspec/specs/` deltas; no `mcp-server/src/` or `Fusion360MCP/` edits.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| MIT grants no patent protection — friction for corporate users in patent-sensitive (Autodesk IP) contexts. | Medium | Apache-2.0 alternative surfaced in Open Question 1; user picks. |
| Apache-2.0 adds ~200 lines of legalese for a small project. | Low | Tradeoff is the explicit patent grant + contributor license; standard for similar MCP servers. |
| Copyright holder name unknown — `LICENSE` cannot be written without it. | High (process) | Surfaced as Open Question 2; blocks `sdd-apply` for `LICENSE`. |
| README tool list drifts from implementation as new tools land in future changes. | Medium | Reference `openspec/specs/` as the source of truth; README section is a snapshot, not a contract. |
| Stale Spanish `prd.md` at the repo root may confuse new users who see it before the README renders. | Low | README mentions the PRD exists and that it is in Spanish; does not link prominently. |
| MIT path lands at ~169 lines; Apache-2.0 path lands at ~450 lines (50 over the 400-line review budget). | Low | If user wants strict ≤400, the README can trim Acknowledgments + Usage; otherwise accept overage per the `face-index-and-runtime-coverage` precedent. |

## Rollback Plan

1. Delete `README.md` and `LICENSE` from the project root.
2. No other artifacts were modified — no spec, design, code, or test rollback needed.

## Dependencies

- **User decision on license** (MIT vs Apache-2.0) — Open Question 1
- **User decision on copyright holder name** — Open Question 2
- Both decisions required before `sdd-apply` writes the files

## Success Criteria

- [ ] `README.md` exists at project root, English, with the 12 sections in the agreed order
- [ ] `README.md` lists all 11 MCP tools, grouped by the 4 capabilities, with one-line input/output shape per tool
- [ ] `README.md` includes working MCP client configuration JSON for at least Claude Desktop
- [ ] `LICENSE` exists at project root, contains the chosen license text (MIT or Apache-2.0) and a copyright line
- [ ] No code, spec, design, or test files modified

## Size Forecast

| File | Lines | Note |
|------|-------|------|
| `README.md` | ~150–250 | 12 sections, 11 tool entries, 3 MCP client config examples |
| `LICENSE` (MIT) | ~19 | SPDX text, year + holder |
| `LICENSE` (Apache-2.0) | ~200 | SPDX text, year + holder |
| **Total (MIT)** | **~169** | **Well under 400-line review budget** |
| **Total (Apache-2.0)** | **~350–450** | **50-line overage possible if README runs long; trim or accept** |

**Budget check**: MIT path lands at ~169 lines (well under 400). Apache-2.0 path lands at ~350–450 lines depending on README length; the 50-line overage (if any) is the legal text, not the documentation. If the user wants strict ≤400 on the Apache-2.0 path, the README can drop the optional badge and trim Acknowledgments to a single line. No chained PR needed under either license.

## Open Questions (Proposal Question Round)

Two product/PRD questions to resolve before `sdd-apply` writes the files. Both are decision gaps that make the proposal ambiguous if left unanswered; the `sdd-apply` phase for `LICENSE` is blocked on them, the `README.md` is not.

1. **License choice — MIT or Apache-2.0?**
   - **MIT** (~19 lines): maximum permissiveness, what most small MCP servers use. No patent grant.
   - **Apache-2.0** (~200 lines): adds explicit patent grant and a contributor license. Standard for projects that may be adopted in corporate / patent-sensitive environments; the Autodesk IP context makes this relevant.
   - Peer review recommended MIT for adoption or Apache-2.0 for patent protection. **Decision required.**

2. **Copyright holder name**? Both MIT and Apache-2.0 require a copyright line (e.g. `Copyright (c) 2026 <name>`). The previous proposals reference "the user" but do not name them. Is the holder `<your-name>`, the GitHub handle, or `mcp-fusion360 contributors`? **Decision required.**
