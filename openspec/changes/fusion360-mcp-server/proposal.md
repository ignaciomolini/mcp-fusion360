# Proposal: Fusion 360 MCP Server

## Intent
Enable AI agents (via Claude Desktop or CLI) to interact with Autodesk Fusion 360 using natural language. The agent reads parametric design data, analyzes geometric clearances, and creates cutouts — all without manual GUI interaction.

## Scope

### In Scope
- Component A (Python): Fusion 360 Add-in with HTTP server (localhost:9876), JSON-RPC 2.0, CustomEvent bridge
- Component B (Node.js/TypeScript): stdio MCP server with 6 tool definitions
- Tool: `get_active_design_parameters` — read all user parameters
- Tool: `measure_clearance` — minimum distance between two bodies
- Tool: `update_user_parameter` — modify parameter with automatic rollback on timeline failure
- Tools: `create_circular_cutout`, `create_rectangular_cutout`, `create_slot_cutout` — sketch + extrude cut on face
- Unit conversion: mm↔cm between agent and Fusion API

### Out of Scope
- Multi-design support (only active design)
- Face selection by persistent ID or normal vector (face_index only)
- Arbitrary profile cutouts (v2)
- Auth/encryption beyond localhost binding

## Capabilities

### New Capabilities
- `fusion360-add-in`: HTTP server, JSON-RPC handler, CustomEvent bridge, Fusion API error wrapping
- `mcp-wrapper`: Stdio MCP server, tool schema definitions, HTTP client to Component A
- `parameter-management`: Read/write user parameters, automatic rollback on computeAll failure
- `geometry-analysis`: Measure minimum distance between named bodies
- `cutout-modeling`: Circular, rectangular, and slot cutouts via sketch + extrude cut

### Modified Capabilities
None

## Approach
Component A (Python) runs inside Fusion 360's embedded interpreter. It binds an HTTP server to `127.0.0.1:9876` (configurable via env). Requests are queued and dispatched to the main thread via `adsk.core.CustomEvent`. Each handler wraps `adsk` exceptions into JSON-RPC errors.

Component B (Node.js/TypeScript) uses `@modelcontextprotocol/sdk`. It registers 6 tools with Zod schemas. Each tool call maps to a JSON-RPC POST to Component A. JSON-RPC errors are translated into MCP `CallToolResult` with `isError: true`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `add-in/` | New | Component A — Python add-in with server, handlers, manifest |
| `mcp-server/` | New | Component B — Node.js/TypeScript MCP wrapper |
| `openspec/specs/` | New | 5 capability specs |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Fusion API changes between versions | Medium | Use stable APIs; document tested version |
| `computeAll()` slow on complex designs | Medium | 30s timeout; inform LLM on timeout |
| `face_index` fragility | Medium | Document as MVP limitation |
| No automated testing for Component A | High | Manual testing in Fusion 360 GUI |

## Rollback Plan
Delete `add-in/` and `mcp-server/` directories. Remove MCP server configuration from client. No persistent data changes.

## Dependencies
- Autodesk Fusion 360 installed
- Node.js 18+ for Component B

## Success Criteria
- [ ] Component A starts inside Fusion 360 and responds to HTTP JSON-RPC
- [ ] Component B registers all 6 tools with an MCP client
- [ ] `get_active_design_parameters` returns correct parameter values
- [ ] `update_user_parameter` modifies a parameter and triggers recompute
- [ ] `create_circular_cutout` creates a visible hole in the active design
- [ ] All Fusion API errors return structured JSON-RPC errors to the LLM
