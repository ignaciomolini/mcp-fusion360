# Manual Test Checklist — Fusion 360 MCP Server

Use this checklist when testing the Add-in inside Fusion 360. Component A cannot be verified automatically outside Fusion's embedded Python interpreter.

## Environment

- Fusion 360 installed and running
- `add-in/` folder copied to Fusion 360 Add-ins directory (or loaded via Scripts and Add-Ins)
- `mcp-server/` built: `cd mcp-server && npm install && npx tsc`
- Optional: [MCP Inspector](https://github.com/modelcontextprotocol/inspector) or any MCP client for E2E testing

---

## A. Add-in Lifecycle

| # | Step | Command / Action | Expected Result | Status |
|---|------|------------------|-----------------|--------|
| A1 | Install Add-in | Copy `add-in/` to Fusion Add-ins directory; open Scripts and Add-Ins | Add-in appears in list | [ ] |
| A2 | Start Add-in | Click **Run** on `Fusion360MCP` | Text Commands shows: `Fusion 360 MCP Server listening on port X` | [ ] |
| A3 | Port override | Close Add-in, set env `FUSION360_MCP_PORT=9999`, restart | Server binds to port 9999 | [ ] |
| A4 | Port auto-increment | Start Add-in twice (or block 9876) | Second instance binds to 9877 | [ ] |
| A5 | Stop Add-in | Click **Stop** | Server stops; `curl` to port times out/refused | [ ] |

---

## B. HTTP / JSON-RPC Sanity (Component A)

Run these with `curl` from a terminal while the Add-in is loaded.

| # | Step | Command | Expected Result | Status |
|---|------|---------|-----------------|--------|
| B1 | Valid request | `curl -X POST http://127.0.0.1:9876 -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"get_active_design_parameters","id":1}'` | JSON with `result.parameters` | [ ] |
| B2 | Malformed JSON | `curl -X POST http://127.0.0.1:9876 -d 'not json'` | `{"error":{"code":-32700,...}}` | [ ] |
| B3 | Non-POST method | `curl http://127.0.0.1:9876` | HTTP 405 with JSON-RPC error | [ ] |
| B4 | Unknown method | `curl -X POST ... -d '{"jsonrpc":"2.0","method":"unknown","id":1}'` | `{"error":{"code":-32601,...}}` | [ ] |

---

## C. Reading & Analysis Tools

Prerequisite: open any Fusion 360 design with at least one User Parameter and two named solid bodies.

| # | Tool | Params | Expected Result | Status |
|---|------|--------|-----------------|--------|
| C1 | `get_active_design_parameters` | `{}` | Returns array of user params with `name`, `expression`, `value` (mm), `unit` | [ ] |
| C2 | `measure_clearance` | `{"body1_name":"Box1","body2_name":"Box2"}` | Returns `distance_mm` and `is_interfering` | [ ] |
| C3 | `measure_clearance` (same body) | `{"body1_name":"Box1","body2_name":"Box1"}` | Error `-32001`: bodies must be different | [ ] |
| C4 | `measure_clearance` (missing body) | `{"body1_name":"Ghost","body2_name":"Box2"}` | Error `-32001`: body not found | [ ] |
| C5 | Any tool (no design) | Close all docs, call any tool | Error `-32002`: no active design | [ ] |

---

## D. Modification Tools

Prerequisite: design with User Parameters and a solid body named `Panel`.

| # | Tool | Params | Expected Result | Status |
|---|------|--------|-----------------|--------|
| D1 | `update_user_parameter` | `{"parameter_name":"Width","new_expression":"50 mm"}` | Parameter updates in Fusion; returns `recomputed: true` | [ ] |
| D2 | `update_user_parameter` rollback | Set expression that breaks timeline (e.g. negative where positive required) | Original parameter value restored; error returned | [ ] |
| D3 | `update_user_parameter` (unknown param) | `{"parameter_name":"Missing","new_expression":"10 mm"}` | Error `-32001`: parameter not found | [ ] |

---

## E. Cutout Tools

Prerequisite: a solid body named `Panel` with at least one planar face.

| # | Tool | Params | Expected Result | Status |
|---|------|--------|-----------------|--------|
| E1 | `create_circular_cutout` | `{"target_body":"Panel","face_index":1,"diameter_mm":10,"depth_mm":5}` | Circular hole cut into face | [ ] |
| E2 | `create_rectangular_cutout` | `{"target_body":"Panel","face_index":1,"width_mm":20,"height_mm":10,"depth_mm":5,"angle_deg":45}` | Rotated rectangle cut | [ ] |
| E3 | `create_slot_cutout` | `{"target_body":"Panel","face_index":1,"length_mm":30,"width_mm":8,"depth_mm":5}` | Slot/obround cut | [ ] |
| E4 | Invalid `face_index` | `{"target_body":"Panel","face_index":99,...}` | Error `-32001`: invalid face_index | [ ] |
| E5 | Negative dimension | `{"target_body":"Panel","face_index":1,"diameter_mm":-5,"depth_mm":5}` | Error `-32001`: positive number required | [ ] |
| E6 | Body not found | `{"target_body":"Ghost",...}` | Error `-32001`: body not found | [ ] |
| E7 | Slot length == width | `{"target_body":"Panel","face_index":1,"length_mm":10,"width_mm":10,"depth_mm":5}` | Currently rejected (`length <= width`). Decide if OK or fix to `<` | [ ] |

---

## F. End-to-End via MCP (Component B)

| # | Step | Command / Action | Expected Result | Status |
|---|------|------------------|-----------------|--------|
| F1 | Start MCP server | `cd mcp-server && node dist/index.js` | Server starts on stdio | [ ] |
| F2 | `tools/list` | Use MCP Inspector or client | Returns 6 tools | [ ] |
| F3 | `get_active_design_parameters` | Call tool with `{}` | Returns parameters from Fusion | [ ] |
| F4 | `update_user_parameter` | Call tool with valid params | Parameter updates and returns success | [ ] |
| F5 | `create_circular_cutout` | Call tool with valid params | Hole created in Fusion | [ ] |
| F6 | Component A not running | Stop Add-in, call any tool | Error: Connection refused / Component A not running | [ ] |
| F7 | No `adsk` in Component B | `grep -r "adsk" mcp-server/src/` | Zero matches | [ ] |

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Tester | | | ☐ PASS / ☐ FAIL |

## Known Limitations to Accept or Flag

- `face_index` is fragile: face order may change after design edits
- Component A cannot be unit-tested outside Fusion 360
- `computeAll()` timeout is 30s; complex assemblies may need longer
- Invalid expression errors currently return `-32000` (Fusion API error) instead of `-32001` (invalid parameter)
