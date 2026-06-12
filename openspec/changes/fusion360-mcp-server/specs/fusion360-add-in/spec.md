# Fusion 360 Add-in Specification

## Purpose

Component A — Python add-in running inside Fusion 360's embedded interpreter. Provides HTTP JSON-RPC 2.0 server on localhost, bridges requests to the main thread via `adsk.core.CustomEvent`, and wraps all Fusion API errors into structured JSON-RPC responses.

## Requirements

### Requirement: HTTP Server Lifecycle

The system SHALL bind an HTTP server to `127.0.0.1` on a configurable port (default: 9876) when the Fusion 360 add-in loads. The server SHALL run in a secondary thread and accept JSON-RPC 2.0 POST requests. On add-in unload, the server SHALL stop and release the port.

#### Scenario: Server starts on add-in load

- GIVEN Fusion 360 is running with the add-in installed
- WHEN the add-in is loaded
- THEN an HTTP server listens on `127.0.0.1:9876`
- AND the add-in logs the bound port to the Fusion text commands palette

#### Scenario: Server stops on add-in unload

- GIVEN the HTTP server is running
- WHEN the add-in is unloaded
- THEN the server stops accepting connections
- AND the port is released

#### Scenario: Configurable port via environment

- GIVEN the environment variable `FUSION360_MCP_PORT` is set to `9999`
- WHEN the add-in loads
- THEN the server binds to `127.0.0.1:9999`

### Requirement: JSON-RPC 2.0 Protocol

The system SHALL accept only HTTP POST requests with `Content-Type: application/json` containing a valid JSON-RPC 2.0 request body. The system SHALL return a JSON-RPC 2.0 response with matching `id`. Invalid requests SHALL return a JSON-RPC 2.0 error response.

#### Scenario: Valid request returns matching id

- GIVEN a POST request with `{"jsonrpc":"2.0","method":"get_active_design_parameters","params":{},"id":1}`
- WHEN the server processes the request
- THEN the response contains `"id":1`

#### Scenario: Invalid JSON returns parse error

- GIVEN a POST request with malformed JSON body
- WHEN the server receives the request
- THEN the response contains JSON-RPC error code `-32700` (Parse error)

#### Scenario: Non-POST method rejected

- GIVEN a GET request to the server endpoint
- WHEN the server receives the request
- THEN the response is HTTP 405 with a JSON-RPC error

### Requirement: CustomEvent Main-Thread Bridge

The system SHALL queue every incoming JSON-RPC request and dispatch it to Fusion 360's main thread via `adsk.core.CustomEvent`. The handler SHALL execute the requested operation using the `adsk` API and return the result to the HTTP response. Concurrent requests SHALL be queued and processed sequentially.

#### Scenario: Request dispatched to main thread

- GIVEN an HTTP POST with a valid method
- WHEN the server receives the request
- THEN the request is queued and fired via `fireCustomEvent()`
- AND the `adsk` API call executes on the main thread

#### Scenario: Concurrent requests processed sequentially

- GIVEN two HTTP POST requests arrive simultaneously
- WHEN both are queued
- THEN the first completes before the second begins
- AND both return correct responses

### Requirement: Fusion API Error Wrapping

The system SHALL catch all `adsk` exceptions during handler execution and wrap them in a JSON-RPC error response. The error object SHALL include `code`, `message`, and `data.fusion_trace` with the sanitized Fusion API error message.

#### Scenario: Fusion API exception wrapped

- GIVEN a handler calls an `adsk` method that raises an exception
- WHEN the exception is caught
- THEN the response contains `"error":{"code":-32000,"message":"Fusion API error: <detail>","data":{"fusion_trace":"<detail>"}}`

#### Scenario: Error codes by category

- GIVEN an invalid parameter is detected before API call
- THEN the error code is `-32001`
- GIVEN no design document is active
- THEN the error code is `-32002`
- GIVEN an unknown method name is requested
- THEN the error code is `-32601`

### Requirement: Operation Timeout

The system SHALL enforce a per-request timeout of 30 seconds (configurable). If a handler exceeds the timeout, the system SHALL return a JSON-RPC error with code `-32003` and message "Operation timed out".

#### Scenario: computeAll exceeds timeout

- GIVEN a design with complex geometry takes >30s to compute
- WHEN `update_user_parameter` triggers `computeAll()`
- THEN the response contains error code `-32003` with "Operation timed out"
