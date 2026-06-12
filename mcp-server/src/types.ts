/** JSON-RPC 2.0 request sent from Component B to Component A. */
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
  id: number | string;
}

/** JSON-RPC 2.0 error object returned by Component A. */
export interface JsonRpcError {
  code: number;
  message: string;
  data?: {
    fusion_trace?: string;
    detail?: string;
  };
}

/** JSON-RPC 2.0 response from Component A. */
export interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: unknown;
  error?: JsonRpcError;
}

/** MCP CallToolResult compatible type for tool responses. */
export interface McpToolResult {
  [x: string]: unknown;
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
}