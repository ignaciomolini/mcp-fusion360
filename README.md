# mcp-fusion360

MCP server for AI-driven Fusion 360 operations — translates MCP tool calls into JSON-RPC 2.0 requests against a local add-in.

## What it does

`mcp-fusion360` exposes a Fusion 360 design as a set of MCP tools that an LLM agent can call. The agent sends a tool call over stdio; the MCP server forwards it to a Python add-in running inside Fusion 360 over local HTTP; the add-in dispatches the work to the Fusion API on the main thread and returns the result. The agent never touches Fusion directly — it sees only the tool surface.

The target user is a developer or technical user prototyping AI-driven CAD automation: a script that sweeps a parameter across a range, an agent that inspects a design before generating a cut, a tool that flags interferences between two bodies. It is not a click-to-Fusion product; it is a programmatic surface for the parts of Fusion that benefit from being driven by a model.

## Architecture

The project is two components bridged by local HTTP, with the MCP client on the far end:

```
MCP client                     Component B                 Component A                 Fusion 360
(Claude Desktop,   stdio JSON-RPC   mcp-server/        HTTP POST 127.0.0.1:9876   Fusion360MCP.py
 Cursor, OpenCode) ──────────────►  (Node.js,          ─────────────────────────►  (Python, adsk API)
                       (MCP/JSON-  @modelcontext-      (JSON-RPC 2.0,             │
                        RPC 1.0)  protocol/sdk)         POST only)                ▼
                                                                              Fusion main thread
                                                                              via RequestBridge
```

- **MCP client** — any host that speaks MCP over stdio (Claude Desktop, Cursor, OpenCode, etc.). It spawns Component B as a subprocess and exchanges JSON-RPC 1.0 messages on stdin/stdout.
- **Component B** — `mcp-server/`, a Node.js process built on `@modelcontextprotocol/sdk`. It registers the 11 tool shapes, validates each call with Zod, and forwards it to Component A over HTTP. The default port is `9876`, overridable via the `FUSION360_MCP_PORT` env var.
- **Component A** — `Fusion360MCP/`, a Fusion 360 add-in written in Python. `Fusion360MCP.py` is the entry point loaded by Fusion's Add-Ins dialog; `server.py` starts an `http.server` daemon thread that accepts POSTs on `127.0.0.1:9876`; `fusion_bridge.py` (the `RequestBridge`) posts each call to Fusion's main thread via the `CustomEvent` system so the `adsk` API is touched on the thread that owns it.

Key files: `mcp-server/src/index.ts` (stdio server), `mcp-server/src/tools.ts` (the 11 Zod shapes), `mcp-server/src/jsonrpc-client.ts` (HTTP client), `Fusion360MCP/Fusion360MCP.py` (add-in entry), `Fusion360MCP/server.py` (HTTP server), `Fusion360MCP/handlers.py` (per-tool handlers), `Fusion360MCP/fusion_bridge.py` (main-thread bridge), `Fusion360MCP/tools.py` (face resolution and geometry helpers).

## Tools

11 tools, grouped into 4 capabilities. Every tool name is a snake_case identifier; inputs are validated by Zod at the MCP boundary before they reach the add-in.

### parameter-management

Read and write User Parameters in the active design, with automatic rollback on `computeAll()` failure.

- `get_active_design_parameters` — list every User Parameter with `name`, `expression`, `value`, `unit` (`"cm"` or `"deg"`), `comment`, and `is_favorite`.
  - Input: `{}`
  - Output: `Array<{ name, expression, value, unit, comment, is_favorite }>`
- `update_user_parameter` — change a parameter's expression and recompute the design. Snapshots all parameters first; on `computeAll()` failure, restores from the snapshot and returns error `-32000`.
  - Input: `{ parameter_name: string, new_expression: string }` (e.g. `new_expression: "50 mm"`)
  - Output: `{ parameter_name, old_expression, new_expression }`

### design-introspection

Read-only discovery of bodies, features, sketches, and document metadata. Use these before issuing mutating calls so the agent sees real names and indices.

- `get_document_info` — active document metadata.
  - Input: `{}`
  - Output: `{ name, units, design_type, material_library }` (`units` is `"mm"` or `"cm"`; `design_type` is `"ParametricDesign"` or `"DirectDesign"`)
- `list_bodies` — every solid body in the root component.
  - Input: `{}`
  - Output: `Array<{ name, index }>` (`index` is 1-based)
- `get_body_info` — physical properties of a named body plus per-face metadata for the first 100 faces.
  - Input: `{ body_name: string }`
  - Output: `{ face_count, bounding_box, volume_cm3, material, body_type, faces: Array<{ index, normal, centroid, area_mm2 }>, faces_truncated? }`
- `list_features` — timeline features (capped at 200; `truncated: true` if the timeline runs longer).
  - Input: `{}`
  - Output: `Array<{ name, type, is_suppressed, timestamp }>`
- `list_sketches` — sketches in the root component.
  - Input: `{}`
  - Output: `Array<{ name, profile_count, referenced_geometry }>`

### cutout-modeling

Sketch-based extrusion cutouts on a face of a target body. All dimensions are in millimeters at the tool interface; Component A converts to centimeters before calling the Fusion API.

Every cutout tool accepts **either** `face_index` (1-based integer, **deprecated** — present for back-compat with early callers) **or** `face_selector` (preferred — a geometry selector with `normal` and/or `centroid`). When both are sent, `face_index` wins during the deprecation period; pick one.

- `create_circular_cutout` — circular hole.
  - Input: `{ target_body: string, face_index?: number, face_selector?: { normal?, centroid?, tolerance_degrees?, tolerance_mm? }, diameter_mm: number, depth_mm: number }`
  - Output: `{ target_body, face_index, diameter_mm, depth_mm }`
- `create_rectangular_cutout` — centered rectangle, optionally rotated.
  - Input: `{ target_body, face_index?, face_selector?, width_mm, height_mm, depth_mm, angle_deg? (default 0) }`
  - Output: `{ target_body, face_index, width_mm, height_mm, depth_mm, angle_deg }`
- `create_slot_cutout` — slot (obround) profile, optionally rotated. `length_mm` must be `>= width_mm`.
  - Input: `{ target_body, face_index?, face_selector?, length_mm, width_mm, depth_mm, angle_deg? (default 0) }`
  - Output: `{ target_body, face_index, length_mm, width_mm, depth_mm, angle_deg }`

### geometry-analysis

- `measure_clearance` — minimum distance between two named bodies, with an `is_interfering` flag for overlap.[^1]
  - Input: `{ body1_name: string, body2_name: string }` (must be different)
  - Output: `{ distance_mm: number, is_interfering: boolean }` (negative distance means interference)

[^1]: Spec lives in `openspec/changes/fusion360-mcp-server/specs/geometry-analysis/spec.md` (not yet promoted to `openspec/specs/`). Behavior is implemented and tested; the spec is in-flight.

## Install

Two components to install: Component B (the MCP server) and Component A (the Fusion 360 add-in). Both ship in this repo.

1. **Clone the repo.**

   ```bash
   git clone <your fork or upstream URL> mcp-fusion360
   cd mcp-fusion360
   ```

2. **Build Component B.**

   ```bash
   cd mcp-server
   npm install
   npm run build
   ```

   This compiles `src/*.ts` to `dist/index.js`, which is what the MCP client spawns. To run the typecheck without emitting: `npm run typecheck`. To re-run the unit tests: `npm test`.

3. **Install Component A as a Fusion 360 add-in.**

   Copy or symlink the `Fusion360MCP/` directory into Fusion's AddIns folder:

   - **Windows**: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`
   - **macOS**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`

   The directory must be placed at the root of `AddIns/` (Fusion scans one level deep). The full path should end with `.../AddIns/Fusion360MCP/Fusion360MCP.manifest`.

4. **Start the add-in in Fusion.**

   In Fusion 360: `Tools → Add-Ins → Scripts and Add-Ins` → **Add-Ins** tab → select `Fusion360MCP` from the list → **Run**. Fusion shows a message box confirming the port (default `9876`). The add-in does **not** start on Fusion launch (`runOnStartup: false` in `Fusion360MCP.manifest`) — repeat this step each session, or set the flag to `true` in the manifest if you prefer.

## Configuration

Add the server to your MCP client's `mcpServers` config. The three blocks below are functionally identical — pick the one for the client you use. **Substitute the absolute path** to your clone in `args`; the MCP client spawns `node` with that exact path.

### Claude Desktop

Edit `claude_desktop_config.json`:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-fusion360/mcp-server/dist/index.js"]
    }
  }
}
```

### Cursor

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "node",
      "args": ["/absolute/path/to/mcp-fusion360/mcp-server/dist/index.js"]
    }
  }
}
```

### OpenCode

Edit your project's `opencode.json`:

```json
{
  "mcp": {
    "fusion360": {
      "type": "local",
      "command": "node",
      "args": ["/absolute/path/to/mcp-fusion360/mcp-server/dist/index.js"]
    }
  }
}
```

After editing the config, restart the client so it respawns the server. The client must be able to reach Component A on `127.0.0.1:9876`; if you change the port with `FUSION360_MCP_PORT` on the Fusion side, the MCP client picks it up on the next call (the port is read at startup, so a server restart is required if you change it later).

## Usage

Open a design in Fusion 360 that contains at least one body, start the `Fusion360MCP` add-in, and make sure the MCP client is connected. From the client, ask in natural language:

> "List the bodies in the active design and give me the bounding box of the first one."

The agent will call `list_bodies`, then `get_body_info` with the first body's name:

```text
User: List the bodies in the active design and give me the bounding box of the first one.
Tool call: list_bodies
Tool call: get_body_info  { "body_name": "Plate" }
```

The client does not use `curl` — MCP speaks JSON-RPC 1.0 over stdio, not HTTP. All HTTP traffic happens between Component B and Component A on `127.0.0.1:9876`, where the user never sees it.

## Development

```
mcp-fusion360/
├── Fusion360MCP/           Component A — Fusion 360 add-in (Python)
│   ├── Fusion360MCP.py     Add-in entry point (run/stop)
│   ├── Fusion360MCP.manifest
│   ├── server.py           HTTP JSON-RPC 2.0 server (daemon thread)
│   ├── fusion_bridge.py    RequestBridge — main-thread dispatch via CustomEvent
│   ├── handlers.py         Per-tool handlers (one per MCP tool)
│   ├── tools.py            resolve_face() and other geometry helpers
│   ├── jsonrpc.py          JSON-RPC 2.0 envelope, error codes
│   └── errors.py           Typed error classes, JSON-RPC error mapping
├── mcp-server/             Component B — MCP stdio wrapper (TypeScript)
│   ├── src/
│   │   ├── index.ts        Stdio MCP server, tool registrations
│   │   ├── tools.ts        11 Zod shapes + handler functions
│   │   ├── jsonrpc-client.ts  HTTP client to Component A
│   │   ├── types.ts        Shared TypeScript types
│   │   ├── errors.ts       JSON-RPC error mapping
│   │   └── tools.test.ts   Vitest unit tests for the handlers
│   ├── package.json
│   └── tsconfig.json
├── openspec/               SDD workflow — specs, changes, config.yaml
├── prd.md                  Spanish PRD (legacy — not the source of truth)
├── LICENSE                 MIT
└── README.md               This file
```

Build commands (run from `mcp-server/`):

| Command            | What it does                                          |
|--------------------|-------------------------------------------------------|
| `npm run build`    | Compile TypeScript to `dist/` (`tsc`)                |
| `npm run typecheck`| Type-check without emitting (`tsc --noEmit`)         |
| `npm test`         | Run the Vitest suite once                            |
| `npm start`        | Run the compiled server (`node dist/index.js`) — the MCP client does this for you |

Component A has no build step. `Fusion360MCP.py` is loaded by Fusion directly from the AddIns directory.

## Testing

| Component | Test command                         | What it covers                                                                |
|-----------|--------------------------------------|-------------------------------------------------------------------------------|
| B         | `cd mcp-server && npm test`          | Vitest suite in `mcp-server/src/tools.test.ts` — argument shape, Zod validation, and the JSON-RPC client against a stubbed HTTP server. |
| A         | `openspec/changes/<name>/manual-test-checklist.md` | Component A runs inside Fusion, so the `adsk` API is unavailable in CI. Each change ships a manual checklist in its change folder; the convention is to walk it before archiving the change. |

The 11 tool shapes are exercised in `tools.test.ts`. End-to-end coverage of the add-in itself is manual — open Fusion, start the add-in, and run the relevant scenario from the change's checklist.

## License

MIT — see [LICENSE](./LICENSE) for the full text.
