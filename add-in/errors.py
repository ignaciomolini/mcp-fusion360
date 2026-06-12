"""Fusion 360 MCP Server error definitions.

JSON-RPC 2.0 error codes for Fusion API interactions.
Standard codes: -32700 (parse), -32600 (invalid request), -32601 (method not found).
Custom codes: -32000 to -32003 for Fusion-specific errors.
"""

# JSON-RPC 2.0 standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601

# Fusion API custom error codes (application-defined)
FUSION_API_ERROR = -32000      # Runtime error from the adsk API
INVALID_PARAMETER = -32001     # Pre-validation: bad param value, missing param, out of range
NO_ACTIVE_DESIGN = -32002     # No open document / active design
OPERATION_TIMEOUT = -32003    # Handler exceeded the per-request timeout

# Human-readable messages for each custom code
_ERROR_MESSAGES = {
    FUSION_API_ERROR: "Fusion API error",
    INVALID_PARAMETER: "Invalid parameter",
    NO_ACTIVE_DESIGN: "No active design",
    OPERATION_TIMEOUT: "Operation timed out",
}


class FusionAPIError(Exception):
    """Exception wrapping a Fusion API error with a JSON-RPC error code.

    Attributes:
        code: JSON-RPC error code (one of -32000 to -32003).
        detail: Additional context or the original Fusion error message.
    """

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        message = _ERROR_MESSAGES.get(code, "Unknown error")
        if detail:
            message = "{}: {}".format(message, detail)
        super(FusionAPIError, self).__init__(message)


def fusion_error(code, detail=""):
    """Build a JSON-RPC 2.0 error object for a Fusion-specific error.

    Args:
        code: One of the custom error codes (-32000 to -32003).
        detail: Optional detail string appended to the standard message.

    Returns:
        A dict suitable for embedding in a JSON-RPC error response,
        e.g. {"code": -32001, "message": "Invalid parameter: ...", "data": {...}}
    """
    message = _ERROR_MESSAGES.get(code, "Unknown error")
    if detail:
        message = "{}: {}".format(message, detail)

    error_obj = {
        "code": code,
        "message": message,
    }

    # Include trace data for API errors
    if code == FUSION_API_ERROR and detail:
        error_obj["data"] = {"fusion_trace": detail}
    elif detail:
        error_obj["data"] = {"detail": detail}

    return error_obj