# Tasks: Fusion 360 MCP Server

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,095 (14 new files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 4 chained PRs (see below) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Component A infrastructure | PR 1 | Base: tracker branch. Server, JSON-RPC, bridge, errors, manifest. ~285 lines |
| 2 | Component A handlers + tools | PR 2 | Base: PR 1 branch. All 6 handlers, validation, unit conversion. ~330 lines |
| 3 | Component B infrastructure | PR 3 | Base: PR 2 branch. Scaffolding, types, client, error translation. ~200 lines |
| 4 | Component B tools + bootstrap | PR 4 | Base: PR 3 branch. Tool schemas, server registration, E2E wiring. ~280 lines |

Each unit is independently verifiable: (1) with curl, (2) with curl, (3) with unit tests, (4) with MCP inspector or tool/list.

Chain strategy is **pending** — user must choose between `stacked-to-main` (each PR merges to main, simplest for independent components) or `feature-branch-chain` (all PRs base on previous, final tracker merge). Since Component A (Python) and Component B (Node.js) have **zero file overlap**, `stacked-to-main` is cleaner — each diff shows only its own files.

## Phase 1: Component A Infrastructure

- [x] **1.1** `add-in/Fusion360MCP.manifest` — XML manifest with GUID, `<Script File="Fusion360MCP.py"/>`. P1. Deps: none. ~15 lines. AC: Fusion 360 loads the add-in.
- [x] **1.2** `add-in/jsonrpc.py` — `build_request()`, `parse_response()`, `validate_id()`. JSON-RPC 2.0 parse error (-32700). P1. Deps: none. ~50 lines. AC: malformed JSON returns code -32700.
- [x] **1.3** `add-in/errors.py` — `FusionAPIError`, error code constants (-32000 to -32003), `fusion_error(code, detail)` builder. P1. Deps: 1.2. ~40 lines. AC: each code produces correct structure.
- [x] **1.4** `add-in/server.py` — `BaseHTTPRequestHandler`, POST-only, route by method name, port from `FUSION360_MCP_PORT` (default 9876), auto-increment on collision, 30s per-request timeout. P1. Deps: 1.2, 1.3. ~120 lines. AC: non-POST returns 405, invalid JSON returns -32700, port collision increments.
- [x] **1.5** `add-in/fusion_bridge.py` — `RequestBridge` class: CustomEvent registration, `threading.Event` per request, synchronous queue, sequential dispatch. P1. Deps: 1.4. ~60 lines. AC: concurrent requests process sequentially, timeout returns -32003.

## Phase 2: Component A Tools & Handlers

- [x] **2.1** `add-in/Fusion360MCP.py` — Entry point: `run()` starts server + bridge threads, `stop()` shuts down, logs bound port to Fusion console. P1. Deps: 1.4, 1.5. ~50 lines. AC: `run()` logs "Fusion 360 MCP Server listening on port X".
- [x] **2.2** `add-in/tools.py` — `mm_to_cm()`, `cm_to_mm()`, shared validators: `resolve_body(name)`, `validate_face_index(body, index)`, `validate_positive(value, name)`. P1. Deps: 1.3. ~80 lines. AC: 10mm→1cm, negative value returns -32001, body not found returns -32001.
- [x] **2.3** `add-in/handlers.py` — All 6 handlers:
  - `handle_get_active_design_parameters` — iterate `design.userParameters`, return `[{name, expression, value, unit}]`
  - `handle_measure_clearance` — `measureManager.measureMinimumDistance`, return `{distance_mm, is_interfering}`
  - `handle_update_user_parameter` — snapshot all params, mutate, `computeAll()`, rollback on failure
  - `handle_create_circular_cutout` — sketch circle, extrude cut
  - `handle_create_rectangular_cutout` — sketch centered rect, extrude cut, optional rotation
  - `handle_create_slot_cutout` — sketch obround profile, extrude cut, optional rotation
  - P1. Deps: 2.2. ~250 lines. AC: each handler matches spec scenarios; rollback restores all params on computeAll failure.

## Phase 3: Component B Infrastructure

- [x] **3.1** `mcp-server/package.json` + `tsconfig.json` — `@modelcontextprotocol/sdk` dep, `zod`, strict TS, ESM output. P1. Deps: none. ~40 lines. AC: `npm install && npx tsc --noEmit` succeeds.
- [x] **3.2** `mcp-server/src/types.ts` — `JsonRpcRequest`, `JsonRpcResponse`, `JsonRpcError` interfaces for JSON-RPC 2.0. P1. Deps: 3.1. ~40 lines. AC: compiles, matches spec wire format.
- [x] **3.3** `mcp-server/src/errors.ts` — `toMcpError(jsonRpcError)` → `{isError: true, content: [{type:"text", text:...}]}`. P1. Deps: 3.2. ~40 lines. AC: error response returns `isError: true`, success returns no `isError`.
- [x] **3.4** `mcp-server/src/jsonrpc-client.ts` — `FusionClient` class: `call(method, params)` → native `fetch` POST to `http://127.0.0.1:{port}`, 35s timeout, port from `FUSION360_MCP_PORT` (default 9876). P1. Deps: 3.2, 3.3. ~80 lines. AC: connection refused returns "Connection refused", valid response returns parsed result.

## Phase 4: Component B Tools & Integration

- [x] **4.1** `mcp-server/src/tools.ts` — 6 Zod schemas with descriptions + handler functions. Each handler calls `FusionClient.call(method, params)`. Schemas enforce required params, numeric types, optional `angle_deg`. P1. Deps: 3.4. ~200 lines. AC: missing required param rejected by Zod, each schema describes all params.
- [x] **4.2** `mcp-server/src/index.ts` — `McpServer` bootstrap, `StdioServerTransport`, `server.tool()` for all 6 tools, `server.connect(transport)`, handshake logging. P1. Deps: 4.1. ~80 lines. AC: `tools/list` returns 6 tools, `get_active_design_parameters` returns Fusion data end-to-end via MCP inspector. No `adsk` import anywhere in `mcp-server/`.
