"""JSON-RPC 2.0 request/response utilities for Fusion 360 MCP Server.

Provides building, parsing, and validation for JSON-RPC 2.0 messages.
Uses only Python stdlib — no third-party dependencies.
"""

import json

# JSON-RPC 2.0 specification constants
JSONRPC_VERSION = "2.0"
PARSE_ERROR_CODE = -32700
PARSE_ERROR_MESSAGE = "Parse error"
METHOD_NOT_FOUND_CODE = -32601
METHOD_NOT_FOUND_MESSAGE = "Method not found"
INVALID_REQUEST_CODE = -32600
INVALID_REQUEST_MESSAGE = "Invalid Request"


def build_request(method, params=None, request_id=1):
    """Build a JSON-RPC 2.0 request dictionary.

    Args:
        method: The method name string.
        params: Optional dict of parameters.
        request_id: Integer or string request ID. Defaults to 1.

    Returns:
        A dict representing a valid JSON-RPC 2.0 request.
    """
    request = {
        "jsonrpc": JSONRPC_VERSION,
        "method": method,
        "id": request_id,
    }
    if params is not None:
        request["params"] = params
    return request


def parse_response(raw_text):
    """Parse a JSON-RPC 2.0 response from raw text.

    Args:
        raw_text: Raw string received from a JSON-RPC endpoint.

    Returns:
        A dict with either 'result' (success) or 'error' (failure),
        plus 'id'. Returns a parse error dict if the input is malformed.
    """
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {
            "jsonrpc": JSONRPC_VERSION,
            "error": {
                "code": PARSE_ERROR_CODE,
                "message": PARSE_ERROR_MESSAGE,
            },
            "id": None,
        }

    if not isinstance(data, dict):
        return {
            "jsonrpc": JSONRPC_VERSION,
            "error": {
                "code": INVALID_REQUEST_CODE,
                "message": INVALID_REQUEST_MESSAGE,
            },
            "id": None,
        }

    return data


def validate_id(request_id):
    """Validate that a JSON-RPC request ID is acceptable.

    JSON-RPC 2.0 requires the id to be a string, number, or null.
    This function ensures the id is not None (which would indicate a
    notification, not a request expecting a response).

    Args:
        request_id: The id field from a JSON-RPC request.

    Returns:
        The validated id.

    Raises:
        ValueError: If the id is None (notification) or an unsupported type.
    """
    if request_id is None:
        raise ValueError("Request id must not be None (notifications not supported)")
    if not isinstance(request_id, (str, int)):
        raise ValueError(
            "Request id must be a string or integer, got {}".format(type(request_id).__name__)
        )
    return request_id