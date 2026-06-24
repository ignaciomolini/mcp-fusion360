"""Shared utilities for Fusion 360 MCP Server handlers.

Unit conversion (mm <-> cm) and geometry validation helpers.
These are pure helpers — callers pass Fusion API objects.
"""

import math

import adsk.core

from errors import FusionAPIError, INVALID_PARAMETER

# Cap on per-face enumeration in get_body_info responses.
# Mirrors the spec ("Get Body Info with Face Geometry" requirement).
MAX_FACES_ENUMERATED = 100


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


def _face_normal_at(face, centroid):
    """Compute the unit normal of a face at a given point.

    Wrapped in try/except because BRepFace.evaluator.getNormalAtPoint
    can raise for non-analytic faces (imported B-splines, degenerate
    blends). On failure, logs a single line and returns None so the
    caller (get_body_info enumeration or selector matching) can skip
    that face without aborting.

    Args:
        face: adsk.fusion.BRepFace instance.
        centroid: adsk.core.Point3D (typically the face bounding-box
            center) where the normal is evaluated.

    Returns:
        A list [x, y, z] of floats (unit-length), or None on failure.
    """
    try:
        success, normal_vector = face.evaluator.getNormalAtPoint(centroid)
        if not success or normal_vector is None:
            return None
        # adsk.core.Vector3D exposes x/y/z; normalize to a unit vector.
        nx, ny, nz = normal_vector.x, normal_vector.y, normal_vector.z
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length == 0:
            return None
        return [nx / length, ny / length, nz / length]
    except Exception as exc:
        try:
            adsk.core.Application.get().log(
                "getNormalAtPoint failed for face '{}': {}".format(
                    face.tempId, str(exc)
                )
            )
        except Exception:
            pass
        return None


def _angular_distance_degrees(a, b):
    """Return the angle (in degrees) between two unit 3D vectors.

    Args:
        a: 3-element sequence (x, y, z) — unit-length.
        b: 3-element sequence (x, y, z) — unit-length.

    Returns:
        Float angle in degrees, in [0, 180].
    """
    dot = (
        a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    )
    # Clamp to handle floating-point overshoot.
    if dot > 1.0:
        dot = 1.0
    elif dot < -1.0:
        dot = -1.0
    return math.degrees(math.acos(dot))


def _centroid_distance_mm(a, b):
    """Return the Euclidean distance (in mm) between two 3D points.

    Args:
        a: 3-element sequence (x, y, z) in cm (Fusion's internal unit).
        b: 3-element sequence (x, y, z) in cm.

    Returns:
        Float distance in mm.
    """
    dx = (a[0] - b[0]) * 10.0
    dy = (a[1] - b[1]) * 10.0
    dz = (a[2] - b[2]) * 10.0
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _match_selector(body, selector):
    """Resolve a BRepFace from a body using a geometry-based selector.

    Iterates every face on the body (read-only), computes each face's
    normal at its bounding-box centroid, and filters by:
      - `selector.normal` within `selector.tolerance_degrees` (default 5°)
      - `selector.centroid` within `selector.tolerance_mm` (default 0.5 mm)

    Tiebreaker order: smallest angular distance to the normal; then
    smallest centroid distance; then largest `area_mm2` (when neither
    selector field is provided as a tiebreaker).

    Args:
        body: adsk.fusion.BRepBody.
        selector: dict with optional `normal`, `centroid`,
            `tolerance_degrees`, `tolerance_mm`.

    Returns:
        adsk.fusion.BRepFace — the best match.

    Raises:
        FusionAPIError(INVALID_PARAMETER): If no face matches.
    """
    tol_deg = selector.get("tolerance_degrees")
    if tol_deg is None:
        tol_deg = 5
    tol_mm = selector.get("tolerance_mm")
    if tol_mm is None:
        tol_mm = 0.5

    want_normal = selector.get("normal")
    want_centroid = selector.get("centroid")

    candidates = []  # (face, normal_unit, centroid_xyz, area_mm2, ang_deg, cent_mm)

    for i in range(body.faces.count):
        face = body.faces.item(i)

        # Centroid from bounding box (always computable).
        bbox = face.boundingBox
        cx = (bbox.minPoint.x + bbox.maxPoint.x) / 2.0
        cy = (bbox.minPoint.y + bbox.maxPoint.y) / 2.0
        cz = (bbox.minPoint.z + bbox.maxPoint.z) / 2.0
        centroid_pt = (cx, cy, cz)

        # Normal (may be None for non-analytic faces).
        normal_unit = _face_normal_at(face, adsk.core.Point3D.create(cx, cy, cz))
        if normal_unit is None and want_normal is not None:
            # Skip faces without a normal when the selector needs one.
            continue

        # Angular filter.
        ang_deg = None
        if want_normal is not None and normal_unit is not None:
            ang_deg = _angular_distance_degrees(
                [want_normal["x"], want_normal["y"], want_normal["z"]],
                normal_unit,
            )
            if ang_deg > tol_deg:
                continue

        # Centroid filter.
        cent_mm = None
        if want_centroid is not None:
            cent_mm = _centroid_distance_mm(
                [want_centroid["x"], want_centroid["y"], want_centroid["z"]],
                [cx, cy, cz],
            )
            if cent_mm > tol_mm:
                continue

        # Area in mm^2 (Fusion returns cm^2).
        try:
            area_mm2 = float(face.area) * 100.0
        except Exception:
            area_mm2 = 0.0

        candidates.append((face, normal_unit, centroid_pt, area_mm2, ang_deg, cent_mm))

    if not candidates:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "no face matched selector",
        )

    # Sort: by ang_deg (None last), then by cent_mm (None last), then by area desc.
    def sort_key(c):
        _face, _n, _c, area, ang, cent = c
        return (
            0 if ang is not None else 1,
            ang if ang is not None else 0.0,
            0 if cent is not None else 1,
            cent if cent is not None else 0.0,
            -area,
        )

    candidates.sort(key=sort_key)
    return candidates[0][0]


def resolve_face(body, face_index=None, face_selector=None):
    """Resolve a single BRepFace from a body using either an index or a selector.

    Implements the "Face Resolution Order" contract:
      1. `face_index` (when provided) wins over `face_selector`
         (deprecation-period precedence).
      2. `face_selector` only — match by normal within tolerance;
         tiebreak by centroid distance; fall back to largest area.
      3. `face_index` only — validate range and return body.faces.item(idx-1).
      4. Neither — error.
      5. Selector yields no face — error.

    Args:
        body: adsk.fusion.BRepBody.
        face_index: 1-based int (optional).
        face_selector: dict (optional) with `normal` and/or `centroid`.

    Returns:
        adsk.fusion.BRepFace.

    Raises:
        FusionAPIError(INVALID_PARAMETER): missing both, empty selector,
            or no face matched.
    """
    if face_index is not None:
        validate_face_index(body, face_index)
        return body.faces.item(face_index - 1)

    if not face_selector:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "face_index or face_selector is required",
        )

    if not (
        face_selector.get("normal") or face_selector.get("centroid")
    ):
        raise FusionAPIError(
            INVALID_PARAMETER,
            "face_selector is empty",
        )

    return _match_selector(body, face_selector)
