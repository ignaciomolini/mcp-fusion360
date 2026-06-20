# Tasks: Fusion 360 Extended Tools

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~395 (8 files) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Component A handlers + Component B tools + tests + docs | PR 1 | Base: main. All file groups in one PR; additive changes only; the proposal housekeeping edit goes as a separate commit in the same PR. |

## Phase 0: Housekeeping

- [ ] **0.1** `openspec/changes/fusion360-extended-tools/proposal.md` — Remove the stale `role` token from lines 13, 27, 61, and 68 (all reference `UserParameter.comment/role` or `comment, role, is_favorite`); `UserParameter` has no `role` (only `ModelParameter` does — see design.md ADR). P0. Deps: none. ~4 lines. AC: proposal.md has no remaining `role` references; the only fields referenced for `UserParameter` are `comment` and `is_favorite`.

## Phase 1: Component A (Python Add-in)

- [ ] **1.1** `Fusion360MCP/handlers.py` — Add 5 new handlers, extend `handle_get_active_design_parameters`, register all in `HANDLERS` dict. P0/P1/P2. Deps: 0.1. ~140 lines. AC: each handler matches its design section; parameter handler adds `comment` and `is_favorite` to every entry; `HANDLERS` dict has 11 entries; no `computeAll()` anywhere.
  - `handle_list_bodies` (P0) — iterate `design.rootComponent.bRepBodies` via `bRepBodies.item(i)`, return `{"bodies": [{"name", "index": i+1}]}`; raise `-32002` if no design
  - `handle_get_document_info` (P0) — read `app.activeDocument.name`, `app.activeDocument.unitsManager.defaultLengthUnits` (normalize to `"mm"`/`"cm"`, pass through for other units), `design.designType` (map `ParametricDesignType` → `"ParametricDesign"`, `DirectDesignType` → `"DirectDesign"`), `app.materialLibraries.item(0).name` (fallback `""`)
  - `handle_get_body_info` (P1) — resolve body via existing `resolve_body()`; read `body.faces.count` (actual, not capped), `body.boundingBox.minPoint/maxPoint` (cm→mm via `cm_to_mm`), `body.volume` (cm³), `body.material.name` (null-safe), `body.isSolid` → `"SolidBody"`/`"SurfaceBody"`; raise `-32001` for empty/missing `body_name` or not-found (message: `"Body 'X' not found"`)
  - `handle_list_features` (P2) — iterate `design.rootComponent.features`, derive `type` via `feature.objectType.split(".")[-1]`, read `isSuppressed`; cap at 200 entries; set top-level `truncated: true` when overflow; `timestamp` = `datetime.utcnow().isoformat() + "Z"` at handler time
  - `handle_list_sketches` (P2) — iterate `design.rootComponent.sketches`, return `profile_count` from `sketch.profiles.count`, `referenced_geometry` as array of `sketch.referencePlane.entityToken` strings (or `[]` when null)
  - `handle_get_active_design_parameters` (MODIFIED, P1) — preserve `name`/`expression`/`value`/`unit`; ADD `comment` (`param.comment`, null-safe) and `is_favorite` (`param.isFavorite`, bool)

- [ ] **1.2** `Fusion360MCP/server.py` — Add 5 method names to the `METHODS` set: `list_bodies`, `get_document_info`, `get_body_info`, `list_features`, `list_sketches`. P0. Deps: 1.1. ~5 lines. AC: `METHODS` has 11 entries; unknown method still returns `-32601`; the dispatcher still 405s on non-POST.

## Phase 2: Component B (TypeScript mcp-server)

- [ ] **2.1** `mcp-server/src/tools.ts` — Add 5 Zod raw shapes + 5 handler functions following the `handleGetActiveDesignParameters` pattern. P0/P1/P2. Deps: 1.1, 1.2. ~75 lines. AC: every field has `.describe(...)`; `getBodyInfoShape` uses `z.string().min(1)`; each handler invokes `client.call(method, args)`; no `adsk` import.
  - `listBodiesShape = {}` → `handleListBodies(client)` → `client.call("list_bodies")`
  - `getDocumentInfoShape = {}` → `handleGetDocumentInfo(client)` → `client.call("get_document_info")`
  - `getBodyInfoShape = { body_name: z.string().min(1).describe("Name of the body to inspect (exact match)") }` → `handleGetBodyInfo(client, args)` → `client.call("get_body_info", args)`
  - `listFeaturesShape = {}` → `handleListFeatures(client)` → `client.call("list_features")`
  - `listSketchesShape = {}` → `handleListSketches(client)` → `client.call("list_sketches")`

- [ ] **2.2** `mcp-server/src/index.ts` — Import the 5 new shapes/handlers and register them via `server.tool(name, description, shape?, handler)`. P0. Deps: 2.1. ~30 lines. AC: `tools/list` returns 11 tools; no `adsk` import anywhere in `mcp-server/src/`; `tsc --noEmit` passes; follows the existing registration style (no schema arg for the 4 zero-arg tools, `shape` arg only for `get_body_info`).

- [ ] **2.3** `mcp-server/src/types.ts` — Add optional `BodyInfo` interface (documentation-only; MCP `registerTool` does not require typed results). P2. Deps: 2.1. ~10 lines. AC: file compiles under strict TS.

## Phase 3: Component B Tests (Vitest, mocked FusionClient)

- [ ] **3.1** `mcp-server/package.json` — Add `vitest` as devDependency, add `"test": "vitest run"` script. P1. Deps: none. ~4 lines. AC: `npm install` resolves; `npx vitest run` discovers `src/tools.test.ts`; `tsc --noEmit` still passes (vitest types are in-band).

- [ ] **3.2** `mcp-server/src/tools.test.ts` — New Vitest suite with mocked `FusionClient`. P1. Deps: 2.1, 3.1. ~95 lines. AC: each test asserts the handler calls `client.call(method, expectedArgs)`; tests run in <1s; no Fusion 360 dependency.
  - `list_bodies` → `expect(client.call).toHaveBeenCalledWith("list_bodies", undefined)`
  - `get_document_info` → `expect(client.call).toHaveBeenCalledWith("get_document_info", undefined)`
  - `get_body_info({body_name: "Plate"})` → `expect(client.call).toHaveBeenCalledWith("get_body_info", {body_name: "Plate"})`
  - `list_features` → `expect(client.call).toHaveBeenCalledWith("list_features", undefined)`
  - `list_sketches` → `expect(client.call).toHaveBeenCalledWith("list_sketches", undefined)`
  - `get_active_design_parameters` (delta, P1) → shape unchanged; handler still calls `client.call("get_active_design_parameters")` with no args

## Phase 4: Documentation

- [ ] **4.1** `openspec/changes/fusion360-mcp-server/manual-test-checklist.md` — Append section G with 11 manual test cases G1–G11 (Component A cannot be unit-tested — these verify the new tools inside Fusion). P0. Deps: 2.2. ~35 lines. AC: G1–G11 cover the 5 new tools, the `-32002` cross-cutting case for all 5, and the parameter-management delta; table format matches existing sections.
  - G1 `list_bodies` on "Escritorio" — returns the sheet-of-steel body
  - G2 `list_bodies` on empty design — `{"bodies": []}`
  - G3 `get_document_info` on "Escritorio" — `units: "mm"`, `design_type: "ParametricDesign"`, non-empty `material_library`
  - G4 `get_body_info` with valid body — `face_count`, `bounding_box` in mm, `volume_cm3`, `material`
  - G5 `get_body_info` with missing body — `-32001` `"Body 'X' not found"`
  - G6 `get_body_info` with empty `body_name` — `-32001`
  - G7 `list_features` on design with mixed features — each entry has `name`, `type`, `is_suppressed`, `timestamp`
  - G8 `list_features` with > 200 features — `truncated: true`, array length 200
  - G9 `list_sketches` on design with sketches — each entry has `name`, `profile_count`, `referenced_geometry`
  - G10 All 5 new tools with no design open — `-32002`
  - G11 `get_active_design_parameters` (delta) — each entry has `comment` and `is_favorite` populated
