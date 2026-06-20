# Proposal: Fusion 360 Extended Tools

## Intent

The LLM can only execute write tools blind or get unhelpful empty read results. We need **introspection tools** so it can discover bodies, parameters, features, and document metadata before mutating. Unlocks inspect → plan → mutate workflows.

## Scope

### In Scope (5 new read-only tools + 1 enhancement)
- **P0** `list_bodies` — `{name, index}` from `rootComponent.bodies`
- **P0** `get_document_info` — name, display units, design type, material library
- **P1** `get_body_info` — face count, bounding box (mm), volume (cm³), material, body type
- **P1** Enhance `get_active_design_parameters` — add `comment`, `is_favorite`
- **P2** `list_features` — timeline summary (type, name, suppressed, timestamp)
- **P2** `list_sketches` — name, profile count, referenced geometry

### Out of Scope
- Write/feature-creation tools (separate change)
- Pagination; face-by-persistent-ID; multi-design; material assignment; server caching

## Capabilities

### New Capabilities
- `design-introspection`: read-only discovery of bodies, features, sketches, and document metadata.

### Modified Capabilities
- `parameter-management`: `get_active_design_parameters` adds `comment`, `is_favorite`.

## Approach

**Component A** (Python) — 5 read-only JSON-RPC methods in `Fusion360MCP/handlers.py` via existing `CustomEvent` bridge. Cap face enumeration at 100; no `computeAll()`/rollback.

**Component B** (TypeScript) — 5 tool definitions in `mcp-server/src/tools.ts` with the existing `Record<string, ZodSchema>` shape. Reuse `FusionClient.call()` and existing error codes. Unit-test with mocked `FusionClient`; Component A stays manual-only.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `Fusion360MCP/handlers.py` | Modified | 5 handlers + router |
| `Fusion360MCP/tools.py` | Modified | Dispatcher stubs |
| `mcp-server/src/tools.ts` | Modified | 5 tool shapes + handlers |
| `mcp-server/src/types.ts` | Modified | Result types |
| `openspec/specs/design-introspection/spec.md` | New | Capability spec |
| `openspec/specs/parameter-management/spec.md` | Delta | Additive fields |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `get_body_info` slow on high-face-count bodies | Medium | Cap faces at 100; LLM pattern: list first, inspect one |
| `list_features` payload too large | Low | Cap at 200 features |
| `body.material` null for default materials | Medium | Return `null`; documented in spec |

## Rollback Plan

Revert `mcp-server/src/tools.ts` and `Fusion360MCP/handlers.py` to previous commit. New tools are additive; existing behavior unchanged. Skip the parameter delta on archive if needed. No persistent data changes.

## Dependencies

- Component A and B infrastructure (proven)
- Fusion API: `Component.bodies/features/sketches`, `Document.unitsManager`, `Body.boundingBox/volume/material`, `UserParameter.comment`

## Success Criteria

- [ ] `list_bodies` on "Escritorio" returns the sheet-of-steel body name
- [ ] `get_document_info` exposes display units (mm or cm)
- [ ] `get_body_info` returns face count, bounding box, volume, material
- [ ] `get_active_design_parameters` returns `comment`, `is_favorite` when present
- [ ] All 5 new tools return `NO_ACTIVE_DESIGN` with no document open
- [ ] Component B unit tests cover the 5 new tools with a mocked `FusionClient`
