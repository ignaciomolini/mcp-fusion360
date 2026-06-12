# Design: Fusion 360 MCP Server

Component A (Python add-in) serves JSON-RPC 2.0 over HTTP on localhost. Component B (TypeScript) translates MCP stdio tool calls to HTTP requests. Wire contract enforced by documentation.

## Technical Approach

Component A uses Python stdlib `http.server` in a daemon thread. Requests are dispatched to Fusion's main thread via `adsk.core.CustomEvent` using a synchronous queue (one `threading.Event` per request). Component B uses `@modelcontextprotocol/sdk` v2 `registerTool` API with Zod schemas. Each tool handler sends a JSON-RPC POST via native `fetch` (Node 18+).

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| HTTP server (Component A) | `http.server.BaseHTTPRequestHandler` (stdlib) | Flask, aiohttp | Fusion's embedded Python has no pip. stdlib only. |
| Thread bridge | `threading.Event` per request + queue | Polling, WebSocket | Synchronous wait matches JSON-RPC request-response. No async complexity. |
| Wire protocol | JSON-RPC 2.0 over HTTP POST | REST, WebSocket | Natural tool→method mapping. Unified error model. Debuggable via curl. |
| MCP SDK API | `registerTool` (v2) with `inputSchema` | `server.tool` (v1) | v2 is current API. Config object with description + Zod schema. |
| Rollback mechanism | Snapshot dict of `{name: expression}` before mutation | Fusion undo groups | Undo API is unreliable across timeline features. Explicit snapshot is deterministic. |
| Unit conversion | Component A converts mm→cm at handler boundary | Component B converts | Keeps Component B unit-agnostic. Fusion always receives cm. Single conversion point. |
| Project layout | Two top-level dirs: `add-in/`, `mcp-server/` | npm workspaces, shared pkg | Different runtimes, no shared deps. Shared types add build complexity for 6 methods. |

## Data Flow

```
LLM ──stdio──► Component B (fetch) ──HTTP POST──► Component A (http.server)
             ◄──response───────────                    │ queue → CustomEvent
                                                       ▼ main thread → adsk API
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `add-in/manifest/Fusion360MCP.manifest` | Create | Add-in manifest with GUID and startup script |
| `add-in/main.py` | Create | Entry point: `run()`, `stop()`, starts HTTP server thread |
| `add-in/server.py` | Create | `HTTPServer` + handler, JSON-RPC parse/response |
| `add-in/bridge.py` | Create | `CustomEvent` registration, request queue, `threading.Event` sync |
| `add-in/handlers.py` | Create | 6 method handlers (parameters, measure, update, 3 cutouts) |
| `add-in/units.py` | Create | `mm_to_cm()`, `cm_to_mm()` conversions |
| `add-in/errors.py` | Create | Error codes, `FusionAPIError` wrapper, JSON-RPC error builders |
| `mcp-server/package.json` | Create | `@modelcontextprotocol/sdk`, `zod`, `typescript` |
| `mcp-server/tsconfig.json` | Create | Strict TS, ESM output |
| `mcp-server/src/index.ts` | Create | Server bootstrap, `StdioServerTransport`, tool registration |
| `mcp-server/src/client.ts` | Create | `FusionClient`: `fetch` wrapper, JSON-RPC builder, timeout |
| `mcp-server/src/tools.ts` | Create | 6 Zod schemas + handler functions |
| `mcp-server/src/errors.ts` | Create | JSON-RPC → MCP `CallToolResult` translation |
| `mcp-server/src/types.ts` | Create | JSON-RPC request/response interfaces |

## Interfaces / Contracts

### JSON-RPC Method Signatures

```
get_active_design_parameters(params: {}) → { parameters: [{name, expression, value, unit}] }
measure_clearance(params: {body1_name, body2_name}) → { distance_mm, is_interfering }
update_user_parameter(params: {parameter_name, new_expression}) → { success: true }
create_circular_cutout(params: {target_body, face_index, diameter_mm, depth_mm}) → { success: true }
create_rectangular_cutout(params: {target_body, face_index, width_mm, height_mm, depth_mm, angle_deg?}) → { success: true }
create_slot_cutout(params: {target_body, face_index, length_mm, width_mm, depth_mm, angle_deg?}) → { success: true }
```

### Error Code Table

| Code | Category | Source | MCP Translation |
|------|----------|--------|-----------------|
| `-32700` | Parse error | JSON-RPC | `isError: true` |
| `-32601` | Method not found | JSON-RPC | `isError: true` |
| `-32000` | Fusion API runtime error | `adsk` exception | `isError: true` + message |
| `-32001` | Invalid parameter | Pre-validation | `isError: true` + message |
| `-32002` | No active design | `app.activeDocument` null | `isError: true` + message |
| `-32003` | Operation timeout | 30s exceeded | `isError: true` + message |

### CustomEvent Bridge (bridge.py)

```python
class RequestBridge:
    def submit(self, method, params) -> dict:
        event = threading.Event()
        envelope = {"method": method, "params": params, "event": event, "result": None}
        self._queue.put(envelope)
        adsk.core.Application.get().fireCustomEvent(self._event_id)
        event.wait(timeout=30)  # blocks HTTP thread until main thread completes
        return envelope["result"]
```

## Testing Strategy

| Layer | Component A | Component B |
|-------|-------------|-------------|
| Unit | Not possible (requires `adsk`) | Mock `fetch` in `FusionClient`, error translation, Zod validation |
| Integration | Manual in Fusion GUI | Mock HTTP endpoint with JSON-RPC fixtures |
| E2E | Requires Fusion 360 | Full pipeline: MCP client → B → A → Fusion API |

## Fusion 360 Manifest

`add-in/manifest/Fusion360MCP.manifest` — standard XML with `<StartupScripts><Script File="main.py"/></StartupScripts>` and a generated GUID.

## Migration / Rollout

Greenfield. Install add-in → start Fusion 360 → configure MCP client.

## Open Questions

- [ ] Should Component A auto-increment port on collision, or fail with clear error?
- [ ] Should `face_index` accept negative indices (Python-style) for "last face"?
