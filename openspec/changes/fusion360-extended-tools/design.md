# Design: Fusion 360 Extended Tools

Component A (Python) gains 5 read-only JSON-RPC methods and an additive change to `get_active_design_parameters`. Component B (TypeScript) gains 5 Zod-typed MCP tools and a small extension to the existing parameter shape. All traffic flows through the proven `FusionClient` over the existing localhost JSON-RPC channel.

## Technical Approach

Five new handlers in `Fusion360MCP/handlers.py` reuse the existing `_get_active_design()` helper and `resolve_body()`. They iterate `Component.bRepBodies` / `Component.features` / `Component.sketches`, read metadata, and return JSON. No `computeAll()`, no rollback, no document mutation. Component B wires each handler to an `McpServer.tool(...)` registration with a Zod raw shape. The modified parameter handler extends each returned object with `comment` and `is_favorite` only; no field is removed or renamed.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| `body_type` source | `BRepBody.isSolid` → `"SolidBody"` / `"SurfaceBody"` | Walk the type hierarchy | `BRepBody` exposes only `isSolid` for "is this a solid" semantics; string mapping is stable and matches spec. |
| Feature `type` field | `feature.objectType.split(".")[-1]` | Hard-coded class names list | `objectType` is the canonical Fusion 360 way; survives new feature types without code change. |
| Feature `timestamp` | `datetime.utcnow().isoformat() + "Z"` at handler time | `timelineObject.index` | Spec asks for ISO 8601; `index` is ordinal, not a date. Capture-when-read is the only honest ISO timestamp available. |
| Sketch `referenced_geometry` | Array of `entityToken` strings | Resolve to plane/face names | `Sketch.referencePlane` returns a `Base` with no stable string name; `entityToken` is the documented stable identifier that survives saves. |
| Parameter `role` field | **REMOVED** from response | Pass-through from spec; set to `null` | The Fusion 360 Python API exposes `role` ONLY on `ModelParameter` (free-form string like "Depth", "Offset"). `UserParameter` inherits from `Parameter` which has no `role`. The spec assumption is wrong; reporting `null` would be a lie. Spec must be revised. |
| Face enumeration in `get_body_info` | OMIT `faces` array; return only `face_count` | Include capped `faces` array | Spec requires `face_count` to be the actual total; the 100-face cap is forward-looking. Keeping the response lean honors both the scenarios and the cap. |
| `material_library` source | `app.materialLibraries.item(0).name` | Empty string fallback | First library is the default Fusion 360 library; spec only requires a non-empty string. |
| Unit conversion for bounding box | Convert cm→mm at handler boundary | Return cm | Matches the rest of the project (mm at the API surface, cm at Fusion). |

## Data Flow

```
LLM ──stdio──► Component B (fetch) ──HTTP POST──► Component A (http.server)
                                                          │
                                                          │ queue → CustomEvent
                                                          ▼
                                                  main thread → adsk API
                                                  (read-only: no computeAll)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `Fusion360MCP/handlers.py` | Modify | Add 5 handler functions; extend `handle_get_active_design_parameters`; register in `HANDLERS` dict |
| `mcp-server/src/tools.ts` | Modify | Add 5 Zod raw shapes + handler functions; no change to `getActiveDesignParametersShape` |
| `mcp-server/src/index.ts` | Modify | Import + register 5 new tools with `server.tool(...)` |
| `mcp-server/src/types.ts` | Modify | Optional: add `ListBodiesResult`, `BodyInfoResult`, etc. (or rely on `unknown` cast) |
| `mcp-server/src/tools.test.ts` | Create | Vitest unit tests with mocked `FusionClient` covering 5 new tools + the parameter delta |
| `openspec/changes/fusion360-extended-tools/specs/parameter-management/spec.md` | Modify (spec delta) | Remove `role` field from the modified `Requirement: Get Active Design Parameters` |
| `openspec/changes/fusion360-extended-tools/manual-test-checklist.md` | Create | Manual verification cases for the 5 new tools |

## Interfaces / Contracts

### 1. `list_bodies` — implements Requirement "List Bodies" of design-introspection

| Aspect | Value |
|---|---|
| Method | `list_bodies` |
| Request params | `{}` (none) |
| Success response | `{"bodies": [{"name": "Plate", "index": 1}, ...]}` |
| Fusion 360 API | `design.rootComponent.bRepBodies` (BRepBodies collection, iterated by `item(i)`) |
| Errors | `-32002` if no active design |

**Errors**:
- `-32002 NO_ACTIVE_DESIGN` — no document open
- `-32000 FUSION_API_ERROR` — unhandled `adsk` exception

**Notes**:
- `index` is 1-based to match the existing `face_index` convention in `cutout-modeling`.
- Iteration uses `BRepBodies.count` and `BRepBodies.item(i)`; Python `for body in bRepBodies:` works but does not guarantee a consistent order — index is a positional label, not a stable ID.

### 2. `get_document_info` — implements Requirement "Get Document Info"

| Aspect | Value |
|---|---|
| Method | `get_document_info` |
| Request params | `{}` (none) |
| Success response | `{"name": "Escritorio", "units": "mm", "design_type": "ParametricDesign", "material_library": "Fusion 360 Material Library"}` |
| Fusion 360 API | `app.activeDocument.name`, `app.activeDocument.unitsManager.defaultLengthUnits`, `design.designType`, `app.materialLibraries.item(0).name` |
| Errors | `-32002` if no active design |

**Errors**:
- `-32002 NO_ACTIVE_DESIGN`
- `-32000 FUSION_API_ERROR`

**Notes**:
- `units` is normalized to `"mm"` or `"cm"`. Other length units (e.g., `"in"`, `"ft"`) are passed through as-is — the spec only enumerates mm and cm as the expected values. Document this in error messages if a non-metric user runs the tool.
- `design_type` mapping: `DesignTypes.ParametricDesignType` → `"ParametricDesign"`, `DesignTypes.DirectDesignType` → `"DirectDesign"`. The spec lists `"PlasticDesign"` but the API enum has only two values; remove `"PlasticDesign"` from the spec (or document it as a future-only value).
- `material_library` falls back to `""` when no libraries are loaded (defensive — rare in real Fusion sessions).

### 3. `get_body_info` — implements Requirement "Get Body Info"

| Aspect | Value |
|---|---|
| Method | `get_body_info` |
| Request params | `{"body_name": "Plate"}` (string, required, non-empty) |
| Success response | `{"face_count": 6, "bounding_box": {"min": {"x": 0, "y": 0, "z": 0}, "max": {"x": 100, "y": 50, "z": 5}}, "volume_cm3": 250.0, "material": "Steel", "body_type": "SolidBody"}` |
| Fusion 360 API | `body.faces.count`, `body.boundingBox.minPoint/maxPoint`, `body.volume`, `body.material` (object or null), `body.isSolid` |
| Errors | `-32001` invalid name / not found, `-32002` no design |

**Errors**:
- `-32001 INVALID_PARAMETER` — empty `body_name`, missing `body_name`, or body not found (message: `"Body 'X' not found"`)
- `-32002 NO_ACTIVE_DESIGN`
- `-32000 FUSION_API_ERROR`

**Notes**:
- Per-face enumeration is **omitted** from the response; the 100-face cap is honored vacuously. If a future requirement adds per-face details, the cap kicks in at the response builder.
- `bounding_box` is converted from cm to mm to match the rest of the API surface (`bbox.minPoint.x * 10`, etc.).
- `volume_cm3` is the raw value from `body.volume` (already in cm³ per the API doc).
- `material` is `material.name` when `body.material` is not null, else `null`.
- `body_type`: `True` → `"SolidBody"`, `False` → `"SurfaceBody"`.

### 4. `list_features` — implements Requirement "List Features"

| Aspect | Value |
|---|---|
| Method | `list_features` |
| Request params | `{}` (none) |
| Success response | `{"features": [{"name": "Extrude1", "type": "ExtrudeFeature", "is_suppressed": false, "timestamp": "2026-06-19T12:34:56Z"}, ...], "truncated": false}` |
| Fusion 360 API | `design.rootComponent.features` (Features collection); `feature.objectType`, `feature.name`, `feature.isSuppressed` |
| Errors | `-32002` no design |

**Errors**:
- `-32002 NO_ACTIVE_DESIGN`
- `-32000 FUSION_API_ERROR`

**Notes**:
- `type` is derived from `feature.objectType` (e.g., `"adsk.fusion.ExtrudeFeature"` → `"ExtrudeFeature"`).
- `truncated: true` is set when `features.count > 200`; the array is sliced to the first 200.
- `timestamp` is `datetime.utcnow().isoformat() + "Z"` per handler call (the Fusion API does not expose creation timestamps on `Feature` or `TimelineObject`).

### 5. `list_sketches` — implements Requirement "List Sketches"

| Aspect | Value |
|---|---|
| Method | `list_sketches` |
| Request params | `{}` (none) |
| Success response | `{"sketches": [{"name": "Sketch1", "profile_count": 1, "referenced_geometry": ["plane-token-abc123"]}, ...]}` |
| Fusion 360 API | `design.rootComponent.sketches`; `sketch.profiles.count`, `sketch.referencePlane.entityToken` (when not null) |
| Errors | `-32002` no design |

**Errors**:
- `-32002 NO_ACTIVE_DESIGN`
- `-32000 FUSION_API_ERROR`

**Notes**:
- `referenced_geometry` is `[]` when `sketch.referencePlane` is null (e.g., direct-modeling or surface-based sketches).
- The `entityToken` is the documented stable identifier for a Fusion entity; it can be passed to `Design.findEntityByToken` later.

### 6. `get_active_design_parameters` (MODIFIED) — implements delta Requirement

**Old response shape (unchanged contract)**:
```json
{
  "parameters": [
    {"name": "Width", "expression": "40 mm", "value": 40.0, "unit": "mm"}
  ]
}
```

**New response shape (additive)**:
```json
{
  "parameters": [
    {
      "name": "Width",
      "expression": "40 mm",
      "value": 40.0,
      "unit": "mm",
      "comment": "outer width in mm",
      "is_favorite": true
    }
  ]
}
```

| Aspect | Value |
|---|---|
| Method | `get_active_design_parameters` (unchanged) |
| Request params | `{}` (unchanged) |
| New fields | `comment` (string or `null`), `is_favorite` (boolean) |
| Removed fields | `role` — see Risks; the spec must be revised to drop it |
| Fusion 360 API | `param.comment` and `param.isFavorite` (both inherited from base `Parameter` class) |

**Backward compatibility**: existing consumers ignore the new fields. The change is purely additive. No new error codes.

## Zod Schemas (TypeScript)

```typescript
// list_bodies — no input params
export const listBodiesShape = {};

// get_document_info — no input params
export const getDocumentInfoShape = {};

// get_body_info — one required string
export const getBodyInfoShape = {
  body_name: z.string().min(1).describe("Name of the body to inspect (exact match)"),
};

// list_features — no input params
export const listFeaturesShape = {};

// list_sketches — no input params
export const listSketchesShape = {};
```

Handler functions follow the existing `tools.ts` pattern — each one calls `client.call("method_name", args)` and returns the result. The `get_active_design_parameters` shape is unchanged; only the Python handler adds fields to each returned object.

## Add-in Handler Signatures (Python)

```python
def handle_list_bodies(params):
    """Return [{name, index}] for every body in the root component.

    Returns:
        dict with 'bodies' key.
    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN)
    """

def handle_get_document_info(params):
    """Return document metadata: name, units, design_type, material_library.

    Returns:
        dict with name, units, design_type, material_library.
    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN)
    """

def handle_get_body_info(params):
    """Return physical properties of a body: face_count, bounding_box, volume_cm3,
    material, body_type.

    Args:
        body_name (str): exact body name.

    Returns:
        dict with face_count, bounding_box, volume_cm3, material, body_type.
    Raises:
        FusionAPIError(INVALID_PARAMETER) on empty or missing name / not found.
        FusionAPIError(NO_ACTIVE_DESIGN).
    """

def handle_list_features(params):
    """Return up to 200 features from the root component timeline.

    Returns:
        dict with 'features' (capped list) and 'truncated' (bool).
    """

def handle_list_sketches(params):
    """Return [{name, profile_count, referenced_geometry}] for each sketch.

    Returns:
        dict with 'sketches' key.
    """

def handle_get_active_design_parameters(params):  # MODIFIED
    """Return all User Parameters. Each entry adds 'comment' and 'is_favorite'.

    Existing fields (name, expression, value, unit) are preserved verbatim.
    """
```

All five new handlers use `_get_active_design()` and follow the existing `try/except FusionAPIError` pattern. `handle_get_body_info` adds `params.get("body_name")` validation and reuses `resolve_body()` from `tools.py`.

## Component A (Add-in) Changes

**Imports** — no new imports required. The handlers use only `adsk.core.Application.get()` and the `Design` instance already accessed in existing code. The Python `datetime` module (stdlib) is used for the feature timestamp.

**`HANDLERS` dict update** (in `Fusion360MCP/handlers.py`):
```python
HANDLERS = {
    "get_active_design_parameters": handle_get_active_design_parameters,
    "measure_clearance": handle_measure_clearance,
    "update_user_parameter": handle_update_user_parameter,
    "create_circular_cutout": handle_create_circular_cutout,
    "create_rectangular_cutout": handle_create_rectangular_cutout,
    "create_slot_cutout": handle_create_slot_cutout,
    "list_bodies": handle_list_bodies,
    "get_document_info": handle_get_document_info,
    "get_body_info": handle_get_body_info,
    "list_features": handle_list_features,
    "list_sketches": handle_list_sketches,
}
```

**`METHODS` set update** (in `Fusion360MCP/server.py`): add the same 5 method names so the dispatcher accepts them.

## Component B (mcp-server) Changes

**`mcp-server/src/tools.ts`** — add 5 raw shapes + handler functions following the existing `getActiveDesignParametersShape` pattern (no input params, just `client.call("method_name")`).

**`mcp-server/src/index.ts`** — add 5 `server.tool(...)` registrations:
```typescript
server.tool("list_bodies", "List all solid bodies in the root component.",
  async () => handleListBodies(client));
server.tool("get_document_info", "Get active document metadata.",
  async () => handleGetDocumentInfo(client));
server.tool("get_body_info", "Get physical properties of a named body.",
  getBodyInfoShape,
  async (args) => handleGetBodyInfo(client, args));
server.tool("list_features", "List features in the root component timeline (capped at 200).",
  async () => handleListFeatures(client));
server.tool("list_sketches", "List sketches in the root component.",
  async () => handleListSketches(client));
```

**`mcp-server/src/jsonrpc-client.ts`** — no changes. The client is method-agnostic.

**`mcp-server/src/types.ts`** — optional. Add named result types for stronger typing:
```typescript
export interface BodyInfo {
  face_count: number;
  bounding_box: { min: Point3D; max: Point3D };
  volume_cm3: number;
  material: string | null;
  body_type: "SolidBody" | "SurfaceBody";
}
```
The MCP `registerTool` API does not require typed results, so this is documentation-only.

## Testing Strategy

| Layer | Component A | Component B |
|-------|-------------|-------------|
| Unit | Not possible (requires `adsk`) | Mock `FusionClient` (stub `.call()`); assert method name + args; assert response wrapping |
| Integration | Manual in Fusion GUI | Mock HTTP endpoint with JSON-RPC fixtures (optional) |
| E2E | Requires Fusion 360 | Full pipeline via MCP Inspector or any stdio MCP client |

**Test setup**: add `vitest` as a devDependency in `mcp-server/package.json`; create `mcp-server/src/tools.test.ts` with one test per new tool:

```typescript
// Pattern for each new tool
test("list_bodies calls the right JSON-RPC method", async () => {
  const mockClient = { call: vi.fn().mockResolvedValue({ content: [], isError: false }) } as unknown as FusionClient;
  await handleListBodies(mockClient);
  expect(mockClient.call).toHaveBeenCalledWith("list_bodies");
});
```

**Manual test cases** (to add to `manual-test-checklist.md`):

| # | Tool | Expected |
|---|------|----------|
| G1 | `list_bodies` on "Escritorio" | Returns the sheet-of-steel body with correct `name` and `index` |
| G2 | `list_bodies` on empty design | `{"bodies": []}` |
| G3 | `get_document_info` on "Escritorio" | `units: "mm"`, `design_type: "ParametricDesign"`, non-empty `material_library` |
| G4 | `get_body_info` with valid body | `face_count`, `bounding_box` in mm, `volume_cm3`, `material` (string or null) |
| G5 | `get_body_info` with missing body | `-32001` with "Body 'X' not found" |
| G6 | `get_body_info` with empty `body_name` | `-32001` |
| G7 | `list_features` on design with mixed features | Each entry has `name`, `type`, `is_suppressed`, `timestamp` |
| G8 | `list_features` with > 200 features | `truncated: true`, array length 200 |
| G9 | `list_sketches` on design with sketches | Each entry has `name`, `profile_count`, `referenced_geometry` |
| G10 | All new tools (no design open) | `-32002` |
| G11 | `get_active_design_parameters` (delta) | Each entry has `comment` and `is_favorite` populated (or `null` / `false`) |

## Risks and Open Questions

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Spec assumption: `UserParameterRole` enum does not exist** | Confirmed | Drop `role` from the spec delta. The Fusion 360 API exposes `role` ONLY on `ModelParameter` (free-form string like "Depth"); `UserParameter` inherits from `Parameter` which has no `role` property. Reporting `null` would be dishonest. |
| **Spec assumption: `design_type: "PlasticDesign"`** | Confirmed | The `DesignTypes` enum has only `ParametricDesignType` and `DirectDesignType`. Remove `"PlasticDesign"` from the spec; treat as a future-only value. |
| `get_body_info` slow on high-face-count bodies | Medium | Cap face enumeration (currently omitted). `face_count` is O(1); the rest of the computation is also cheap. |
| `list_features` timestamp semantics | Low | The Fusion API has no per-feature creation date. We capture `utcnow()` at handler call time. Document this explicitly so LLM users do not confuse "when read" with "when created". |
| Sketch `referenced_geometry` resolution | Low | `entityToken` is stable but not human-readable. If users need names, future change can resolve via `Design.findEntityByToken` and inspect the result. |
| Backward compatibility of the modified parameter handler | Low | Change is purely additive (new fields). Existing consumers ignore unknown fields. No version bump needed. |
| 800-face body | Low | Tested: `BRepBody.faces.count` is O(1) on the API side; we do not iterate faces. |

## Migration / Rollout

No data migration. No feature flags. The change is additive on both sides:
- Component A: new handlers + a wider response for one existing method
- Component B: new tool registrations + a wider response (transparent to LLM)

Rollback: revert the two files (`Fusion360MCP/handlers.py`, `mcp-server/src/tools.ts`, `mcp-server/src/index.ts`) and the spec revision. The existing handlers stay untouched.

## Open Questions

- [ ] Should `get_document_info` normalize non-metric units (e.g., return `"in"` as-is, or convert to mm/cm at the response boundary)? Current design: pass-through. Spec only enumerates mm and cm; behavior outside that is undocumented.
- [ ] Should `list_features` sort by timeline position or by `name`? Current design: insertion order from `Features` collection (timeline order). `TimelineObject.index` is the documented position.
- [ ] Should `get_body_info` include a `faces` array capped at 100 with index + area? Current design: omitted. Reopen if LLM consumption patterns show a need.

## Spec Revision Required (BLOCKING before archive)

The `parameter-management` spec delta in `openspec/changes/fusion360-extended-tools/specs/parameter-management/spec.md` currently lists `role` as a field of the modified response. This MUST be removed before archive. Replace:

```diff
- `role` (string: "User", "Favorite", or another valid Fusion `UserParameterRole` value)
```

with nothing (drop the field entirely). All test scenarios that reference `role` must be rewritten to drop the assertion.

The `design-introspection` spec should also drop `"PlasticDesign"` from the `design_type` enumeration in the `Get Document Info` requirement.
