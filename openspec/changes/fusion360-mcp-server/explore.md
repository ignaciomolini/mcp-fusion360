# Exploration: Fusion 360 MCP Server — Communication Protocol & API Contract

## Current State

The project is GREENFIELD. Only the PRD (`prd.md`) and OpenSpec configuration (`openspec/config.yaml`) exist. No code, no tests, no existing artifacts. The architecture is defined as a two-component system:

- **Component A**: Fusion 360 Add-in (Python) — runs inside Fusion 360's embedded Python interpreter, uses `adsk` API, must execute API calls on the main thread via `adsk.core.CustomEvent`.
- **Component B**: MCP Wrapper (Node.js/TypeScript) — stdio-based MCP server using `@modelcontextprotocol/sdk`, translates LLM tool calls into network requests to Component A.

The critical open decision before spec/design is the **communication protocol** between A and B, and the **API contract** that governs it.

---

## Affected Areas

- `add-in/` (new) — Component A (Python) will live here. Needs threading, HTTP/WS server, CustomEvent bridge, and Fusion API handlers.
- `mcp-server/` (new) — Component B (Node.js/TypeScript) will live here. Needs MCP SDK integration, network client to A, and tool definitions.
- `shared/` (new, optional) — Shared TypeScript types for the wire format if using strict typing.

---

## Approaches

### 1. Communication Protocol: HTTP vs WebSocket

| Approach | Pros | Cons | Complexity |
|----------|------|------|------------|
| **HTTP (Recommended)** | Simpler, stateless, easier to debug (curl), natural request-response mapping to MCP's stdio model. Python's `http.server` or `flask` can run in a secondary thread. Long operations can use polling or async response with a request ID. | No native server-push. For long operations, needs either (a) blocking with timeout, or (b) polling endpoint. | Low |
| **WebSocket** | Persistent connection, bidirectional, can push async progress or results. Slightly lower latency per message. | Adds complexity (reconnection logic, heartbeat, connection state management). Overkill since MCP itself is request-response over stdio — Component B has no use for server-push. | Medium |

**Analysis**: The MCP protocol is fundamentally **request-response** via stdio. Component B receives a `tools/call` request, must return a result. There is no streaming or long-lived session concept in the MCP stdio transport. Therefore, WebSocket's bidirectionality and persistent connection add **no functional value** for this use case. HTTP's simplicity and debuggability outweigh any theoretical latency benefits.

**Decision**: Use **HTTP** with a simple JSON-RPC-like REST format. For operations that take seconds (e.g., `computeAll`), Component B will make a synchronous HTTP request with a generous timeout (e.g., 30s). If operations need to be longer, add a polling pattern later.

---

### 2. API Contract (Wire Format)

**Decision**: Use **JSON-RPC 2.0** over HTTP POST.

Why JSON-RPC over REST?
- Each tool maps naturally to a JSON-RPC `method` (e.g., `get_active_design_parameters`).
- Unified error handling via `error` object with `code`, `message`, `data`.
- Batching is possible if needed later.
- Simpler than designing RESTful nouns/verbs for actions like `update_user_parameter`.

**Request format**:
```json
{
  "jsonrpc": "2.0",
  "method": "get_active_design_parameters",
  "params": {},
  "id": 1
}
```

**Response format**:
```json
{
  "jsonrpc": "2.0",
  "result": { "parameters": [...] },
  "id": 1
}
```

**Error format**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "Fusion API error: Body 'Foo' not found",
    "data": { "fusion_trace": "..." }
  },
  "id": 1
}
```

**Error handling contract**:
- Component A catches all `adsk` exceptions and wraps them in JSON-RPC errors.
- Error codes:
  - `-32000`: Fusion API error (runtime)
  - `-32001`: Invalid parameter (client error)
  - `-32002`: Design not active / no document open
  - `-32601`: Method not found (tool not implemented)
- Component B translates JSON-RPC errors into MCP `CallToolResult` with `isError: true` and the error message in `content[].text`.

**Timeout handling**:
- Component A: set a per-request timeout inside the CustomEvent handler (e.g., 30s). If exceeded, return JSON-RPC error `code: -32003, message: "Operation timed out"`.
- Component B: HTTP client timeout set to 35s (slightly higher than A's internal timeout to avoid double-timeout races).
- Future enhancement: for very long operations, Component A can return a `jobId` immediately, and Component B polls a `getJobStatus` method.

**Authentication/Security**:
- **Localhost only**. Component A binds to `127.0.0.1` on a configurable port (default: 9876).
- **No auth tokens**. The threat model is local — only processes on the same machine can reach it. If needed later, add a simple shared secret via env var.
- **CORS**: Not applicable (no browser client).

---

### 3. Tool Implementations Feasibility

Based on Fusion 360 API knowledge (Autodesk Fusion 360 API Reference, Python):

#### `get_active_design_parameters`
- **API surface**: `design.userParameters` → `adsk.fusion.UserParameters` → iterate `userParam.name`, `userParam.expression`, `userParam.value`.
- **Units**: Fusion internally stores lengths in **cm**, angles in **degrees**. The PRD requires `value_cm` and `value_deg` in the response — this is straightforward.
- **Risk**: `userParam.value` returns the evaluated value in the document's internal units. Conversion to mm (if needed) is `value_cm * 10`.
- **Feasibility**: ✅ HIGH. Well-documented, stable API.

#### `measure_clearance`
- **API surface**: `measureManager = app.measureManager` → `measureManager.measureMinimumDistance(body1, body2)`.
- **Input**: `body1_name`, `body2_name` → need to resolve bodies by name from `design.rootComponent.bodies`.
- **Output**: Returns a `MinimumDistance` object with `.value` (distance in cm) and `.isIntersecting` (boolean).
- **Risk**: If bodies are in different components, need to use `occurrence1` and `occurrence2` references. The MVP can assume bodies are in the root component.
- **Feasibility**: ✅ HIGH. `measureMinimumDistance` is the correct API.

#### `update_user_parameter`
- **API surface**: `userParam = design.userParameters.itemByName(name)` → `userParam.expression = new_expression` → `design.computeAll()`.
- **Force recompute**: `design.computeAll()` is correct. It recomputes the entire timeline.
- **Risk**: If the expression causes a geometry error (e.g., over-constrained sketch), `computeAll()` throws an exception. Must catch and return error.
- **Units**: The agent sends expressions like `"40 mm"`. Fusion's `expression` setter accepts unit strings natively.
- **Feasibility**: ✅ HIGH. Standard parametric workflow.

#### `create_hardware_cutout`
- **API surface**:
  1. Get target body and face: `body = rootComponent.bodies.itemByName(target_body)` → `face = body.faces.item(face_index)`.
  2. Create sketch on face: `sketches = component.sketches` → `sketch = sketches.add(face)`.
  3. Draw circle: `sketch.sketchCurves.sketchCircles.addByCenterRadius(centerPoint, radius)`.
  4. Extrude cut: `extrudes = component.features.extrudeFeatures` → `extrudeInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)` → `extrudeInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth_cm))` → `extrudes.add(extrudeInput)`.
- **Units**: `diameter_mm` and `depth_mm` must be converted to cm before passing to Fusion API.
- **Risk**: Face selection by index is fragile — face ordering can change. Better to use a stable identifier (e.g., face centroid or persistent name) if available. For MVP, `face_index` is acceptable with documented caveats.
- **Feasibility**: ✅ MEDIUM-HIGH. Requires multiple API steps; error handling at each step is critical.

---

### 4. Node.js MCP SDK Considerations

**SDK**: `@modelcontextprotocol/sdk` (TypeScript).

**Tool registration pattern** (from SDK docs):
```typescript
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new McpServer({ name: 'fusion360-mcp', version: '1.0.0' });

server.tool('get_active_design_parameters', {}, async () => {
  const response = await fetch('http://localhost:9876', {
    method: 'POST',
    body: JSON.stringify({ jsonrpc: '2.0', method: 'get_active_design_parameters', params: {}, id: 1 }),
  });
  const result = await response.json();
  return { content: [{ type: 'text', text: JSON.stringify(result.result) }] };
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

**Key considerations**:
- **Zod schemas**: The `McpServer.tool()` API accepts Zod schemas for parameter validation. Use `z.object({ ... })` for each tool.
- **Error handling**: If Component A returns a JSON-RPC error, return an MCP `CallToolResult` with `isError: true` and the error message. Do NOT throw — MCP expects a result object.
- **Logging**: Use `ctx.log()` (if available) to send debug info to the MCP client.
- **HTTP client**: Use native `fetch` (Node 18+) or `axios` if proxy support is needed. No complex HTTP client needed.

---

### 5. Project Structure Recommendations

**Recommendation**: Monorepo with two top-level packages + a shared types package.

```
mcp-fusion360/
├── add-in/                 # Component A — Python
│   ├── manifest/
│   ├── server/
│   ├── handlers/
│   └── main.py
├── mcp-server/             # Component B — Node.js/TypeScript
│   ├── src/
│   ├── package.json
│   └── tsconfig.json
├── shared/                 # Shared TypeScript types (optional)
│   └── types.ts
├── openspec/
├── prd.md
└── README.md
```

**Why not a shared package for Python**? Component A is Python, Component B is TypeScript. Shared types are only useful if we generate JSON schemas or TypeScript-to-Python converters. For MVP, keep the wire format documented in the spec and duplicate lightweight types in each language. Add a shared schema (e.g., JSON Schema) if the contract grows.

**Package managers**:
- Component A: no package manager — Fusion 360 Python is embedded. Code is loaded as an Add-in via `.manifest` file.
- Component B: `npm` or `pnpm`. Standard Node.js project.

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| **HTTP over WebSocket** | MCP is request-response; WebSocket adds complexity with no benefit. HTTP is simpler to debug and implement. |
| **JSON-RPC 2.0 over HTTP** | Natural mapping from tools to methods. Unified error handling. Easier to batch if needed later. |
| **Localhost-only, no auth** | Threat model is local. Can add a shared secret later if needed. |
| **Monorepo, two packages** | Clear separation of concerns. Component A and B have different runtimes and build processes. |
| **Per-component specs** | OpenSpec config requires separating specs per component (A/B). This aligns with the two-package structure. |

---

## Open Questions

1. **Port collision**: What if port 9876 is taken? Should Component A auto-increment or write a port file? **Recommendation**: Allow configurable port, default to 9876, log the actual port on startup.
2. **Component B startup**: How does Component B know where Component A is running? **Recommendation**: Component B reads `FUSION360_MCP_PORT` env var, default 9876. The user must start Fusion 360 (which loads Component A) before starting the MCP server.
3. **Error granularity**: Should Fusion API stack traces be exposed to the LLM? **Recommendation**: For MVP, yes — the PRD says "devolver el mensaje de error de la API al agente". Sanitize later if needed.
4. **Face selection stability**: `face_index` is fragile. **Recommendation**: Document this as an MVP limitation. Future enhancement: use `face.nativeObject` or persistent ID if available.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Fusion 360 API changes between versions | Medium | Stick to stable API (`userParameters`, `measureMinimumDistance`, `computeAll`). Document Fusion 360 version tested. |
| `computeAll()` can be very slow on complex designs | Medium | Set a long timeout (30s). If timeout is hit, inform the LLM and suggest retry or simplify. |
| Component A thread-safety with CustomEvent | Low | Use `adsk.core.CustomEvent` as documented. Queue requests if multiple arrive simultaneously. |
| No automated testing for Component A | High | Acknowledged. Manual testing via Fusion 360 GUI is required. Component B can be unit-tested with mocked HTTP server. |
| `face_index` fragility in `create_hardware_cutout` | Medium | Document clearly in tool description. Future: add face selection by name or centroid. |

---

## Recommendation

Proceed with **HTTP + JSON-RPC 2.0** as the communication protocol. The simplicity and debuggability are critical for a greenfield project where manual testing in Fusion 360 is required. All four MVP tools are feasible with the documented Fusion API surface.

---

## Ready for Proposal

**Yes**. The next step is `sdd-propose` to formalize the change scope, followed by `sdd-spec` to write the component-separated specs. The orchestrator should inform the user that the exploration is complete and the communication protocol decision is:

> **HTTP on localhost with JSON-RPC 2.0**. This is the simplest, most debuggable approach that matches the request-response nature of the MCP protocol. WebSocket was evaluated but rejected as overkill for this use case.

---

*Generated by sdd-explore phase for change `fusion360-mcp-server`.*
