# Design: README and LICENSE

Two new files at the project root: `README.md` (entry point for new users, ~150–250 lines, 12 sections) and `LICENSE` (MIT, ~19 lines). No code, spec, or test files touched. Content is derived strictly from existing artifacts in the repo — tool list from `openspec/specs/` (3 capabilities) plus `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (the 4th, still living in its change folder), install steps from the actual add-in structure, MCP client configs from real command paths.

## Technical Approach

Two deliverables, both pure documentation. `LICENSE` is the unmodified MIT SPDX text with one project-specific line: `Copyright (c) 2026 Ignacio Molini`. `README.md` is a 12-section document in the order specified by the proposal; each section has a clear scope and points back to a source-of-truth file in the repo so the content can be re-derived if any source changes.

No tooling, no scripts, no automation. The author (human or LLM) writes the files directly. The design specifies WHAT goes in each section but does not contain the section bodies — the section bodies are produced in the `sdd-apply` phase per the proposal's separation of concerns.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| README language | English only | Project convention; `prd.md` is Spanish but everything in `mcp-server/`, `Fusion360MCP/`, and `openspec/` is English. |
| Section order | 1–12 fixed per proposal | Order is part of the proposal's contract; do not reorder. |
| Heading hierarchy | H1 title, H2 sections, H3 subsections | Standard for GitHub-flavored Markdown; matches `openspec/changes/.../*.md` style. |
| Tool list grouping | 4 capabilities, 11 tools | Maps 1:1 to the proposal's capability table; gives the reader a mental model. |
| Source of truth for tool list | `openspec/specs/` (3 caps) + `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (1 cap) | `geometry-analysis` is not yet promoted to the permanent specs tree (flagged in `archive/face-index-and-runtime-coverage.md:139`); the README documents what is implemented, not what is permanently spec'd. |
| Install steps | Load add-in via Fusion's Scripts and Add-Ins dialog | This is the only supported add-in installation method for Fusion 360; the add-in is not packaged as `.exe`/`.dmg`/`.vsix`. |
| MCP client config commands | `node dist/index.js` from `mcp-server/` | Matches `package.json` `"main": "dist/index.js"` and `"start": "node dist/index.js"`. The README tells users to run `npm run build` first. |
| Acknowledgments | Yes — credit Joe-Spencer, AuraFriday, ArchimedesCrypto as prior art | The proposal explicitly lists this credit; peer review identified them as comparable servers. |
| No badges | License-only shield, no build/coverage/dependency status | README must not contain unverified badges (no "build passing" without a CI). |
| No screenshots | Text + ASCII diagram only | The proposal rules out visual assets. |
| No TODO items | None in README | Open work belongs in issues, not docs. |
| No Contributing / Security sections | Explicitly out of scope per proposal | Follow-up change. |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Create | Project entry point. 12 sections, English, ~150–250 lines. |
| `LICENSE` | Create | MIT SPDX text with `Copyright (c) 2026 Ignacio Molini`. ~19 lines. |

No other files modified.

## Content Specification

### `LICENSE` (verbatim, ~19 lines)

Full MIT License text, unmodified from the SPDX standard. The only project-specific line is the copyright:

```
Copyright (c) 2026 Ignacio Molini
```

Insert this line directly above `Permission is hereby granted, ...`. No other deviations from the SPDX text. Holder name matches the `author` field in `Fusion360MCP/Fusion360MCP.manifest:5`.

### `README.md` (12 sections, ~150–250 lines)

| # | Heading (H2 unless noted) | Content spec |
|---|---------------------------|--------------|
| H1 | `mcp-fusion360` | Project title + one-line description: "MCP server for AI-driven Fusion 360 operations — translates MCP tool calls into JSON-RPC 2.0 requests against a local add-in." |
| 1 | Title + description (above the H1) | One-line tagline; no separate H2. |
| 2 | Status | Optional line: `[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)`. No build/coverage badges — there is no CI. If omitted, drop the whole section. |
| 3 | What it does | 1–2 paragraphs. Para 1: value proposition (let an LLM drive Fusion 360 via natural language → MCP tool calls). Para 2: target user (developers prototyping AI-driven CAD automation, not end-user designers). |
| 4 | Architecture | ASCII diagram of three components: `MCP client` (Claude Desktop / Cursor / OpenCode) → `stdio` → `mcp-server/` (Component B, Node.js, `@modelcontextprotocol/sdk`) → `HTTP POST 127.0.0.1:9876` → `Fusion360MCP.py` add-in (Component A, Python, `adsk` API) → Fusion main thread via `RequestBridge`. Reference actual files: `mcp-server/src/index.ts`, `Fusion360MCP/Fusion360MCP.py`, `Fusion360MCP/server.py`. |
| 5 | Tools | Sub-headers H3 per capability, 11 tool entries total. Each entry: tool name as inline code, one-line description, input shape as fenced TypeScript block (`{param: type, ...}`), one-line output shape. Group as the proposal specifies. **Source**: see "Source-of-truth references" below. |
| 6 | Install | Step-by-step: (a) clone repo; (b) `cd mcp-server && npm install && npm run build`; (c) copy or symlink the `Fusion360MCP/` directory into Fusion's AddIns folder (Windows: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`; macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`); (d) in Fusion, `Tools → Add-Ins → Scripts and Add-Ins` → Add-Ins tab → select `Fusion360MCP` → Run. Add a "Start on launch" sub-bullet pointing at `runOnStartup: false` in the manifest. |
| 7 | Configuration | Three fenced JSON blocks for `mcpServers` config: Claude Desktop (`claude_desktop_config.json` path), Cursor (`~/.cursor/mcp.json`), OpenCode (project `opencode.json`). Each block uses `command: "node"` and `args: ["<absolute path to>/mcp-server/dist/index.js"]`. Caveat: the absolute path is user-specific; the README shows a placeholder and tells the reader to substitute. |
| 8 | Usage | One concrete example. Recommended: open Fusion 360 with a design containing at least one body, then from the MCP client call `list_bodies` and `get_body_info`. Use the actual tool name and one input param, e.g. `get_body_info({body_name: "Plate"})`. Show the MCP-client side as a fenced code block (a user message, not a `curl` example — `curl` does not speak MCP/stdio). |
| 9 | Development | Project layout tree: `Fusion360MCP/` (Component A: add-in entry, HTTP server, handlers, tools, errors, manifest), `mcp-server/` (Component B: stdio wrapper, JSON-RPC client, Zod schemas, types, errors), `openspec/` (SDD: `specs/`, `changes/`, `config.yaml`), `prd.md` (Spanish PRD, legacy). Build commands table: `npm run build` (TS → `dist/`), `npm run typecheck` (no emit), `npm run test` (Vitest). Component A has no build step — `Fusion360MCP.py` is loaded by Fusion directly. |
| 10 | Testing | Two-column table. Component B: Vitest (`npm run test`); `mcp-server/src/tools.test.ts` covers the 11 handlers. Component A: no unit tests (the `adsk` API is unavailable outside Fusion); manual gate via `openspec/changes/<name>/manual-test-checklist.md` per change; link the convention. |
| 11 | License | One line: `MIT — see [LICENSE](./LICENSE) for the full text.` |
| 12 | Acknowledgments | One sentence per credited project: Joe-Spencer, AuraFriday, ArchimedesCrypto. Frame as "prior art that informed the design", not endorsements. |

## Source-of-truth References

The README must not invent content. Every section maps to a file in the repo:

| Section | Source file(s) |
|---------|----------------|
| 4 Architecture | `Fusion360MCP/server.py:33` (`DEFAULT_PORT = 9876`), `Fusion360MCP/Fusion360MCP.py:1-30` (entry + bridge wiring), `mcp-server/src/index.ts` (stdio server), `mcp-server/package.json:5` (`"type": "module"`) |
| 5 Tools | 10 tools from `openspec/specs/{parameter-management,design-introspection,cutout-modeling}/spec.md`. 1 tool (`measure_clearance`) from `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (see Open Question Q1). Cross-checked against `mcp-server/src/tools.ts:1-221` (the 11 Zod shapes). |
| 6 Install | `Fusion360MCP/Fusion360MCP.manifest:8` (`runOnStartup: false`); Fusion 360 add-in install paths are Autodesk-documented and stable since the Electron migration. |
| 7 Configuration | `mcp-server/package.json:6,9` (`main: "dist/index.js"`, `start: "node dist/index.js"`). MCP client config formats are documented by each client vendor. |
| 9 Development | Directory listings: `Fusion360MCP/` (8 files), `mcp-server/src/` (6 files), `openspec/` (`specs/`, `changes/`, `config.yaml`). |
| 10 Testing | `mcp-server/package.json:11` (`"test": "vitest run"`), `mcp-server/src/tools.test.ts`. |
| 12 Acknowledgments | The proposal names these three; no source file in the repo credits them yet. |

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| R1 `geometry-analysis` not in permanent specs — README references a spec that lives in a change folder | The design is honest about this (see "Source-of-truth references" + Open Question Q1). The README is a snapshot, not a contract; the next `archive` cycle can promote `geometry-analysis`. |
| R2 `face_selector` deprecation in cutout tool descriptions (from `face-index-and-runtime-coverage`) | Each cutout tool entry in Section 5 must document BOTH `face_index` (deprecated) and `face_selector` (preferred). Matches the wording in `mcp-server/src/tools.ts:80,105,134`. |
| R3 Absolute path in MCP client config is user-specific | The README uses a placeholder (`/absolute/path/to/mcp-fusion360/mcp-server/dist/index.js`) and explicitly says "substitute your clone path". Do not embed a real path. |
| R4 `prd.md` is Spanish, will confuse English-only readers | Section 9 lists `prd.md` and notes "(Spanish, legacy)" inline. Do not link it prominently. |
| R5 README tool list drifts from implementation | Marked in the proposal's risk table; README is a snapshot. Re-derive from `openspec/specs/` when adding a tool. The 400-line review budget is for a single change, not a permanent maintenance load. |
| R6 User runs `node dist/index.js` without building first | Section 6 step (b) runs `npm run build` before any other action. Section 7 configs assume `dist/index.js` exists. |

## Testing Strategy

Documentation-only — no unit tests. Sanity checks performed by the README author before `sdd-verify`:

| Check | How |
|-------|-----|
| Render check | Open `README.md` in a Markdown preview (GitHub, VS Code) and confirm H1/H2/H3 hierarchy renders. |
| Link check | All internal links (`./LICENSE`) resolve; no broken `[text]()` placeholders. |
| Tool count | Grep for tool names; the count must be exactly 11. Cross-check against `mcp-server/src/tools.ts`. |
| Capability grouping | Each tool appears under exactly one capability H3. |
| MCP config JSON | All three blocks parse as valid JSON (`node -e "JSON.parse(require('fs').readFileSync('snippet.json'))"`). |
| MIT text | `LICENSE` matches the SPDX standard verbatim except for the copyright line. |
| Section count | 12 H2 sections (Status is optional and counts when present, or is omitted entirely). |

## Migration / Rollout

No migration. Both files are new at the project root. Rollback: `git rm README.md LICENSE`. No spec, design, code, or test artifacts to roll back.

## Open Questions

- **Q1 — `geometry-analysis` source-of-truth**: the proposal claims the tool list is drawn from `openspec/specs/`, but `measure_clearance` lives in `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (not yet promoted to the permanent tree — flagged in `archive/face-index-and-runtime-coverage.md:139` and `archive/fusion360-extended-tools.md:121`). The design references the change-folder spec and notes the gap. **Confirm with user** that documenting an in-flight capability in the README is acceptable, OR promote `geometry-analysis` first as a separate SDD change.
- **Q2 — Acknowledgments phrasing**: the proposal names Joe-Spencer, AuraFriday, ArchimedesCrypto as prior art. The README draft will frame them as comparable servers that informed the design. **Confirm** the framing is acceptable before `sdd-apply` writes the file.
- **Q3 — Optional status badge**: Section 2 (Status) is a single line with a shields.io MIT badge. If the user prefers no badge at all, drop the whole section and renumber (the section count drops from 12 to 11, and the proposal's "12 sections" needs an explicit amendment). **Decide before `sdd-apply`**.

## Size Forecast

| File | Lines | Note |
|------|-------|------|
| `LICENSE` | ~19 | MIT SPDX + copyright line |
| `README.md` | ~150–250 | 12 sections, 11 tool entries, 3 MCP client configs |
| **Total** | **~170–270** | **Under the 400-line review budget** (D1) |

The design artifact itself is ~190 lines, well under the 800-word size budget. No chained PR needed.
