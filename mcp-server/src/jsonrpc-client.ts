import type { JsonRpcRequest, JsonRpcResponse, McpToolResult } from "./types.js";
import { toMcpError, toMcpResult } from "./errors.js";

const DEFAULT_PORT = 9876;
const REQUEST_TIMEOUT_MS = 35_000;

/**
 * HTTP JSON-RPC 2.0 client that communicates with Component A (Python add-in).
 * Sends POST requests to http://127.0.0.1:{port} and translates responses
 * into MCP CallToolResult objects.
 */
export class FusionClient {
  private readonly baseUrl: string;

  constructor(port?: number) {
    const resolvedPort =
      port ?? (Number(process.env.FUSION360_MCP_PORT) || DEFAULT_PORT);
    this.baseUrl = `http://127.0.0.1:${resolvedPort}`;
  }

  /**
   * Send a JSON-RPC 2.0 request to Component A and return an MCP tool result.
   *
   * @param method - The JSON-RPC method name (e.g. "get_active_design_parameters")
   * @param params - Optional parameters dict for the method call
   * @returns McpToolResult — isError:true on connection/refusal/JSON-RPC error
   */
  async call(
    method: string,
    params?: Record<string, unknown>,
  ): Promise<McpToolResult> {
    const requestId = Date.now();
    const request: JsonRpcRequest = {
      jsonrpc: "2.0",
      method,
      id: requestId,
    };
    if (params !== undefined) {
      request.params = params;
    }

    let response: Response;
    try {
      response = await fetch(this.baseUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : String(err);
      if (
        message.includes("ECONNREFUSED") ||
        message.includes("Connection refused")
      ) {
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: "Connection refused: Component A not running",
            },
          ],
        };
      }
      return {
        isError: true,
        content: [
          { type: "text", text: `Request failed: ${message}` },
        ],
      };
    }

    if (!response.ok) {
      return {
        isError: true,
        content: [
          {
            type: "text",
            text: `HTTP error ${response.status}: ${response.statusText}`,
          },
        ],
      };
    }

    const body = (await response.json()) as JsonRpcResponse;

    if (body.error) {
      return toMcpError(body.error);
    }

    return toMcpResult(body.result);
  }
}