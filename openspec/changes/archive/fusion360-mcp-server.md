# Archive: Fusion 360 MCP Server

## Change Summary

Implemented a two-component Model Context Protocol (MCP) server for Autodesk Fusion 360. The system enables an AI agent (via CLI or Claude Desktop) to interact with Fusion 360 using natural language: reading design parameters, measuring clearances, updating parameters, and creating circular/rectangular/slot cutouts.

- **Component A**: Fusion 360 Add-in in Python. Runs inside Fusion 360's embedded Python interpreter. Exposes an HTTP JSON-RPC 2.0 server on localhost (port 9876, auto-increment on collision). Delegates API calls to Fusion's main thread via `adsk.core.CustomEvent`.
- **Component B**: MCP Wrapper in Node.js/TypeScript. Stdio-based MCP server using `@modelcontextprotocol/sdk`. Translates MCP tool calls into HTTP JSON-RPC requests to Component A.

## Verification Status

**PASS WITH WARNINGS**

- TypeScript compilation: clean (`npx tsc --noEmit`)
- Forbidden `adsk` imports in Component B: confirmed absent
- All 6 tools registered in MCP server
- JSON-RPC wire format, error codes, unit conversion, and rollback logic verified
- Component A requires manual runtime testing inside Fusion 360 GUI (platform limitation)

## Artifacts Produced

| Phase | File System | Engram Topic Key |
|---|---|---|
| Exploration | `openspec/changes/fusion360-mcp-server/explore.md` | `sdd/fusion360-mcp-server/explore` |
| Proposal | `openspec/changes/fusion360-mcp-server/proposal.md` | `sdd/fusion360-mcp-server/proposal` |
| Specs | `openspec/changes/fusion360-mcp-server/specs/*` | `sdd/fusion360-mcp-server/spec` |
| Design | `openspec/changes/fusion360-mcp-server/design.md` | `sdd/fusion360-mcp-server/design` |
| Tasks | `openspec/changes/fusion360-mcp-server/tasks.md` | `sdd/fusion360-mcp-server/tasks` |
| Verify Report | `openspec/changes/fusion360-mcp-server/verify-report.md` | `sdd/fusion360-mcp-server/verify-report` |
| Archive Report | `openspec/changes/archive/fusion360-mcp-server.md` | `sdd/fusion360-mcp-server/archive-report` |

## Files Delivered

### Component A — Fusion 360 Add-in (`add-in/`)

| File | Purpose |
|---|---|
| `Fusion360MCP.manifest` | Fusion 360 add-in manifest with GUID and script entry |
| `Fusion360MCP.py` | Add-in entry point: `run()` and `stop()` lifecycle |
| `jsonrpc.py` | JSON-RPC 2.0 request/response utilities |
| `errors.py` | Error codes and `FusionAPIError` exception class |
| `server.py` | HTTP server with POST-only routing, port auto-increment, 30s timeout |
| `fusion_bridge.py` | `RequestBridge` using `adsk.core.CustomEvent` and `threading.Event` |
| `tools.py` | mm↔cm conversion and validation helpers |
| `handlers.py` | All 6 JSON-RPC handlers with parameter snapshot/rollback |

### Component B — MCP Wrapper (`mcp-server/`)

| File | Purpose |
|---|---|
| `package.json` | Node.js dependencies (`@modelcontextprotocol/sdk`, `zod`) |
| `tsconfig.json` | Strict TypeScript configuration |
| `src/types.ts` | JSON-RPC and MCP result types |
| `src/errors.ts` | JSON-RPC to MCP error/result translation |
| `src/jsonrpc-client.ts` | `FusionClient` HTTP client to Component A |
| `src/tools.ts` | Zod schemas and handlers for 6 MCP tools |
| `src/index.ts` | MCP server bootstrap and stdio transport |

## Tools Exposed to the LLM

1. `get_active_design_parameters` — returns all User Parameters of the active design
2. `measure_clearance` — minimum distance between two bodies (same-body guard enforced)
3. `update_user_parameter` — updates a parameter, recomputes, and auto-rolls back on failure
4. `create_circular_cutout` — circular hole via sketch + extrude cut
5. `create_rectangular_cutout` — rectangular cutout with optional rotation
6. `create_slot_cutout` — slot/obround cutout with optional rotation

## Key Design Decisions

- HTTP + JSON-RPC 2.0 over localhost (WebSocket rejected as overkill for request-response MCP)
- Component B NEVER imports `adsk`; all Fusion API code lives in Component A
- Unit conversion at Component A boundary (mm in tool interface, cm in Fusion API)
- Parameter snapshot + rollback for `update_user_parameter`
- Separate MCP tools per cutout type (cleaner schemas, simpler implementation)
- 1-based `face_index` validated on Component A
- Port auto-increment on collision

## Chained PR Strategy

4 stacked-to-main PRs:

1. Component A infrastructure
2. Component A handlers + tools
3. Component B infrastructure
4. Component B tools + integration

## Known Limitations

- `face_index` selection is fragile; face order in Fusion 360 is arbitrary and may change with design edits
- Component A cannot be unit-tested outside Fusion 360; all Add-in logic requires manual GUI testing
- `computeAll()` timeout is fixed at 30s and may be insufficient for very complex assemblies
- No shared type contract between Python Component A and TypeScript Component B; wire format is documented in specs

## Follow-up Work

- Manual end-to-end test inside Fusion 360: load Add-in, run MCP server, exercise all 6 tools
- Consider v2 enhancements:
  - Face selection by normal vector or named entity instead of index
  - Multi-design support
  - Arbitrary profile cutouts
  - Component A unit tests if Fusion provides a headless runtime

## Rollback Notes

This archive marks the change as complete. Future modifications should start a new SDD change referencing this archive.
