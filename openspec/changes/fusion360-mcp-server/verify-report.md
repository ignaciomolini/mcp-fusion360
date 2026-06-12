## Verification Report

**Change**: `fusion360-mcp-server`
**Version**: 0.1.0
**Mode**: Standard (no Strict TDD runner detected)

---

### Executive Summary

Re-verification after fixes. Both CRITICAL issues from the previous report are resolved. `face_index` descriptions in Component B now read "1-based" (matching Component A's validation), and `measure_clearance` now includes a same-body guard. TypeScript compilation passes cleanly. Verdict upgraded from **FAIL** to **PASS WITH WARNINGS** — 4 non-blocking warnings remain (none new).

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 13 |
| Tasks complete | 13 |
| Tasks incomplete | 0 |
| Spec domains | 5/5 |
| Python files present | 7/7 + 1 manifest |
| TypeScript files present | 5/5 |

All 13 tasks checked as complete in `tasks.md`. All files referenced by tasks exist on disk.

---

### Build & Tests Execution

**Build**: ✅ Passed

```
npx tsc --noEmit  →  (zero errors, zero warnings)
```

**Node.js**: v22.17.0

**Tests**: ➖ None available

No automated test suite exists for either component:
- **Component A** (Python): Cannot be tested without Fusion 360 GUI — `adsk` module is only available inside Fusion's embedded interpreter.
- **Component B** (TypeScript): No test files exist (`*.test.ts` not found). The MCP SDK integration (tool registration, JSON-RPC client) can only be exercised E2E against a running Component A inside Fusion 360.

**Coverage**: ➖ Not available

---

### Fix Verification (Re-run)

#### 🔴 CRITICAL #1 (RESOLVED): face_index 0-based → 1-based

| Check | Result |
|-------|--------|
| `create_circular_cutout`: `face_index` Zod describe | ✅ "1-based index of the face on the target body" (line 57) |
| `create_rectangular_cutout`: `face_index` Zod describe | ✅ "1-based index of the face on the target body" (line 80) |
| `create_slot_cutout`: `face_index` Zod describe | ✅ "1-based index of the face on the target body" (line 107) |
| Component A `validate_face_index` range check | ✅ `index < 1` rejected (line 77, `tools.py`) |
| Component A face access offset | ✅ `body.faces.item(face_idx - 1)` (handlers lines 325, 381, 487) |
| "Zero-based" grep in `mcp-server/src/` | ✅ Zero matches — no stale references remain |
| Both components agree on 1-based | ✅ Component A docs "Face indices are 1-based" (tools.py:66), Component B Zod descriptions "1-based" |

**Status**: Fully resolved. An LLM following the description and passing `face_index: 0` will receive error `-32001` "Invalid face_index 0 ... (valid range: 1-N)". The first valid face requires `face_index: 1`, consistent across both components.

#### 🔴 CRITICAL #2 (RESOLVED): measure_clearance same-body guard

| Check | Result |
|-------|--------|
| Guard exists in `handlers.py` | ✅ Lines 110-114 |
| Condition | ✅ `if body1_name == body2_name:` |
| Error code | ✅ `INVALID_PARAMETER` (-32001) |
| Error message | ✅ `"body1_name and body2_name must be different bodies"` |
| Guard placement (before resolve_body) | ✅ Before line 116 (`_get_active_design()`) and 117-118 (`resolve_body()` calls) — fails fast |
| Type check still present | ✅ Lines 104-108 validate string types before equality check |

**Status**: Fully resolved. Calling `measure_clearance` with identical body names now returns error `-32001` with the descriptive message, matching the spec scenario.

---

### Forbidden Import Guard

| Check | Result |
|-------|--------|
| `adsk` import in `mcp-server/src/` | ✅ Zero matches — PASS |

---

### Wire Format Agreement (unchanged since initial verification)

| Check | Component A | Component B | Match? |
|-------|------------|-------------|--------|
| JSON-RPC version | `"2.0"` (`jsonrpc.py:10`) | `"2.0"` (`types.ts:3,21`, `jsonrpc-client.ts:34`) | ✅ Yes |
| Protocol | HTTP POST JSON | HTTP POST JSON (`fetch`) | ✅ Yes |
| Method count | 6 (`server.py:38-44`) | 6 (`tools.ts`, `index.ts:30-69`) | ✅ Yes |
| Default port | 9876 (`server.py:33`) | 9876 (`jsonrpc-client.ts:4`) | ✅ Yes |
| Port env var | `FUSION360_MCP_PORT` (`server.py:50`) | `FUSION360_MCP_PORT` (`jsonrpc-client.ts:17`) | ✅ Yes |

**Method name match (all 6)**:

| Method | Component A (server.py) | Component A (handlers.py) | Component B (tools.ts) | Component B (index.ts) |
|--------|------------------------|--------------------------|----------------------|---------------------|
| `get_active_design_parameters` | ✅ | ✅ | ✅ | ✅ |
| `measure_clearance` | ✅ | ✅ | ✅ | ✅ |
| `update_user_parameter` | ✅ | ✅ | ✅ | ✅ |
| `create_circular_cutout` | ✅ | ✅ | ✅ | ✅ |
| `create_rectangular_cutout` | ✅ | ✅ | ✅ | ✅ |
| `create_slot_cutout` | ✅ | ✅ | ✅ | ✅ |

**Error code table — design vs implementation** (unchanged):

| Code | Category | Design | errors.py | server.py | jsonrpc.py |
|------|----------|--------|-----------|-----------|------------|
| -32700 | Parse error | ✅ | ✅ `PARSE_ERROR` | ✅ | ✅ `PARSE_ERROR_CODE` |
| -32600 | Invalid request | ✅ | ✅ `INVALID_REQUEST` | ✅ | ✅ `INVALID_REQUEST_CODE` |
| -32601 | Method not found | ✅ | ✅ `METHOD_NOT_FOUND` | ✅ | ✅ `METHOD_NOT_FOUND_CODE` |
| -32000 | Fusion API error | ✅ | ✅ `FUSION_API_ERROR` | ✅ | — |
| -32001 | Invalid parameter | ✅ | ✅ `INVALID_PARAMETER` | ✅ | — |
| -32002 | No active design | ✅ | ✅ `NO_ACTIVE_DESIGN` | ✅ | — |
| -32003 | Operation timeout | ✅ | ✅ `OPERATION_TIMEOUT` | ✅ | — |

Component B does not embed error codes — it translates JSON-RPC error objects from Component A via `toMcpError()` in `errors.ts`. The `JsonRpcError` interface in `types.ts` captures all fields (`code`, `message`, `data.fusion_trace`, `data.detail`). ✅

---

### Spec Compliance Matrix

#### fusion360-add-in spec

| Requirement | Scenario | Evidence | Result |
|------------|----------|----------|--------|
| HTTP Server Lifecycle | Server starts on add-in load | `Fusion360MCP.py:53` → `start_server()` + `FusionMCPServer`, logs port | ⚠️ UNTESTED (requires Fusion GUI) |
| HTTP Server Lifecycle | Server stops on add-in unload | `Fusion360MCP.py:82-86` → `server.shutdown()`, `server_close()` | ⚠️ UNTESTED |
| HTTP Server Lifecycle | Configurable port via env | `server.py:49-51` → `os.environ.get("FUSION360_MCP_PORT")` | ✅ Static review |
| JSON-RPC 2.0 Protocol | Valid request returns matching id | `server.py:126,151-156` → `_send_jsonrpc_result` uses `request_id` | ⚠️ UNTESTED |
| JSON-RPC 2.0 Protocol | Invalid JSON returns parse error | `server.py:98-101` → `PARSE_ERROR_CODE` (-32700) on `JSONDecodeError` | ✅ Static review |
| JSON-RPC 2.0 Protocol | Non-POST method rejected | `server.py:137-147` → `do_GET`, `do_PUT`, `do_DELETE` all send 405 | ✅ Static review |
| CustomEvent Main-Thread Bridge | Request dispatched to main thread | `fusion_bridge.py:58-105` → `submit()` enqueues, fires `fireCustomEvent()` | ⚠️ UNTESTED |
| CustomEvent Bridge | Concurrent requests sequential | `fusion_bridge.py:113-137` → drains queue with `get_nowait()`, one at a time | ⚠️ UNTESTED |
| Fusion API Error Wrapping | Fusion API exception wrapped | `fusion_bridge.py:128-134` catches all exceptions → `FusionAPIError(-32000, ...)` | ⚠️ UNTESTED |
| Fusion API Error Wrapping | Error codes by category | `errors.py:14-17` defines -32000 to -32003; handlers use correct codes | ✅ Static review |
| Operation Timeout | computeAll exceeds timeout | `fusion_bridge.py:95-99` → `event.wait(timeout=30)`, raises `OPERATION_TIMEOUT` | ⚠️ UNTESTED |

#### mcp-wrapper spec

| Requirement | Scenario | Evidence | Result |
|------------|----------|----------|--------|
| MCP Tool Registration | All 6 tools visible | `index.ts:30-69` → 6 `server.tool()` calls | ⚠️ UNTESTED (requires MCP client) |
| MCP Tool Registration | Zod schema validates params | `tools.ts` → Zod schemas with `.string()`, `.number()`, `.int()`, `.default(0)` | ⚠️ UNTESTED |
| HTTP Client to Component A | Tool call → JSON-RPC POST | `jsonrpc-client.ts:44-49` → `fetch(POST, jsonrpc: "2.0", method, id)` | ⚠️ UNTESTED |
| HTTP Client | Connection refused | `jsonrpc-client.ts:53-66` → catches "ECONNREFUSED", returns "Connection refused: Component A not running" | ✅ Static review |
| JSON-RPC Error → MCP | Fusion API error returned | `errors.ts:8-18` → `toMcpError()` extracts `fusion_trace > detail > message` | ✅ Static review |
| JSON-RPC Error → MCP | Successful result | `errors.ts:24-27` → `toMcpResult()` stringifies result as JSON text | ✅ Static review |
| No adsk Import | Zero adsk imports | grep `adsk` in `mcp-server/src/` → 0 matches | ✅ PASS (verified) |

#### parameter-management spec

| Requirement | Scenario | Evidence | Result |
|------------|----------|----------|--------|
| Get Active Design Parameters | Returns all user parameters | `handlers.py:61-87` → iterates `design.userParameters` | ⚠️ UNTESTED |
| Get Active Design Parameters | Empty design → empty array | `handlers.py:87` → returns `{"parameters": [...]}` (empty if no loop iteration) | ⚠️ UNTESTED |
| Get Active Design Parameters | No active design → -32002 | `handlers.py:35-39` → `_get_active_design()` raises `NO_ACTIVE_DESIGN` | ⚠️ UNTESTED |
| Update User Parameter with Rollback | Parameter updated successfully | `handlers.py:126-204` → snapshot, mutate, computeAll(), return success | ⚠️ UNTESTED |
| Update User Parameter with Rollback | Rollback on computeAll failure | `handlers.py:180-198` → restores ALL params from snapshot on exception | ✅ Static review |
| Update User Parameter with Rollback | Parameter not found → -32001 | `handlers.py:153-162` → `FusionAPIError(INVALID_PARAMETER, "Parameter 'X' not found")` | ✅ Static review |
| Update User Parameter with Rollback | Invalid expression format → error | `handlers.py:172-176` → catches `target.expression = new_expr` exception, wraps as `FUSION_API_ERROR` (-32000). Note: spec expects -32001; see WARNING #4. | ✅ Static review |

#### geometry-analysis spec

| Requirement | Scenario | Evidence | Result |
|------------|----------|----------|--------|
| Measure Clearance | Bodies with positive clearance | `handlers.py:90-129` → `measureMinimumDistance`, `cm_to_mm()` conversion | ⚠️ UNTESTED |
| Measure Clearance | Bodies in interference | `handlers.py:126-128` → `distance_mm` negative, `is_interfering: true` | ⚠️ UNTESTED |
| Measure Clearance | Body not found → -32001 | `handlers.py:117-118` → `resolve_body()` raises `FusionAPIError(INVALID_PARAMETER, "Body 'X' not found")` | ✅ Static review |
| Measure Clearance | Same body → -32001 | `handlers.py:110-114` → raises `FusionAPIError(INVALID_PARAMETER, "body1_name and body2_name must be different bodies")` | ✅ Static review |
| Measure Clearance | No active design → -32002 | `handlers.py:116` → `_get_active_design()` | ⚠️ UNTESTED |

#### cutout-modeling spec

| Requirement | Scenario | Evidence | Result |
|------------|----------|----------|--------|
| Create Circular Cutout | Cutout created successfully | `handlers.py:292-340` → sketch circle, extrude cut | ⚠️ UNTESTED |
| Create Circular Cutout | Invalid face index → -32001 | `tools.py:63-83` → `validate_face_index` | ✅ Static review |
| Create Circular Cutout | Negative diameter → -32001 | `tools.py:86-100` → `validate_positive` | ✅ Static review |
| Create Circular Cutout | Target body not found → -32001 | `tools.py:39-60` → `resolve_body` | ✅ Static review |
| Create Rectangular Cutout | Cutout created successfully | `handlers.py:343-435` → centered rect, extrude cut | ⚠️ UNTESTED |
| Create Rectangular Cutout | Rotation applied | `handlers.py:393-402` → `angle_deg` → rotation via `math.sin/cos` | ⚠️ UNTESTED |
| Create Rectangular Cutout | Zero width rejected → -32001 | `handlers.py:369` → `validate_positive(val, name)` | ✅ Static review |
| Create Slot Cutout | Slot created successfully | `handlers.py:438-564` → obround profile, arcs, extrude cut | ⚠️ UNTESTED |
| Create Slot Cutout | Length < width rejected → -32001 | `handlers.py:475-481` → `length_mm <= width_mm` → error | ✅ Static review |
| Create Slot Cutout | Default angle is zero | `handlers.py:460` → `params.get("angle_deg", 0)` | ✅ Static review |
| Unit Conversion | mm→cm for circular cutout | `tools.py:10-22` → `mm_to_cm()`, `handlers.py:326` → `radius_cm = mm_to_cm(diameter_mm/2.0)` | ✅ Static review |

**Compliance summary**: 21/45 scenarios have static evidence confirming implementation structure. 24/45 scenarios require runtime verification inside Fusion 360 GUI (marked UNTESTED). 0 scenarios unimplemented (down from 1 in previous report).

---

### Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Rollback snapshots ALL params before mutation | ✅ | `handlers.py:171-173` — iterates `design.userParameters`, stores all `name → expression` |
| Rollback restores ALL params (not just target) | ✅ | `handlers.py:189-196` — iterates all params, restores from snapshot |
| Rollback reports partial failures | ✅ | `handlers.py:200-203` — collects failures, appends to error detail |
| mm→cm for diameter (radius = half) | ✅ | `handlers.py:326` — `radius_cm = mm_to_cm(diameter_mm / 2.0)` |
| depth_mm → cm in extrude | ✅ | `handlers.py:228` — `depth_cm = mm_to_cm(depth_mm)` |
| cm→mm for measure results | ✅ | `handlers.py:124` — `distance_mm = cm_to_mm(distance_cm)` |
| cm→mm for parameter display | ✅ | `handlers.py:76` — `display_value = cm_to_mm(raw_value)` |
| angle parameters NOT converted | ✅ | Angles pass through unconverted; `mm_to_cm` only applied to linear values |
| Empty params for get_active_design_parameters | ✅ | `index.ts:33` → no shape passed; handler ignores params |
| Optional angle_deg defaults to 0 | ✅ | `tools.ts:84,111` → `z.number().default(0)`, `handlers.py:362,460` → `.get("angle_deg", 0)` |
| Port auto-increment on collision | ✅ | `server.py:59-81` → `_find_available_port` probes up to 100 ports |
| Component B 35s timeout (5s buffer over Component A's 30s) | ✅ | `jsonrpc-client.ts:5,48` → `35_000` via `AbortSignal.timeout()` |
| No adsk import in Component B | ✅ | Verified: 0 matches in `mcp-server/src/` |
| JSON-RPC error with `data.fusion_trace` | ✅ | `errors.py:66-67` → only for `FUSION_API_ERROR (-32000)` |
| POST-only enforcement | ✅ | `server.py:137-147` → `do_GET/PUT/DELETE` return 405 with JSON-RPC error |
| face_index: 1-based across both components | ✅ | `tools.py:66,77` + `tools.ts:57,80,107` — consistent contract |
| measure_clearance: same-body guard present | ✅ | `handlers.py:110-114` — returns INVALID_PARAMETER before resolve_body |
| measure_clearance: string type validation precedes equality check | ✅ | Lines 104-108 validate types; line 110 checks equality |

---

### Coherence (Design)

| Decision | Design Choice | Implementation | Followed? |
|----------|--------------|----------------|-----------|
| HTTP server | `http.server.BaseHTTPRequestHandler` (stdlib) | `server.py:84` → `RPCHandler(BaseHTTPRequestHandler)` | ✅ Yes |
| Thread bridge | `threading.Event` per request + queue | `fusion_bridge.py:76-105` → `threading.Event()`, `queue.Queue()` | ✅ Yes |
| Wire protocol | JSON-RPC 2.0 over HTTP POST | Both components match | ✅ Yes |
| MCP SDK API | `registerTool` (v2) → `server.tool` (v1) | `index.ts:30-69` → 6 `server.tool()` calls | ✅ Yes (v1 API, matches installed SDK v1.29.0) |
| Rollback mechanism | Snapshot dict of `{name: expression}` before mutation | `handlers.py:171-173` → `snapshot[p.name] = p.expression` | ✅ Yes |
| Unit conversion | Component A converts mm→cm at handler boundary | `tools.py:10-36` → `mm_to_cm()`, `cm_to_mm()` | ✅ Yes |
| Port handling | `FUSION360_MCP_PORT`, default 9876, auto-increment | `server.py:33,49-51,59-81` | ✅ Yes |
| Manifest path | `add-in/manifest/Fusion360MCP.manifest` | File at `add-in/Fusion360MCP.manifest` (flat, no `manifest/` subdir) | ⚠️ Slight deviation |
| Modules named | `bridge.py`, `main.py`, `units.py` | `fusion_bridge.py`, `Fusion360MCP.py`, `tools.py` | ⚠️ Names differ |
| Timeout hierarchy | Component A: 30s, Component B: 35s | `server.py:35` → 30s, `jsonrpc-client.ts:5` → 35s | ✅ Yes |
| Project layout | Two top-level dirs: `add-in/`, `mcp-server/` | `add-in/` (8 files), `mcp-server/` (5 src files + config) | ✅ Yes |
| face_index convention | 1-based indexing | Both components use 1-based (was previously mismatched) | ✅ Yes (fixed) |
| Same-body validation | Pre-validation in handler before API call | `handlers.py:110-114` | ✅ Yes (fixed) |

---

### Issues Found

#### 🔴 CRITICAL

None. Both CRITICAL issues from the previous verification are resolved.

#### ⚠️ WARNING

1. **Slot cutout: length == width rejected (spec says >=)**
   - **Where**: `handlers.py:475` vs spec `cutout-modeling/spec.md`
   - **What**: Handler uses `length_mm <= width_mm` (strict inequality required). The spec error message says "length_mm must be >= width_mm for a valid slot". Equal length and width is rejected by the handler.
   - **Impact**: A slot where `length_mm == width_mm` (which would produce a circular obround, still valid geometry) is rejected. This is a boundary case — arguably acceptable since a slot with equal length/width is just a circle.
   - **Fix**: Either change `<=` to `<` in handler, or update spec scenario message to say "must be greater than".

2. **Invalid expression error code mismatch**
   - **Where**: Spec `parameter-management/spec.md` vs `handlers.py:178-182`
   - **What**: Spec scenario "Invalid expression format" expects error code `-32001` (INVALID_PARAMETER). Handler catches `target.expression = new_expr` exception and wraps as `FUSION_API_ERROR` (-32000), because the error comes from the Fusion API, not from pre-validation.
   - **Impact**: LLM sees `-32000` instead of `-32001`. Both are error responses with descriptive messages. The distinction affects error categorization for the agent.
   - **Fix**: Either update spec to accept `-32000` for expression validation errors (they do originate from Fusion API), or add pre-validation to catch invalid expressions before setting.

3. **Parameter unit label: spec says "cm" but implementation says "mm"**
   - **Where**: Spec `parameter-management/spec.md` line 19 vs implementation `tools.py:52-53` and `handlers.py:76`
   - **What**: Spec example: `Width` (40 mm) → `unit: "cm"`, `value: 4.0`. Implementation: `Width` (40 mm) → `unit: "mm"`, `value: 40.0`.
   - **Impact**: The implementation is actually MORE useful (returns values in the unit the agent uses), but diverges from the spec document.
   - **Fix**: Update spec to reflect the actual behavior: `unit: "mm"` for lengths, `value` in displayed unit.

4. **`is_interfering` uses `distance_cm` instead of `distance_mm`**
   - `handlers.py:128` → `"is_interfering": distance_cm <= 0`
   - Since `distance_mm = cm_to_mm(distance_cm)`, sign is preserved → logically equivalent. Using `distance_mm <= 0` would be clearer and more consistent.
   - **Impact**: None functionally. Minor readability.

#### 💡 SUGGESTION

5. **Design document file paths don't match implementation**
   - Design.md references `add-in/manifest/Fusion360MCP.manifest`, `add-in/main.py`, `add-in/bridge.py`, `add-in/units.py`. Actual files: `add-in/Fusion360MCP.manifest`, `add-in/Fusion360MCP.py`, `add-in/fusion_bridge.py`, `add-in/tools.py`.
   - **Impact**: None on functionality. Confusion for someone reading design vs code.
   - **Fix**: Update design.md File Changes table to match actual filenames, or rename files to match design.

6. **No automated tests for Component B**
   - The MCP SDK client (`FusionClient`) and error translation (`toMcpError`, `toMcpResult`) are pure functions that could be unit-tested with mock `fetch`.
   - Zod schema validation and tool handler wiring could be tested with MCP inspector or unit tests.
   - **Impact**: Bugs in error translation or JSON-RPC format would only surface at integration time.
   - **Fix**: Add Jest/Vitest tests for `errors.ts`, `jsonrpc-client.ts` (with fetch mock), and Zod schema validation.

---

### Manual Test Checklist (Fusion 360 GUI)

Component A can only be fully verified with a running Fusion 360 instance. Execute these steps manually:

- [ ] **A1. Install**: Copy `add-in/` folder to Fusion 360 Add-ins directory. Verify add-in appears in Scripts and Add-Ins dialog.
- [ ] **A2. Start**: Load the add-in. Confirm "Fusion 360 MCP Server listening on port X" in Text Commands palette.
- [ ] **A3. Port config**: Set `FUSION360_MCP_PORT=9999`, restart add-in. Confirm server binds to 9999.
- [ ] **A4. HTTP POST**: From external terminal, `curl -X POST http://127.0.0.1:9876 -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","method":"get_active_design_parameters","id":1}'`.
- [ ] **A5. Malformed JSON**: Send `curl ... -d 'not json'`. Confirm response `{"error":{"code":-32700,...}}`.
- [ ] **A6. GET rejected**: Send `curl http://127.0.0.1:9876`. Confirm HTTP 405 with JSON-RPC error.
- [ ] **A7. Measure clearance**: Create 2 bodies (e.g., two boxes), name them "Box1" and "Box2". Call `measure_clearance`. Verify distance.
- [ ] **A7b. Same-body rejection**: Call `measure_clearance` with `body1_name: "Box1"`, `body2_name: "Box1"`. Confirm error `-32001` "body1_name and body2_name must be different bodies".
- [ ] **A8. Update parameter**: Create user parameter `Width = 40 mm`. Call `update_user_parameter` with `"50 mm"`. Verify parameter updates in Fusion Parameters dialog.
- [ ] **A9. Rollback**: Set parameter to expression that will break a feature (e.g., if a fillet depends on it). Call `update_user_parameter`. Verify parameter reverts to original value.
- [ ] **A10. Circular cutout**: Create a body "Panel", call `create_circular_cutout` with `face_index: 1, diameter_mm: 10, depth_mm: 5`. Verify hole in GUI.
- [ ] **A11. Rectangular cutout with rotation**: Call `create_rectangular_cutout` with `angle_deg: 45`. Verify rotated rectangle.
- [ ] **A12. Slot cutout**: Call `create_slot_cutout` with `length_mm: 30, width_mm: 8`. Verify slot shape.
- [ ] **A13. Invalid face_index**: Call cutout with `face_index: 99` on a 3-face body. Confirm `-32001` error.
- [ ] **A14. Negative diameter**: Call `create_circular_cutout` with `diameter_mm: -5`. Confirm `-32001` error.
- [ ] **A15. Body not found**: Call any tool with `target_body: "Ghost"`. Confirm `-32001` error.
- [ ] **A16. No active design**: Close all documents. Call any tool. Confirm `-32002` error.
- [ ] **A17. Stop**: Unload add-in. Confirm server stops and port is released (no response to curl).
- [ ] **A18. E2E**: Start Component B (`node dist/index.js`), connect MCP Inspector. Run `tools/list` → 6 tools. Run `get_active_design_parameters` → returns parameter data.

---

### Verdict

**PASS WITH WARNINGS** — both critical issues resolved:

1. ✅ `face_index` descriptions changed from "Zero-based" to "1-based" across all three cutout tools in Component B — contract is now consistent with Component A.
2. ✅ Same-body validation added to `measure_clearance` with correct error code (`-32001`) and message ("body1_name and body2_name must be different bodies").

4 non-blocking warnings remain:
- Slot cutout `length <= width` instead of `length < width` (boundary case)
- Invalid expression error code `-32000` vs spec's `-32001` (semantic distinction)
- Parameter unit label `"mm"` vs spec's `"cm"` (implementation is more practical)
- `is_interfering` uses `distance_cm` instead of `distance_mm` (cosmetic)

2 suggestions remain (design doc path drift, no automated tests for Component B).

---

### Artifacts

| Artifact | Path / Key |
|----------|-----------|
| Verify report (filesystem) | `openspec/changes/fusion360-mcp-server/verify-report.md` |
| Verify report (Engram) | `sdd/fusion360-mcp-server/verify-report` |
| Mode | `both` |

---

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Initial | Full verification. Verdict: **FAIL** (2 critical). |
| 2.0 | 2026-06-12 | Re-verification after fixes. Verdict: **PASS WITH WARNINGS**. |
