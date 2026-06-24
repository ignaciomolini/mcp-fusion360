# Proposal: Face Index and Runtime Coverage

## Intent

Two gaps from the peer review of `mcp-fusion360` against three comparable servers (Joe-Spencer, AuraFriday, ArchimedesCrypto) and the archived verify report.

**face_index fragility**: the three cutout tools take a 1-based `face_index: int` referencing `BRepBody.faces` by ordinal, and face order is not stable across edits (verify-report line 234, archive-report line 89). Fix: enrich `get_body_info` with per-face geometry (normal, centroid, area) and add an optional `face_selector` so an LLM picks a face by intent, not ordinal.

**runtime coverage**: 24 of 45 spec scenarios are `UNTESTED` (verify-report line 194). This change closes the three highest-priority ones — **A1** (install), **A2** (start), **F3** (`get_active_design_parameters` E2E) — exercising the full add-in → HTTP → MCP path.

## Scope

### In Scope
- Add `faces: [{index, normal: {x,y,z}, centroid: {x,y,z}, area_mm2}]` to `get_body_info`, capped at 100 entries
- Add optional `face_selector` to the three cutout tools (normal vector + nearest-centroid tiebreaker)
- Keep `face_index` working unchanged; deprecate, do not remove
- Execute A1, A2, F3 inside Fusion 360; record results in the manual-test-checklist
- Update the verify report with the new runtime evidence
- Component B: extend Zod schemas, add types, add Vitest cases for the new shape and selector path

### Out of Scope
- Removing `face_index` (current prompts still rely on it)
- Arbitrary profile cutouts (v2 capability)
- New cutout types (loft, sweep, etc.)
- Component A unit tests (no Python interpreter on this machine; verify-report defers)
- README/LICENSE work (separate change)
- The Joe-Spencer clone under `Fusion360MCP_test/`

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `design-introspection`: add "Get Body Info with Face Geometry" requirement + scenario (per-face enumeration was deliberately omitted in `fusion360-extended-tools` to honor the 100-face cap vacuously)
- `cutout-modeling`: add `face_selector` to the three cutout requirements; add deprecation note for `face_index`

## Approach

**Component A** (`handlers.py` + `tools.py`): extend `handle_get_body_info` to enumerate faces up to the 100-entry cap (normal via `BRepFace.evaluator.getNormalAtPoint`, centroid from `face.boundingBox`). Add a `resolve_face(body, face_index=None, face_selector=None)` helper in `tools.py` — the selector matches the face whose normal is closest to `selector.normal` (default tolerance 5°), breaking ties by smallest centroid distance. The three cutout handlers call `resolve_face` instead of `body.faces.item(face_idx - 1)`, preserving the index path.

**Component B** (`tools.ts` + `types.ts`): add a shared `FaceSelectorSchema` (Zod) and `FaceGeometry`/`FaceSelector` types. The three cutout schemas gain an optional `face_selector`. Tests in `tools.test.ts` cover the new `get_body_info` shape and the selector path. **Runtime coverage**: a new `manual-test-checklist.md` captures A1 (copy add-in, verify in Scripts and Add-Ins), A2 (Run, confirm log "Fusion 360 MCP Server listening on port X"), and F3 (MCP Inspector call to `get_active_design_parameters`); status column goes from `[ ]` to `[x] PASS`/`[x] FAIL` with one-line evidence per row.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `Fusion360MCP/handlers.py` | Modified | Face enumeration in `get_body_info`; cutout handlers call `resolve_face` |
| `Fusion360MCP/tools.py` | Modified | New `resolve_face` helper |
| `mcp-server/src/tools.ts` | Modified | `get_body_info` shape extended; 3 cutout schemas gain `face_selector` |
| `mcp-server/src/types.ts` | Modified | `FaceGeometry`, `FaceSelector` interfaces |
| `mcp-server/src/tools.test.ts` | Modified | New test cases for shape and selector path |
| `openspec/specs/design-introspection/spec.md` | Modified | New face-geometry requirement + scenario |
| `openspec/specs/cutout-modeling/spec.md` | Modified | `face_selector` requirement + `face_index` deprecation note |
| `openspec/changes/face-index-and-runtime-coverage/manual-test-checklist.md` | New | A1, A2, F3 results |
| `openspec/changes/fusion360-mcp-server/verify-report.md` | Modified | Re-mark 3 UNTESTED scenarios |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `BRepFace.evaluator.getNormalAtPoint` may raise on faces with no analytic normal (B-spline, blended edges). | Medium | Wrap in `try/except`; on failure return `normal: null` and the selector skips that face. |
| `face_selector` with `normal` only can match multiple faces (e.g. top vs bottom of a slab). | Medium | **Nearest centroid** as tiebreaker; if `selector.centroid` is omitted, pick the face with the largest `area_mm2`. |
| Re-introducing the `faces` array is a wire-format change (additive but visible); LLM prompts hard-coded to 6 fields see an extra key. | Low | Field is additive; consumers ignore unknown keys. |
| 100-entry cap on `faces`: a body with 500 faces returns only 100; the selector only sees those 100. | Low | Spec already requires `face_count` to reflect the actual total; cap is on the enumerated array. |
| A1/A2/F3 require Fusion 360 with the add-in loaded; no GUI session on this machine. | High (process) | The checklist is a hard gate. Verify report is only updated after the user fills the rows. |
| Component A has no unit tests; a syntax error in `resolve_face` would only surface at runtime. | Medium | Visual review + A1/A2/F3 manual run; mirrors the existing `try/except FusionAPIError` + `_get_active_design()` discipline. |
| `face_index` deprecation is announced but not enforced; new clients may keep using ordinals. | Low | Selector is optional; index path unchanged. Tool descriptions nudge toward the selector. |

## Rollback Plan

1. Revert `handlers.py` + `tools.py`: drop `resolve_face` and the face enumeration block; cutout handlers fall back to `body.faces.item(face_idx - 1)`.
2. Revert `tools.ts` + `types.ts` to the pre-change Zod schemas and types.
3. Revert the spec deltas in `openspec/specs/design-introspection/spec.md` and `openspec/specs/cutout-modeling/spec.md`.
4. Revert `tools.test.ts` to drop the new cases and revert the new `manual-test-checklist.md` rows to "untested".
5. No persistent design data is touched: no cutouts are executed during testing, so the timeline stays clean.

## Dependencies

- Autodesk Fusion 360 with the Add-in loaded (for A1, A2, F3)
- No new Python or Node packages

## Success Criteria

- [ ] `get_body_info` returns `faces: [{index, normal, centroid, area_mm2}]` capped at 100; `face_count` reflects the actual total
- [ ] All 3 cutout tools accept optional `face_selector: {normal?, centroid?, tolerance_deg?}` and resolve deterministically
- [ ] `face_index` remains valid and unchanged in both components (no breaking change)
- [ ] Component B Vitest suite adds tests for the new `get_body_info` shape and the `face_selector` parameter
- [ ] A1, A2, F3 executed inside Fusion 360; results captured in `manual-test-checklist.md` with status column filled
- [ ] Verify report marks A1, A2, F3 (and 3 cutout scenarios) as PASS or FAIL with evidence

## Size Forecast

| File | Lines | Note |
|------|-------|------|
| `Fusion360MCP/handlers.py` | ~85 | Face enumeration + 3 handler call-site updates |
| `Fusion360MCP/tools.py` | ~45 | `resolve_face` helper |
| `mcp-server/src/tools.ts` | ~30 | `FaceSelectorSchema` + 3 schema extensions |
| `mcp-server/src/types.ts` | ~25 | `FaceGeometry`, `FaceSelector` |
| `mcp-server/src/tools.test.ts` | ~50 | 4 new test cases |
| `openspec/specs/design-introspection/spec.md` | ~30 | New requirement + scenario |
| `openspec/specs/cutout-modeling/spec.md` | ~40 | 3 modified requirements + deprecation note |
| `openspec/changes/face-index-and-runtime-coverage/manual-test-checklist.md` | ~25 | New file |
| `openspec/changes/fusion360-mcp-server/verify-report.md` | ~15 | Re-mark 3 scenarios |
| **Total** | **~345** | **All additive; under 400-line budget** |

**Budget check**: ~345 lines across 9 files, all additive. **Under the 400-line review budget — no chained PR needed.**
