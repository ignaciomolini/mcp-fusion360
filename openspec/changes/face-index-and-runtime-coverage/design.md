# Design: Face Index and Runtime Coverage

Component A adds a `resolve_face()` helper plus per-face enumeration to `get_body_info`. Component B adds a Zod `FaceSelectorSchema` and threads it into the three cutout tools. Manual gate: A1/A2/F3 run inside Fusion 360 by the user.

## Technical Approach

`tools.py` gains `resolve_face(body, face_index=None, face_selector=None)`. The three cutout handlers swap `body.faces.item(face_idx - 1)` for `resolve_face(body, face_idx, params.get("face_selector"))`. `handle_get_body_info` enumerates `body.faces` up to 100 entries, computing centroid (existing `_get_face_centroid`), area (`face.area`, cm²→mm²), and normal (`face.evaluator.getNormalAtPoint(centroid)` in `try/except`).

In Component B, a shared `FaceSelectorSchema` extends the three cutout shapes; `get_body_info` shape is unchanged (face payload is documentation-only in `types.ts`).

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `resolve_face` location | New function in `Fusion360MCP/tools.py` | Mirrors `validate_face_index` + `resolve_body` style. |
| Normal source | `face.evaluator.getNormalAtPoint(centroid)` in `try/except` | Centroid is the only point already computed. |
| `face.area` source | `BRepFace.area` direct property | No exception path; convert cm²→mm² at the boundary. |
| Cap constant | `MAX_FACES_ENUMERATED = 100` in `tools.py` | Single source of truth. |
| Selector precedence | `face_index` wins when both present | Matches deprecation-period contract (spec delta line 82). |
| Zod validation gate | `.refine(v => v.normal \|\| v.centroid)` | One shape; refine message names the error code. |
| `mcp_comm/` log dir | **NOT introduced** (proposal was aspirational) | No such pattern exists; `app.log()` (Fusion360MCP.py:58) is the established path. |
| Tool description nudge | Append "Use `face_selector` instead" to cutout descriptions | MCP SDK v1.12 has no deprecation flag. |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `Fusion360MCP/tools.py` | Modify | Add `resolve_face`, `MAX_FACES_ENUMERATED = 100`, `_face_normal_at`. |
| `Fusion360MCP/handlers.py` | Modify | `handle_get_body_info` enumerates faces; 3 cutout handlers call `resolve_face`. |
| `mcp-server/src/tools.ts` | Modify | New `FaceSelectorSchema`; add `face_selector?` to 3 cutout shapes. |
| `mcp-server/src/types.ts` | Modify | `FaceGeometry`, `FaceSelector`; extend `BodyInfo` with `faces?`, `faces_truncated?`. |
| `mcp-server/src/tools.test.ts` | Modify | 4 new cases; existing cutout cases still pass without `face_selector`. |
| `mcp-server/src/index.ts` | Modify | Append deprecation hint to 3 cutout tool descriptions. |
| `openspec/changes/face-index-and-runtime-coverage/manual-test-checklist.md` | Create | A1/A2/F3 rows. |
| `openspec/changes/fusion360-mcp-server/verify-report.md` | Modify | Re-mark A1, A2, F3 + 3 cutout scenarios. |

## Interfaces / Contracts

### `resolve_face(body, face_index, face_selector)` (Component A)

```python
def resolve_face(body, face_index=None, face_selector=None):
    if face_index is not None:
        validate_face_index(body, face_index)
        return body.faces.item(face_index - 1)
    if not face_selector:
        raise FusionAPIError(INVALID_PARAMETER,
            "face_index or face_selector is required")
    if not (face_selector.get("normal") or face_selector.get("centroid")):
        raise FusionAPIError(INVALID_PARAMETER, "face_selector is empty")
    return _match_selector(body, face_selector)
```

`_match_selector` enumerates `body.faces`, computes angular distance from each face's normal to `selector.normal` (skips faces where `_face_normal_at` returns `None`), filters by `tolerance_degrees` (default 5°), picks the face whose centroid is closest to `selector.centroid`. If no centroid, picks the largest-area match. No match → `FusionAPIError(INVALID_PARAMETER, "no face matched selector")`.

### `FaceSelectorSchema` (Component B)

```ts
const FaceSelectorSchema = z.object({
  normal: z.object({x:z.number(),y:z.number(),z:z.number()}).optional(),
  tolerance_degrees: z.number().default(5).optional(),
  centroid: z.object({x:z.number(),y:z.number(),z:z.number()}).optional(),
  tolerance_mm: z.number().default(0.5).optional(),
}).refine(v => v.normal || v.centroid, {
  message: "face_selector must include normal or centroid (-32001)"
});
```

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| R1 evaluator raises | `_face_normal_at` returns `None`; selector skips that face; one `app.log` line. |
| R2 selector normal-only ambiguity | Centroid tiebreaker; if no centroid, largest `area_mm2`. |
| R3 wire-format change | Additive; existing consumers ignore unknown keys. |
| R4 100-face cap | `faces_truncated: true`; `face_count` stays at actual total. |
| R5 no GUI session | Manual gate; verify non-passing until rows filled. |
| R6 no Python unit tests | Static review against the 4 selector scenarios in spec delta. |
| R7 `face_index` deprecation | Description nudge only; index path remains valid. |

## Testing Strategy

| Layer | Component A | Component B |
|-------|-------------|-------------|
| Unit | None (`adsk` unavailable); static review | Vitest: cutout forwards `face_selector`; existing tests pass without it. |
| Manual | A1, A2, F3 | — |
| E2E | F3 closes the add-in→HTTP→MCP round-trip | — |

## Manual Test Plan (verify gate)

`manual-test-checklist.md` gets three new rows. Evidence column requires a one-liner (e.g. `"Text Commands: Fusion 360 MCP Server listening on port 9876"` for A2). Verify is non-passing until the user fills the status column.

## Migration / Rollout

No migration. `face_index` preserved; the only deprecation is the tool-description nudge. Rollback: drop `resolve_face`, revert cutout handlers to `body.faces.item(face_idx - 1)`, drop `face_selector` from Component B schemas/types.

## Open Questions

- `mcp_comm/` is referenced in the proposal's risk table but does not exist in this repo. Recommend using the existing `app.log()` path. **Confirm.**
- Slot cutout still uses `length_mm <= width_mm` (handlers.py:502); previous verify report flagged this. Out of scope here.

## Size Forecast

~280 lines across 8 files, all additive. Under the 400-line review budget — no chained PR needed.
