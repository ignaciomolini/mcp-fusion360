# Tasks: Face Index and Runtime Coverage

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~280-345 (8 files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Component B — Vitest Cases

- [x] **1.1** `mcp-server/src/tools.test.ts` — 4 Zod cases for `FaceSelectorSchema`: empty `{}` rejected, normal-only, centroid-only, `tolerance_degrees` defaults to 5. AC: 4 vitest passes.
- [x] **1.2** `mcp-server/src/tools.test.ts` — 3 cases: circular/rectangular/slot forward `face_selector` to `client.call`. Deps: 1.1. AC: pre-existing cutout cases still pass.

## Phase 2: Component B — Types, Schema, Descriptions

- [x] **2.1** `mcp-server/src/types.ts` — Add `FaceGeometry` (`{index, normal, centroid, area_mm2}`) and `FaceSelector` (`{normal?, centroid?, tolerance_degrees?, tolerance_mm?}`). Extend `BodyInfo` with `faces?: FaceGeometry[]` and `faces_truncated?: boolean`. AC: `npm run typecheck` passes.
- [x] **2.2** `mcp-server/src/tools.ts` — Add `FaceSelectorSchema` with `.refine(v => v.normal || v.centroid)`. Thread `face_selector?` into 3 cutout shapes; make `face_index` optional. Deps: 2.1. AC: `{normal: {x:0,y:0,z:1}}` succeeds; `{}` fails.
- [x] **2.3** `mcp-server/src/index.ts` — Append `" Use \`face_selector\` instead (preferred)."` to 3 cutout tool descriptions (lines 62, 69, 76). Deps: 2.2. AC: `tools/list` shows suffix; no `adsk` import.
- [x] **2.4** Run `npm test` from `mcp-server/`. Deps: 1.1, 1.2, 2.1, 2.2, 2.3. AC: all cases pass.

## Phase 3: Component A — Helpers in `tools.py`

- [x] **3.1** `Fusion360MCP/tools.py` — Add `MAX_FACES_ENUMERATED = 100` and `_face_normal_at(face, centroid)`. Normal via `face.evaluator.getNormalAtPoint(centroid)` in `try/except`; on failure `app.log(...)`, return `None`. AC: only imports `adsk.core`; `None` for non-analytic faces.
- [x] **3.2** `Fusion360MCP/tools.py` — Add `resolve_face(body, face_index=None, face_selector=None)` implementing the 5-row "Face Resolution Order" table. Deps: 3.1. AC: traces all 5 rows correctly.

## Phase 4: Component A — Per-Face Enumeration

- [x] **4.1** `Fusion360MCP/handlers.py` — Extend `handle_get_body_info` (line 702) with per-face enumeration per the 4 ADDED scenarios. Deps: 3.1. AC: matches those 4 scenarios.

## Phase 5: Component A — Wire `resolve_face` Into Cutout Handlers

- [x] **5.1** `Fusion360MCP/handlers.py` — Update `handle_create_circular_cutout` (line 319) to call `resolve_face` instead of `body.faces.item(face_idx - 1)` (line 352). Deps: 3.2, 4.1. AC: `face_index: 1` produces same cutout; selector resolves.
- [x] **5.2** `Fusion360MCP/handlers.py` — Same for `handle_create_rectangular_cutout` (lines 370, 408). Deps: 5.1. AC: `angle_deg` rotation still works.
- [x] **5.3** `Fusion360MCP/handlers.py` — Same for `handle_create_slot_cutout` (lines 465, 514). Deps: 5.2. AC: `length_mm > width_mm` validation still triggers.

## Phase 6: Manual Test Plan and Verify

- [x] **6.1** `openspec/changes/face-index-and-runtime-coverage/manual-test-checklist.md` — New file. 3 rows: A1 (install), A2 (start, confirm log), F3 (MCP Inspector `get_active_design_parameters`). Each row: preconditions, steps, expected evidence, status `[ ]` → `[x] PASS`/`[x] FAIL`. AC: mirrors `fusion360-mcp-server/manual-test-checklist.md` format.
- [x] **6.2** **MANUAL** — User runs A1, A2, F3 inside Fusion 360. Deps: 5.3, 6.1. AC: each row has status + one-line evidence; cannot be automated.
- [x] **6.3** `openspec/changes/fusion360-mcp-server/verify-report.md` — Re-mark A1, A2, F3 and 3 cutout scenarios as `[x] PASS`/`[x] FAIL` with evidence. Append Changelog entry. Deps: 6.2. AC: 6 rows updated; Changelog added.

---

> **Note (2026-06-24, archive phase)**: All 15 tasks marked complete by the `sdd-archive` sub-agent as an exceptional stale-checkbox reconciliation. The verify-report at `openspec/changes/face-index-and-runtime-coverage/verify-report.md` proves every task is complete: 20/20 Vitest cases pass, all 8 ADDED spec scenarios implemented, A1/A2/F3 PASS with user-supplied runtime evidence. The `sdd-apply` phase stopped at 6.1 without marking checkboxes; task 6.3 (the verify-report update on the previous change) is being executed as part of this `sdd-archive` call per the orchestrator's explicit instruction. Full reconciliation reason recorded in the archive report.
