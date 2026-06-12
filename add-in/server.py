"""HTTP JSON-RPC 2.0 server for Fusion 360 MCP Server.

Runs on localhost in a daemon thread. Accepts POST requests only.
Dispatches JSON-RPC methods to the RequestBridge for main-thread execution.
Auto-increments port on collision (finds next available port).
"""

import json
import os
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from jsonrpc import (
    JSONRPC_VERSION,
    PARSE_ERROR_CODE,
    PARSE_ERROR_MESSAGE,
    METHOD_NOT_FOUND_CODE,
    METHOD_NOT_FOUND_MESSAGE,
    INVALID_REQUEST_CODE,
    INVALID_REQUEST_MESSAGE,
)
from errors import (
    FUSION_API_ERROR,
    INVALID_PARAMETER,
    NO_ACTIVE_DESIGN,
    OPERATION_TIMEOUT,
    FusionAPIError,
    fusion_error,
)

# Default port, overridable via environment variable
DEFAULT_PORT = 9876
# Per-request timeout in seconds
REQUEST_TIMEOUT = 30

# Method names — handlers registered by the bridge
METHODS = {
    "get_active_design_parameters",
    "measure_clearance",
    "update_user_parameter",
    "create_circular_cutout",
    "create_rectangular_cutout",
    "create_slot_cutout",
}


def _get_port():
    """Read the port from FUSION360_MCP_PORT env var, or return default."""
    env_port = os.environ.get("FUSION360_MCP_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    return DEFAULT_PORT


def _find_available_port(start_port, max_tries=100):
    """Try to bind starting from start_port, incrementing on collision.

    Args:
        start_port: The preferred port number.
        max_tries: Maximum number of ports to try.

    Returns:
        The first available port number.

    Raises:
        OSError: If no port is available after max_tries.
    """
    for port in range(start_port, start_port + max_tries):
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(("127.0.0.1", port))
            test_sock.close()
            return port
        except OSError:
            continue
    raise OSError("No available port found in range {}-{}".format(start_port, start_port + max_tries - 1))


class RPCHandler(BaseHTTPRequestHandler):
    """HTTP request handler that processes JSON-RPC 2.0 POST requests."""

    # Suppress default logging
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        """Handle POST requests with JSON-RPC 2.0 payloads."""
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="replace")

        # Parse JSON
        try:
            request = json.loads(raw_body)
        except (json.JSONDecodeError, ValueError):
            self._send_jsonrpc_error(PARSE_ERROR_CODE, PARSE_ERROR_MESSAGE, None, 200)
            return

        # Validate request structure
        if not isinstance(request, dict):
            self._send_jsonrpc_error(INVALID_REQUEST_CODE, INVALID_REQUEST_MESSAGE, None, 200)
            return

        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        # Validate method name
        if not isinstance(method, str) or method not in METHODS:
            self._send_jsonrpc_error(
                METHOD_NOT_FOUND_CODE,
                METHOD_NOT_FOUND_MESSAGE,
                request_id,
                200,
            )
            return

        # Dispatch to the bridge (set during server startup)
        bridge = self.server.bridge  # type: ignore[attr-defined]
        try:
            result = bridge.submit(method, params, timeout=REQUEST_TIMEOUT)
            self._send_jsonrpc_result(request_id, result)
        except FusionAPIError as exc:
            self._send_jsonrpc_error(exc.code, str(exc), request_id, 200)
        except Exception as exc:
            self._send_jsonrpc_error(
                FUSION_API_ERROR,
                "Fusion API error: {}".format(str(exc)),
                request_id,
                200,
            )

    def do_GET(self):
        """Reject non-POST methods with 405."""
        self._send_error_response(405, "Method Not Allowed")

    def do_PUT(self):
        """Reject non-POST methods with 405."""
        self._send_error_response(405, "Method Not Allowed")

    def do_DELETE(self):
        """Reject non-POST methods with 405."""
        self._send_error_response(405, "Method Not Allowed")

    def _send_jsonrpc_result(self, request_id, result):
        """Send a successful JSON-RPC 2.0 response."""
        response = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }
        self._send_json_response(200, response)

    def _send_jsonrpc_error(self, code, message, request_id, http_status=200):
        """Send a JSON-RPC 2.0 error response."""
        error_obj = {"code": code, "message": message}

        # Attach data for known Fusion error codes
        if code in (FUSION_API_ERROR, INVALID_PARAMETER, NO_ACTIVE_DESIGN, OPERATION_TIMEOUT):
            error_obj = fusion_error(code, message if code != FUSION_API_ERROR else "")

        response = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": error_obj,
        }
        self._send_json_response(http_status, response)

    def _send_json_response(self, status_code, body):
        """Send a JSON response with the given HTTP status code."""
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_response(self, status_code, message):
        """Send a plain HTTP error response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        error_body = json.dumps({
            "jsonrpc": JSONRPC_VERSION,
            "error": {"code": -32600, "message": message},
            "id": None,
        }).encode("utf-8")
        self.wfile.write(error_body)


class FusionMCPServer(HTTPServer):
    """HTTP server with a reference to the RequestBridge."""

    def __init__(self, bridge, port, **kwargs):
        self.bridge = bridge
        super().__init__(("127.0.0.1", port), RPCHandler, **kwargs)


def start_server(bridge, log_callback=None):
    """Start the HTTP server in a daemon thread.

    Args:
        bridge: A RequestBridge instance for dispatching requests.
        log_callback: Optional callable(msg) for logging to Fusion console.

    Returns:
        A dict with 'server' (FusionMCPServer), 'thread' (Thread),
        'port' (int) bound.
    """
    preferred_port = _get_port()
    port = _find_available_port(preferred_port)

    server = FusionMCPServer(bridge, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if log_callback:
        log_callback("Fusion 360 MCP Server listening on port {}".format(port))

    return {"server": server, "thread": thread, "port": port}