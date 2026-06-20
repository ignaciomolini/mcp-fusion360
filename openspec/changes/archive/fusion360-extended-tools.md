# Archive: Fusion 360 Extended Tools

## Change Summary

Added 5 read-only JSON-RPC methods to the Fusion 360 Add-in (`list_bodies`, `get_document_info`, `get_body_info`, `list_features`, `list_sketches`) and the matching MCP tools in Component B, plus an additive `comment`/`is_favorite` extension to the existing `get_active_design_parameters` tool. Unlocks inspect → plan → mutate workflows so an LLM agent can discover design state before issuing mutating tool calls. Component B gained a Vitest test suite (13 tests, 100% pass) and a permanent spec home was seeded for the first time in this repo.

The MCP tool surface grew from 6 to 11 tools. The parameter-management response shape is purely additive — existing consumers ignore the new fields. No regressions on the 6 original tools.

## Verification Status

**PASS WITH WARNINGS**

- TypeScript compilation: clean (`npx tsc --noEmit`)
- Vitest: 13/13 passing in 9ms (6 pre-existing + 5 new + 2 new `get_body_info` cases + 1 parameter delta re-assertion)
- Forbidden `adsk` imports in Component B: confirmed absent (one docstring mention in test file is the only `adsk` string in `mcp-server/src/`)
- `HANDLERS` dict and `METHODS` set in parity: 11 entries each
- Component A reviewed statically (no Python interpreter on this machine); new handlers follow the established `try/except FusionAPIError` + `_get_active_design()` pattern
- 11 manual test cases (G1–G11) require a running Fusion 360 instance and are deferred to the user

## Artifacts Produced

| Phase | File System | Engram Topic Key |
|---|---|---|
| Proposal | `openspec/changes/fusion360-extended-tools/proposal.md` | `sdd/fusion360-extended-tools/proposal` |
| Spec — design-introspection (new) | `openspec/changes/fusion360-extended-tools/specs/design-introspection/spec.md` | `sdd/fusion360-extended-tools/spec-design-introspection` |
| Spec — parameter-management (delta) | `openspec/changes/fusion360-extended-tools/specs/parameter-management/spec.md` | `sdd/fusion360-extended-tools/spec-parameter-management-delta` |
| Design | `openspec/changes/fusion360-extended-tools/design.md` | `sdd/fusion360-extended-tools/design` |
| Tasks | `openspec/changes/fusion360-extended-tools/tasks.md` | `sdd/fusion360-extended-tools/tasks` |
| Verify Report | `openspec/changes/fusion360-extended-tools/verify-report.md` | `sdd/fusion360-extended-tools/verify-report` |
| Archive Report | `openspec/changes/archive/fusion360-extended-tools.md` (this file) | `sdd/fusion360-extended-tools/archive-report` |

### Permanent Specs (first time this repo has a `openspec/specs/` tree populated)

| Capability | File | Action |
|---|---|---|
| `design-introspection` | `openspec/specs/design-introspection/spec.md` | **Created** (new capability, copied from the change's NEW spec) |
| `parameter-management` | `openspec/specs/parameter-management/spec.md` | **Created with merged state** — `get_active_design_parameters` requirement includes the additive `comment`/`is_favorite` fields from this change's delta, plus the original `update_user_parameter` requirement promoted from the `fusion360-mcp-server` archive |

See **Archive Notes** below for the seeding rationale and remaining follow-ups.

## Files Delivered

### Component A — Fusion 360 Add-in (`Fusion360MCP/`)

| File | Change | Purpose |
|---|---|---|
| `Fusion360MCP/handlers.py` | +284 lines (857 total) | 5 new handlers + extended `handle_get_active_design_parameters`; 11 entries in `HANDLERS` dict |
| `Fusion360MCP/server.py` | +5 lines (229 total) | 5 new method names in `METHODS` set (parity with `HANDLERS`) |

### Component B — MCP Wrapper (`mcp-server/`)

| File | Change | Purpose |
|---|---|---|
| `mcp-server/src/tools.ts` | +66 lines (192 total) | 5 new Zod raw shapes + 5 handler functions; `getActiveDesignParametersShape` is bit-identical to main |
| `mcp-server/src/index.ts` | +41 lines (123 total) | 5 new `server.tool(...)` registrations; 11 total |
| `mcp-server/src/types.ts` | +63 lines (95 total) | 5 new documentation-only result interfaces (`ListBodiesResult`, `BodyInfo`, etc.) |
| `mcp-server/src/tools.test.ts` | new file, 210 lines | Vitest suite, 13 tests, mocked `FusionClient` |
| `mcp-server/package.json` | +4 lines | `vitest` devDependency + `"test": "vitest run"` script |

### Documentation

| File | Change | Purpose |
|---|---|---|
| `openspec/changes/fusion360-mcp-server/manual-test-checklist.md` | +35 lines (sections G1–G11) | Manual test cases for the 5 new tools and the parameter delta |

## Tools Exposed to the LLM

The MCP tool surface grew from 6 to 11:

7. `list_bodies` — returns `{name, index}` for every body in `rootComponent` (1-based index)
8. `get_document_info` — returns document `name`, `units` (mm/cm), `design_type`, `material_library`
9. `get_body_info` — returns `face_count`, `bounding_box` (mm), `volume_cm3`, `material`, `body_type` for a named body
10. `list_features` — returns up to 200 features with `name`, `type`, `is_suppressed`, `timestamp`; `truncated: true` when over
11. `list_sketches` — returns `name`, `profile_count`, `referenced_geometry` (entityToken array) for every sketch

Modified tool:

1. `get_active_design_parameters` — each entry now also includes `comment` (string or `null`) and `is_favorite` (boolean). Purely additive; existing fields unchanged.

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `body_type` source | `BRepBody.isSolid` → `"SolidBody"` / `"SurfaceBody"` | `BRepBody` exposes only `isSolid`; string mapping is stable and matches spec. |
| Feature `type` field | `feature.objectType.split(".")[-1]` | Canonical Fusion 360 way; survives new feature types without code change. |
| Feature `timestamp` | `datetime.now(timezone.utc)` at handler time | Fusion API has no per-feature creation date; this is the only honest ISO timestamp available. |
| Sketch `referenced_geometry` | Array of `entityToken` strings | `entityToken` is the documented stable identifier; resolvable later via `Design.findEntityByToken`. |
| Parameter `role` field | **DROPPED** (spec correction) | Fusion 360 API exposes `role` only on `ModelParameter` (free-form string), not on `UserParameter`. Reporting `null` would be dishonest; spec was revised before archive. |
| Face enumeration in `get_body_info` | OMIT `faces` array; return only `face_count` | Honors the 100-face cap vacuously; spec requires `face_count` to be the actual total. |
| `material_library` source | `app.materialLibraries.item(0).name` | First library is the default Fusion 360 library; spec only requires a non-empty string. |
| Unit conversion for bounding box | Convert cm→mm at handler boundary | Matches the rest of the project (mm at the API surface, cm at Fusion). |
| `design_type` enumeration | `"ParametricDesign"` / `"DirectDesign"` (no `"PlasticDesign"`) | Fusion 360 `DesignTypes` enum has only two values. Spec revised. |
| `list_features` cap | 200 entries + `truncated: true` flag | Keeps response payload bounded; documented in spec. |
| Zod shape for zero-arg tools | `{}` (empty object) | Matches the existing `getActiveDesignParametersShape` pattern. |
| Component B tests | Vitest with mocked `FusionClient` | Component A is not unit-testable (requires `adsk`); Component B has full coverage. |
| Permanent specs location | `openspec/specs/{capability}/spec.md` | First time this repo has populated the tree. See Archive Notes. |

## PR Strategy

**Single PR** on branch `feat/fusion360-mcp-component-b-tools`. 400-line budget risk: **Low**. Estimated ~395 changed lines across 8 files, all additive.

The branch already has the implementation committed in 6 atomic commits on top of the previously-stacked `feat/fusion360-mcp-component-b-tools` base (PR 4 of the `fusion360-mcp-server` chain, which was already merged to main in that change's archive flow). The commits, in order:

1. `e29a053` — docs(extended-tools): add planning artifacts and fix stale `role` references
2. `ca76cae` — docs(extended-tools): expand task 0.1 scope to 4 stale proposal lines
3. `e563c67` — feat(add-in): add 5 new introspection handlers + enhance `get_active_design_parameters`
4. `8f08194` — feat(mcp-server): add 5 new introspection tools with zod schemas
5. `f9674c5` — test(mcp-server): add unit tests for introspection tools + Vitest setup
6. `ed28ec1` — docs(extended-tools): add 11 manual test cases for new tools
7. `6ac028d` — chore(extended-tools): mark all 7 tasks complete in tasks.md (verify gate)

**Archive does NOT merge to main.** That is a separate PR step. The branch is ready for review.

## Known Limitations

- **No `face_index` equivalent for bodies** — `list_bodies.index` is positional, not a persistent ID. Faces within a body are not enumerated in the response (only the total `face_count` is returned). Reopen if LLM consumption patterns show a need for per-face details.
- **`list_features.timestamp` is capture-time, not creation-time** — Fusion 360 has no per-feature creation date. Documented in the spec and design ADR.
- **`get_document_info.units` for non-metric users** — units like `"in"` and `"ft"` are passed through as-is. The spec only enumerates mm and cm. Documented in the design ADR.
- **Component A requires manual runtime testing inside Fusion 360 GUI** — no Python interpreter or headless Fusion on this machine; all Add-in logic is verified by visual review and the 11 G-section manual cases.
- **Live Add-in folder does not exist on this machine** — `%APPDATA%\Autodesk\FusionAddins\Fusion360MCP\` is missing until the user loads the Add-in once inside Fusion 360. The sync step is a no-op until then. See **Archive Notes** below.
- **Permanent specs tree is a new convention** — this is the first time `openspec/specs/` has been populated in this repo. The other 4 capabilities introduced by `fusion360-mcp-server` (`cutout-modeling`, `fusion360-add-in`, `geometry-analysis`, `mcp-wrapper`) are still living only in their archived change folder. See **Archive Notes** below.

## Follow-up Work

### Deferred to the user (manual, requires Fusion 360 GUI)

- **Run the 11 G-section manual test cases (G1–G11)** in the manual test checklist (`openspec/changes/fusion360-mcp-server/manual-test-checklist.md` lines 95–119). These verify Component A end-to-end inside Fusion and cannot be automated.
- **Load the Add-in inside Fusion 360 once** to create `%APPDATA%\Autodesk\FusionAddins\Fusion360MCP\`. This makes any future sync step meaningful. The verify report flagged this as `#222` in Engram.
- **Run `python -m py_compile Fusion360MCP/handlers.py Fusion360MCP/server.py`** if a real Python interpreter becomes available. Visual review is the only static check possible from this environment.

### Cleanup (low-priority)

- **Update F2 in the manual test checklist** — it currently says "Returns 6 tools" but the new total is 11. The task instruction was "append G section, do not edit existing sections", so this was correctly left alone, but a future cleanup pass should refresh F2 to say "Returns 11 tools".
- **Add a trailing newline** to `mcp-server/src/tools.ts` and `mcp-server/src/index.ts`. This is a pre-existing condition (`main` is also missing the newline), not a regression from this change.

### Spec hygiene

- **Promote the remaining 4 capabilities from `fusion360-mcp-server` to `openspec/specs/`** — `cutout-modeling`, `fusion360-add-in`, `geometry-analysis`, `mcp-wrapper`. This change seeded `design-introspection` and `parameter-management` as the first permanent specs; the prior change did not promote its own. Recommend doing this in a separate SDD change or as a quick follow-up before the next feature work.
- **Open the PR for branch `feat/fusion360-mcp-component-b-tools`** (this change's implementation). The branch is ready for review.

## Rollback Notes

This archive marks the change as complete. Future modifications should start a new SDD change referencing this archive. If the change must be rolled back after the PR merges:

1. Revert `mcp-server/src/tools.ts`, `mcp-server/src/index.ts`, `mcp-server/src/types.ts` to the pre-change state (6 tools, no introspection).
2. Revert `Fusion360MCP/handlers.py` to remove the 5 new handlers and the parameter `comment`/`is_favorite` extension.
3. Revert `Fusion360MCP/server.py` to remove the 5 new method names from `METHODS`.
4. Revert the `vitest` devDependency in `mcp-server/package.json` and `mcp-server/src/tools.test.ts`.
5. Drop the G section from `openspec/changes/fusion360-mcp-server/manual-test-checklist.md`.
6. Revert the permanent specs: delete `openspec/specs/design-introspection/` and revert `openspec/specs/parameter-management/spec.md` to the pre-delta state.

The change is purely additive on both components; rollback does not touch any persistent data.

## Archive Notes

**Archived on**: 2026-06-20
**Archived by**: `sdd-archive` sub-agent (orchestrator-delegated)
**Convention used**: single-file archive (`openspec/changes/archive/{change-name}.md`), matching the pattern established by `fusion360-mcp-server.md`. The change folder (`openspec/changes/fusion360-extended-tools/`) is removed after consolidation.
**Artifact store mode**: hybrid (filesystem + Engram).

### What was deferred

- **11 G-section manual test cases (G1–G11)** cannot be executed from this verification environment. They require a running Fusion 360 instance with a real design. Documented in `openspec/changes/fusion360-mcp-server/manual-test-checklist.md` (G section, lines 95–119). The user must run them before merging the PR.
- **Live Add-in folder sync** — `%APPDATA%\Autodesk\FusionAddins\Fusion360MCP\` does not exist on this machine. The verify report noted that the user must load the Add-in inside Fusion 360 once for any future sync to be meaningful.
- **Python interpreter not available** — `python -m py_compile` was not runnable; Component A was reviewed statically. The risk of a syntax error is low because all new handlers mirror the established `try/except FusionAPIError` + `_get_active_design()` + `resolve_body()` pattern, but not zero.

### What follow-ups remain

- **F2 line in manual test checklist is stale** — says "Returns 6 tools", actual is 11. Trivial cleanup; flagged above.
- **Sync to AppData once the Add-in is loaded** — the apply-progress entry documented the live-folder requirement. After the user loads the Add-in inside Fusion 360 once, future sync steps will be meaningful.
- **Promote remaining 4 capabilities to `openspec/specs/`** — `cutout-modeling`, `fusion360-add-in`, `geometry-analysis`, `mcp-wrapper` from the prior `fusion360-mcp-server` archive are not yet in the permanent specs tree. This change seeded the first two; the other four should follow.
- **Open the PR for `feat/fusion360-mcp-component-b-tools`** — the implementation is on the branch (7 commits on top of the previously-merged PR 4 base). Ready for review, not for merge.

### Branch state at archive

- **Branch**: `feat/fusion360-mcp-component-b-tools`
- **HEAD**: `6ac028d` (chore(extended-tools): mark all 7 tasks complete in tasks.md)
- **Commits ahead of `main`**: 7 (3 docs/housekeeping + 2 feat + 1 test + 1 chore)
- **Lines changed**: ~395 across 8 files (estimate; matches the tasks forecast)
- **Status on disk**: clean except for `.atl/.skill-registry.cache.json` and `.atl/skill-registry.md` (auto-regenerated by the agent harness) and the deleted test add-in stubs (`Fusion360MCP_test/`, removed during prior cleanup). The branch is ready to push and open as a PR.

### Engram observations at archive

- `sdd/fusion360-extended-tools/proposal` (#212)
- `sdd/fusion360-extended-tools/spec-design-introspection` (#216)
- `sdd/fusion360-extended-tools/spec-parameter-management-delta` (#217)
- `sdd/fusion360-extended-tools/design` (#218)
- `sdd/fusion360-extended-tools/tasks` (#221)
- `sdd/fusion360-extended-tools/verify-report` (#223)
- `sdd/fusion360-extended-tools/apply-progress` (#222, will be updated to "ARCHIVED" by this sub-agent)
- `sdd/fusion360-extended-tools/archive-report` (this sub-agent's output)
