# Manual Test Checklist — Face Index and Runtime Coverage

Use this checklist to close the three highest-priority `UNTESTED` scenarios from the `fusion360-mcp-server` verify report (A1, A2, F3) and to verify the runtime behavior of the new `face_selector` parameter and the enriched `get_body_info.faces` enumeration.

Component A cannot be verified automatically — `adsk` is only available inside Fusion's embedded Python interpreter. The user must run the Add-in inside Fusion 360 and exercise the tools.

## Environment

- Fusion 360 installed and running
- `Fusion360MCP/` folder copied to the Fusion 360 Add-ins directory
  (typically `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`)
  or loaded via **Scripts and Add-Ins → Add-Ins → Add…**
- `mcp-server/` built: `cd mcp-server && npm install && npx tsc`
- Optional: [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
  or any MCP client for E2E testing (used by F3)

---

## A. Add-in Lifecycle

| # | Step | Command / Action | Expected Result | Status |
|---|------|------------------|-----------------|--------|
| A1 | Install Add-in | Copy `Fusion360MCP/` to the Fusion 360 Add-ins directory; open Scripts and Add-Ins | Add-in appears in the list as `Fusion360MCP` | [ ] |
| A2 | Start Add-in | Click **Run** on `Fusion360MCP` in Scripts and Add-Ins | Text Commands palette shows: `Fusion 360 MCP Server listening on port <X>` (default `9876`, env override via `FUSION360_MCP_PORT`) | [ ] |

---

## F. End-to-End via MCP (Component B)

| # | Step | Command / Action | Expected Result | Status |
|---|------|------------------|-----------------|--------|
| F3 | `get_active_design_parameters` E2E | With the Add-in running, start the MCP server (`cd mcp-server && node dist/index.js`) and connect MCP Inspector; call the `get_active_design_parameters` tool with `{}` | Tool returns the user parameters from the active Fusion 360 design; each entry has `name`, `expression`, `value` (mm), `unit`, `comment` (string or `null`), `is_favorite` (bool) | [ ] |

---

## Verification Notes

- **A1 and A2** verify the Add-in load path that the new `face_selector` and per-face enumeration code depends on. If A1 or A2 fail, F3 and the runtime cutout scenarios cannot be exercised.
- **F3** is the only E2E round-trip (Add-in → HTTP → MCP) in this change. It exercises `handle_get_active_design_parameters` and the `comment` / `is_favorite` delta fields. A clean F3 run is strong evidence that the per-face enumeration payload (added in `handle_get_body_info`) will also reach an MCP client, since both share the same JSON-RPC wire path.
- This checklist is **intentionally minimal**: the new `face_selector` parameter and the `get_body_info.faces` enrichment are exercised by the static review in the verify report; the manual gate exists to close the three `UNTESTED` scenarios and to surface any wiring regressions the static review could not catch.

---

## Sign-off

| Role | Name | Date | Result |
|------|------|------|--------|
| Tester | | | ☐ PASS / ☐ FAIL |
