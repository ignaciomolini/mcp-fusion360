# Tasks: README and LICENSE

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~200-240 (2 new files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: LICENSE

- [x] **1.1** `LICENSE` — MIT SPDX text. Project-specific line: `Copyright (c) 2026 Ignacio Molini` (inserted per SPDX standard). Holder matches `Fusion360MCP.manifest:5`. 19 lines ±2, SPDX verbatim, copyright present.

## Phase 2: README Header (Sections 1-2)

- [x] **2.1** `README.md` — H1 `mcp-fusion360` + one-line tagline, then H2 `What it does`: 2 paragraphs (value prop + target user). No badges, no placeholders.

## Phase 3: Architecture (Section 3)

- [x] **3.1** `README.md` — H2 `Architecture` with diagram: MCP client → stdio → `mcp-server/` → HTTP POST `127.0.0.1:9876` → `Fusion360MCP.py` add-in → Fusion via `RequestBridge`. No invented files.

## Phase 4: Tools List (Section 4) — Critical

- [x] **4.1** `README.md` — H2 `Tools`, 4 H3 groups, 11 tools. `parameter-management`: `get_active_design_parameters`, `update_user_parameter`. `design-introspection`: `get_body_info`, `get_document_info`, `list_bodies`, `list_features`, `list_sketches`. `cutout-modeling`: `create_circular_cutout`, `create_rectangular_cutout`, `create_slot_cutout` — document BOTH `face_index` and `face_selector`. `geometry-analysis`: `measure_clearance` with footnote (spec not promoted). 4 H3, 11 tools, `face_selector` in 3 cutouts, footnote present.

## Phase 5: Install (Section 5)

- [x] **5.1** `README.md` — H2 `Install`, 4 steps: clone; `cd mcp-server && npm install && npm run build`; copy `Fusion360MCP/` to AddIns (Win `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`, Mac `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns\`); `Tools → Add-Ins → Scripts and Add-Ins` → Run. `runOnStartup: false`. 4 steps, both OS paths present.

## Phase 6: Configuration (Section 6)

- [x] **6.1** `README.md` — H2 `Configuration` with 3 fenced JSON `mcpServers` blocks (Claude Desktop, Cursor, OpenCode). Each: `command: "node"` + `args: ["<abs path>/mcp-server/dist/index.js"]`; placeholder path. 3 valid JSON, all use `dist/index.js`.

## Phase 7: Usage (Section 7)

- [x] **7.1** `README.md` — H2 `Usage` with one example: open Fusion with a body, call `list_bodies` then `get_body_info({body_name: "Plate"})`. Fenced user-message block (NOT `curl`). Real tool names, input matches Zod.

## Phase 8: Development (Section 8)

- [x] **8.1** `README.md` — H2 `Development` with project tree (`Fusion360MCP/`, `mcp-server/`, `openspec/`, `prd.md`) + build commands table (`npm run build` → `dist/`; `npm run typecheck` → no emit; `npm run test` → Vitest). `prd.md` Spanish/legacy; Component A has no build step. 4 tree entries, commands match `package.json`.

## Phase 9: Testing (Section 9)

- [x] **9.1** `README.md` — H2 `Testing`, 2-row table: Component B (Vitest via `npm run test`, covers `mcp-server/src/tools.test.ts`); Component A (manual gate via `openspec/changes/<name>/manual-test-checklist.md`). Honest re Component A, link checklist.

## Phase 10: License Section (Section 10)

- [x] **10.1** `README.md` — H2 `License`: `MIT — see [LICENSE](./LICENSE) for the full text.` Relative link `./LICENSE`.

## Phase 11: Final Review

- [x] **11.1** `README.md` — End-to-end: 10 H2 sections (no Status, no Acknowledgments), 11 tool names, 2/5/3/1 split, `face_selector` in 3 cutouts, `measure_clearance` footnote, no fake badges/TODO/curl. Verify: `^## ` count = 10; `TODO|FIXME|XXX` = 0; line count ≤270.
