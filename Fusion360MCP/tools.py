"""Shared utilities for Fusion 360 MCP Server handlers.

Unit conversion (mm <-> cm) and geometry validation helpers.
These are pure helpers — callers pass Fusion API objects.
"""

from errors import FusionAPIError, INVALID_PARAMETER


def mm_to_cm(mm):
    """Convert millimeters to centimeters.

    Fusion 360 uses cm internally for all linear measurements.
    All MCP tool parameters are in mm for user/agent convenience.

    Args:
        mm: Value in millimeters.

    Returns:
        Value in centimeters.
    """
    return mm / 10.0


def cm_to_mm(cm):
    """Convert centimeters to millimeters.

    Fusion 360 API returns values in cm; MCP tools return mm.

    Args:
        cm: Value in centimeters.

    Returns:
        Value in millimeters.
    """
    return cm * 10.0


def resolve_body(design, name):
    """Find a BRepBody by name in the active design.

    Args:
        design: adsk.fusion.Design instance.
        name: Body name to search for.

    Returns:
        adsk.fusion.BRepBody instance.

    Raises:
        FusionAPIError(INVALID_PARAMETER): If the body is not found.
    """
    root = design.rootComponent
    for body in root.bRepBodies:
        if body.name == name:
            return body

    raise FusionAPIError(
        INVALID_PARAMETER,
        "Body '{}' not found in the active design".format(name),
    )


def validate_face_index(body, index):
    """Validate that face_index refers to an existing face.

    Face indices are 1-based (matching user expectations).
    Negative indices are not supported (face order is arbitrary in Fusion).

    Args:
        body: adsk.fusion.BRepBody instance.
        index: 1-based face index to validate.

    Raises:
        FusionAPIError(INVALID_PARAMETER): If the index is out of range.
    """
    face_count = body.faces.count
    if not isinstance(index, int) or index < 1 or index > face_count:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "Invalid face_index {} for body '{}' (valid range: 1-{})".format(
                index, body.name, face_count
            ),
        )


def validate_positive(value, name):
    """Validate that a numeric value is strictly positive.

    Args:
        value: The value to check.
        name: Parameter name for the error message.

    Raises:
        FusionAPIError(INVALID_PARAMETER): If value <= 0.
    """
    if not isinstance(value, (int, float)) or value <= 0:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "{} must be a positive number, got '{}'".format(name, value),
        )
