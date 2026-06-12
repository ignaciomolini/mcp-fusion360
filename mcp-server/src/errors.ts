import type { JsonRpcError, McpToolResult } from "./types.js";

/**
 * Translate a JSON-RPC error from Component A into an MCP CallToolResult
 * with isError: true. The error message is extracted from the most specific
 * field available: data.fusion_trace > data.detail > message.
 */
export function toMcpError(error: JsonRpcError): McpToolResult {
  const text =
    error.data?.fusion_trace ??
    error.data?.detail ??
    error.message;

  return {
    isError: true,
    content: [{ type: "text", text }],
  };
}

/**
 * Create a successful MCP CallToolResult from an arbitrary result value.
 * The result is stringified as JSON text content.
 */
export function toMcpResult(result: unknown): McpToolResult {
  return {
    content: [{ type: "text", text: JSON.stringify(result) }],
  };
}