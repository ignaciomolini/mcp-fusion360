# MCP Wrapper Specification

## Purpose

Component B — Node.js/TypeScript stdio MCP server using `@modelcontextprotocol/sdk`. Translates MCP tool calls into HTTP JSON-RPC requests to Component A and returns results to the MCP client. NEVER imports `adsk`.

## Requirements

### Requirement: MCP Tool Registration

The system SHALL register exactly 6 tools with the MCP server: `get_active_design_parameters`, `measure_clearance`, `update_user_parameter`, `create_circular_cutout`, `create_rectangular_cutout`, `create_slot_cutout`. Each tool SHALL have a Zod schema defining required and optional parameters with types and descriptions.

#### Scenario: All 6 tools visible to MCP client

- GIVEN the MCP server starts successfully
- WHEN an MCP client sends `tools/list`
- THEN the response lists all 6 tool names with their schemas

#### Scenario: Zod schema validates tool parameters

- GIVEN `update_user_parameter` is called without `parameter_name`
- WHEN the MCP server validates the input
- THEN the call is rejected with a parameter validation error

### Requirement: HTTP Client to Component A

The system SHALL send each tool invocation as an HTTP POST to `http://127.0.0.1:{port}` with a JSON-RPC 2.0 request body. The port SHALL be read from `FUSION360_MCP_PORT` environment variable (default: 9876). The HTTP client SHALL set a timeout of 35 seconds.

#### Scenario: Tool call translated to JSON-RPC

- GIVEN `get_active_design_parameters` is invoked
- WHEN the MCP server forwards the call
- THEN it sends POST to `http://127.0.0.1:9876` with `{"jsonrpc":"2.0","method":"get_active_design_parameters","params":{},"id":<unique>}`

#### Scenario: Connection refused when Component A not running

- GIVEN Component A is not running
- WHEN a tool is invoked
- THEN the MCP server returns `isError: true` with message "Connection refused: Component A not running"

### Requirement: JSON-RPC Error to MCP Translation

The system SHALL translate JSON-RPC error responses from Component A into MCP `CallToolResult` with `isError: true`. The error message SHALL be placed in `content[0].text` as a human-readable string. Successful responses SHALL return `content[0].text` with the JSON result stringified.

#### Scenario: Fusion API error returned to client

- GIVEN Component A returns `{"error":{"code":-32000,"message":"Body 'Foo' not found"}}`
- WHEN the MCP server processes the response
- THEN it returns `{isError:true, content:[{type:"text", text:"Body 'Foo' not found"}]}`

#### Scenario: Successful result returned to client

- GIVEN Component A returns `{"result":{"parameters":[...]}}`
- WHEN the MCP server processes the response
- THEN it returns `{content:[{type:"text", text:JSON.stringify({parameters:[...]})}]}`

### Requirement: No adsk Import

The system SHALL NOT import, reference, or depend on the `adsk` module in any file. All Fusion API interaction SHALL occur exclusively through HTTP requests to Component A.

#### Scenario: Codebase contains no adsk imports

- GIVEN the `mcp-server/` source tree
- WHEN scanned for `import.*adsk` or `require.*adsk`
- THEN zero matches are found
