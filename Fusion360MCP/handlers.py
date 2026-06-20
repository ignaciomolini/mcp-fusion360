"""Request handlers for the Fusion 360 MCP Server.

Each handler receives a params dict and returns a result dict.
Handlers run on Fusion's main thread (dispatched by RequestBridge),
so they can use the adsk API directly.
"""

from datetime import datetime, timezone

import adsk.core
import adsk.fusion

from errors import (
    FUSION_API_ERROR,
    INVALID_PARAMETER,
    NO_ACTIVE_DESIGN,
    FusionAPIError,
)
from tools import (
    mm_to_cm,
    cm_to_mm,
    resolve_body,
    validate_face_index,
    validate_positive,
)


def _get_active_design():
    """Get the currently active Fusion 360 design.

    Returns:
        adsk.fusion.Design instance.

    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN): If no design is open.
    """
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise FusionAPIError(NO_ACTIVE_DESIGN, "No active design open")
    return design


def _get_unit_label(param):
    """Extract the unit label from a Fusion parameter for display.

    Args:
        param: adsk.fusion.UserParameter instance.

    Returns:
        Unit string: 'mm', 'cm', 'deg', 'rad', or ''.
    """
    unit = param.unit
    if unit == "mm" or unit == "cm":
        return "mm"
    elif unit == "deg":
        return "deg"
    elif unit == "rad":
        return "rad"
    return unit


def handle_get_active_design_parameters(params):
    """Return all User Parameters from the active design.

    Each entry is augmented with the additive fields ``comment`` and
    ``is_favorite``. ``comment`` is the parameter's optional free-form
    description (``None`` when not set) and ``is_favorite`` reflects the
    user-marked favorite flag in the Parameters dialog.

    Returns:
        dict with 'parameters' key containing a list of parameter objects,
        each with: name, expression, value (converted to mm or deg), unit,
        comment (str or None), is_favorite (bool).
    """
    design = _get_active_design()
    parameters = []

    for param in design.userParameters:
        unit = _get_unit_label(param)
        raw_value = param.value
        # Fusion returns cm for lengths; convert to mm
        if unit == "mm":
            display_value = cm_to_mm(raw_value)
        else:
            display_value = raw_value

        parameters.append({
            "name": param.name,
            "expression": param.expression,
            "value": display_value,
            "unit": unit,
            "comment": _safe_param_comment(param),
            "is_favorite": bool(param.isFavorite),
        })

    return {"parameters": parameters}


def _safe_param_comment(param):
    """Return the parameter's comment, or None if the API raises.

    Some Fusion 360 builds raise on ``param.comment`` access for
    parameters that have never been edited. Treat any failure as
    "no comment set" so the read path stays non-fatal.
    """
    try:
        comment = param.comment
    except Exception:
        return None
    if comment is None:
        return None
    stripped = str(comment).strip()
    return stripped or None


def handle_measure_clearance(params):
    """Measure the minimum distance between two solid bodies.

    Args:
        body1_name (str): Name of the first body.
        body2_name (str): Name of the second body.

    Returns:
        dict with distance_mm (float, negative = interference) and
        is_interfering (bool).
    """
    body1_name = params.get("body1_name")
    body2_name = params.get("body2_name")

    if not isinstance(body1_name, str) or not isinstance(body2_name, str):
        raise FusionAPIError(
            INVALID_PARAMETER,
            "body1_name and body2_name are required string parameters",
        )

    if body1_name == body2_name:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "body1_name and body2_name must be different bodies",
        )

    design = _get_active_design()
    body1 = resolve_body(design, body1_name)
    body2 = resolve_body(design, body2_name)

    app = adsk.core.Application.get()
    results = app.measureManager.measureMinimumDistance(body1, body2)

    distance_cm = results.value
    distance_mm = cm_to_mm(distance_cm)

    return {
        "distance_mm": distance_mm,
        "is_interfering": distance_cm <= 0,
    }


def handle_update_user_parameter(params):
    """Modify a User Parameter and recompute the design.

    Takes a snapshot of ALL user parameters before mutation.
    On computeAll() failure, restores ALL parameters to their
    original values and returns the Fusion error message.

    Args:
        parameter_name (str): Name of the parameter to modify.
        new_expression (str): New expression value (e.g. '50 mm').

    Returns:
        dict with parameter_name, new_expression, and recomputed=True.
    """
    param_name = params.get("parameter_name")
    new_expr = params.get("new_expression")

    if not isinstance(param_name, str) or not isinstance(new_expr, str):
        raise FusionAPIError(
            INVALID_PARAMETER,
            "parameter_name and new_expression are required string parameters",
        )

    design = _get_active_design()

    # Find the target parameter
    target = None
    for p in design.userParameters:
        if p.name == param_name:
            target = p
            break

    if target is None:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "Parameter '{}' not found".format(param_name),
        )

    # Snapshot ALL user parameters BEFORE mutation
    snapshot = {}
    for p in design.userParameters:
        snapshot[p.name] = p.expression

    # Mutate the target parameter
    try:
        target.expression = new_expr
    except Exception as exc:
        raise FusionAPIError(
            FUSION_API_ERROR,
            "Failed to set parameter '{}': {}".format(param_name, str(exc)),
        )

    # Force recompute
    try:
        design.computeAll()
    except Exception as exc:
        # Rollback: restore ALL parameters from snapshot
        rollback_failures = []
        for p in design.userParameters:
            if p.name in snapshot:
                try:
                    p.expression = snapshot[p.name]
                except Exception as rb_exc:
                    rollback_failures.append(
                        "{}: {}".format(p.name, str(rb_exc))
                    )

        detail = "Compute failed: {}".format(str(exc))
        if rollback_failures:
            detail += " | Partial rollback failures: {}".format(
                "; ".join(rollback_failures)
            )
        raise FusionAPIError(FUSION_API_ERROR, detail)

    return {
        "parameter_name": param_name,
        "new_expression": new_expr,
        "recomputed": True,
    }


def _sketch_and_cut(design, body, face, profile_builder, depth_mm, cutout_type, extra_info=None):
    """Shared logic for creating a sketch on a face and extruding a cut.

    Args:
        design: adsk.fusion.Design instance.
        body: adsk.fusion.BRepBody (target body, used for logging).
        face: adsk.fusion.BRepFace to sketch on.
        profile_builder: Callable(sketch) that draws geometry; returns a profile.
        depth_mm: Cut depth in millimeters.
        cutout_type: String label (circular, rectangular, slot).
        extra_info: Optional dict with additional dimensions to include in result.

    Returns:
        dict with cutout details.
    """
    depth_cm = mm_to_cm(depth_mm)

    # Create sketch on the target face
    root = design.rootComponent
    sketch = root.sketches.add(face)

    # Draw geometry and get the profile
    profile = profile_builder(sketch)

    if profile is None:
        raise FusionAPIError(
            FUSION_API_ERROR,
            "Failed to create a closed profile for {} cutout".format(cutout_type),
        )

    # Extrude cut
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(
        profile,
        adsk.fusion.FeatureOperations.CutFeatureOperation,
    )
    distance = adsk.core.ValueInput.createByReal(depth_cm)
    extrude_input.setDistanceExtent(
        False,
        distance,
    )

    try:
        extrudes.add(extrude_input)
    except Exception as exc:
        raise FusionAPIError(
            FUSION_API_ERROR,
            "Failed to create {} cutout: {}".format(cutout_type, str(exc)),
        )

    result = {
        "cutout_type": cutout_type,
        "target_body": body.name,
        "depth_mm": depth_mm,
    }
    if extra_info:
        result.update(extra_info)

    return result


def _get_face_centroid(face):
    """Get the centroid (center point) of a face.

    Uses the face's bounding box center as an approximation.

    Args:
        face: adsk.fusion.BRepFace instance.

    Returns:
        adsk.core.Point3D at the face centroid.
    """
    bbox = face.boundingBox
    center_x = (bbox.minPoint.x + bbox.maxPoint.x) / 2.0
    center_y = (bbox.minPoint.y + bbox.maxPoint.y) / 2.0
    center_z = (bbox.minPoint.z + bbox.maxPoint.z) / 2.0
    return adsk.core.Point3D.create(center_x, center_y, center_z)


def handle_create_circular_cutout(params):
    """Create a circular cutout on a face of a body.

    Args:
        target_body (str): Name of the body to cut.
        face_index (int): 1-based index of the face to sketch on.
        diameter_mm (float): Diameter of the hole in mm.
        depth_mm (float): Cut depth in mm.

    Returns:
        dict with cutout details.
    """
    target_name = params.get("target_body")
    face_idx = params.get("face_index")
    diameter_mm = params.get("diameter_mm")
    depth_mm = params.get("depth_mm")

    if not isinstance(target_name, str):
        raise FusionAPIError(INVALID_PARAMETER, "target_body must be a string")
    if not isinstance(face_idx, int):
        raise FusionAPIError(INVALID_PARAMETER, "face_index must be an integer")
    if not isinstance(diameter_mm, (int, float)):
        raise FusionAPIError(INVALID_PARAMETER, "diameter_mm must be a number")
    if not isinstance(depth_mm, (int, float)):
        raise FusionAPIError(INVALID_PARAMETER, "depth_mm must be a number")

    validate_positive(diameter_mm, "diameter_mm")
    validate_positive(depth_mm, "depth_mm")

    design = _get_active_design()
    body = resolve_body(design, target_name)
    validate_face_index(body, face_idx)

    face = body.faces.item(face_idx - 1)
    radius_cm = mm_to_cm(diameter_mm / 2.0)

    def draw_circle(sketch):
        center = _get_face_centroid(face)
        sketch.sketchCurves.sketchCircles.addByCenterRadius(center, radius_cm)
        return sketch.profiles.item(0)

    return _sketch_and_cut(
        design, body, face, draw_circle, depth_mm,
        "circular",
        extra_info={
            "face_index": face_idx,
            "diameter_mm": diameter_mm,
        },
    )


def handle_create_rectangular_cutout(params):
    """Create a rectangular cutout on a face of a body.

    Args:
        target_body (str): Name of the body to cut.
        face_index (int): 1-based index of the face to sketch on.
        width_mm (float): Rectangle width in mm.
        height_mm (float): Rectangle height in mm.
        depth_mm (float): Cut depth in mm.
        angle_deg (float, optional): Rotation around face normal in degrees. Default 0.

    Returns:
        dict with cutout details.
    """
    target_name = params.get("target_body")
    face_idx = params.get("face_index")
    width_mm = params.get("width_mm")
    height_mm = params.get("height_mm")
    depth_mm = params.get("depth_mm")
    angle_deg = params.get("angle_deg", 0)

    if not isinstance(target_name, str):
        raise FusionAPIError(INVALID_PARAMETER, "target_body must be a string")
    if not isinstance(face_idx, int):
        raise FusionAPIError(INVALID_PARAMETER, "face_index must be an integer")

    for name, val in [("width_mm", width_mm), ("height_mm", height_mm), ("depth_mm", depth_mm)]:
        if not isinstance(val, (int, float)):
            raise FusionAPIError(INVALID_PARAMETER, "{} must be a number".format(name))
        validate_positive(val, name)

    if not isinstance(angle_deg, (int, float)):
        raise FusionAPIError(INVALID_PARAMETER, "angle_deg must be a number")

    design = _get_active_design()
    body = resolve_body(design, target_name)
    validate_face_index(body, face_idx)

    face = body.faces.item(face_idx - 1)
    half_w_cm = mm_to_cm(width_mm / 2.0)
    half_h_cm = mm_to_cm(height_mm / 2.0)

    def draw_rect(sketch):
        import math
        center = _get_face_centroid(face)
        lines = sketch.sketchCurves.sketchLines

        # Unrotated corners relative to center
        corners = [
            (-half_w_cm, -half_h_cm),
            (half_w_cm, -half_h_cm),
            (half_w_cm, half_h_cm),
            (-half_w_cm, half_h_cm),
        ]

        # Apply rotation if needed
        if angle_deg != 0:
            angle_rad = math.radians(angle_deg)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            rotated = []
            for dx, dy in corners:
                rx = dx * cos_a - dy * sin_a
                ry = dx * sin_a + dy * cos_a
                rotated.append((rx, ry))
            corners = rotated

        # Create points in 3D (using face normal approximation via Z offset)
        points = []
        for dx, dy in corners:
            pt = adsk.core.Point3D.create(
                center.x + dx,
                center.y + dy,
                center.z,
            )
            points.append(pt)

        # Draw 4 lines forming a closed rectangle
        for i in range(4):
            lines.addByTwoPoints(points[i], points[(i + 1) % 4])

        return sketch.profiles.item(0)

    return _sketch_and_cut(
        design, body, face, draw_rect, depth_mm,
        "rectangular",
        extra_info={
            "face_index": face_idx,
            "width_mm": width_mm,
            "height_mm": height_mm,
            "angle_deg": angle_deg,
        },
    )


def handle_create_slot_cutout(params):
    """Create a slot (obround) cutout on a face of a body.

    A slot is an obround shape: two parallel lines connected by
    semicircular arcs at both ends.

    Args:
        target_body (str): Name of the body to cut.
        face_index (int): 1-based index of the face to sketch on.
        length_mm (float): Total length of the slot in mm.
        width_mm (float): Width of the slot in mm.
        depth_mm (float): Cut depth in mm.
        angle_deg (float, optional): Rotation around face normal in degrees. Default 0.

    Returns:
        dict with cutout details.
    """
    target_name = params.get("target_body")
    face_idx = params.get("face_index")
    length_mm = params.get("length_mm")
    width_mm = params.get("width_mm")
    depth_mm = params.get("depth_mm")
    angle_deg = params.get("angle_deg", 0)

    if not isinstance(target_name, str):
        raise FusionAPIError(INVALID_PARAMETER, "target_body must be a string")
    if not isinstance(face_idx, int):
        raise FusionAPIError(INVALID_PARAMETER, "face_index must be an integer")

    for name, val in [("length_mm", length_mm), ("width_mm", width_mm), ("depth_mm", depth_mm)]:
        if not isinstance(val, (int, float)):
            raise FusionAPIError(INVALID_PARAMETER, "{} must be a number".format(name))
        validate_positive(val, name)

    if not isinstance(angle_deg, (int, float)):
        raise FusionAPIError(INVALID_PARAMETER, "angle_deg must be a number")

    if length_mm <= width_mm:
        raise FusionAPIError(
            INVALID_PARAMETER,
            "length_mm ({}) must be greater than width_mm ({})".format(
                length_mm, width_mm
            ),
        )

    design = _get_active_design()
    body = resolve_body(design, target_name)
    validate_face_index(body, face_idx)

    face = body.faces.item(face_idx - 1)

    half_len_cm = mm_to_cm(length_mm / 2.0)
    half_w_cm = mm_to_cm(width_mm / 2.0)

    def draw_slot(sketch):
        import math
        center = _get_face_centroid(face)

        # The slot is oriented along the X axis (horizontal) before rotation.
        # It consists of:
        #   - Two parallel horizontal lines (top and bottom)
        #   - Two semicircular arcs at left and right ends

        # Key points (unrotated, relative to center):
        #   p1: top-left     p2: top-right
        #   p3: bottom-right p4: bottom-left
        p1 = (-(half_len_cm - half_w_cm), half_w_cm)
        p2 = (half_len_cm - half_w_cm, half_w_cm)
        p3 = (half_len_cm - half_w_cm, -half_w_cm)
        p4 = (-(half_len_cm - half_w_cm), -half_w_cm)

        # Arc center points (left and right ends)
        arc_left_center = (-(half_len_cm - half_w_cm), 0)
        arc_right_center = (half_len_cm - half_w_cm, 0)

        # Apply rotation if needed
        if angle_deg != 0:
            angle_rad = math.radians(angle_deg)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            def rotate(pt):
                x, y = pt
                return (x * cos_a - y * sin_a, x * sin_a + y * cos_a)

            p1 = rotate(p1)
            p2 = rotate(p2)
            p3 = rotate(p3)
            p4 = rotate(p4)
            arc_left_center = rotate(arc_left_center)
            arc_right_center = rotate(arc_right_center)

        def to_3d(dx, dy):
            return adsk.core.Point3D.create(center.x + dx, center.y + dy, center.z)

        pt1 = to_3d(*p1)
        pt2 = to_3d(*p2)
        pt3 = to_3d(*p3)
        pt4 = to_3d(*p4)

        # Draw the two straight lines
        lines = sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(pt1, pt2)  # top
        lines.addByTwoPoints(pt3, pt4)  # bottom

        # Draw the two semicircular arcs
        arcs = sketch.sketchCurves.sketchArcs
        arc_left_center_3d = to_3d(*arc_left_center)
        arc_right_center_3d = to_3d(*arc_right_center)

        # Left arc: from bottom-left to top-left, counterclockwise
        arcs.addByCenterStartSweep(arc_left_center_3d, pt4, math.pi)
        # Right arc: from top-right to bottom-right, counterclockwise
        arcs.addByCenterStartSweep(arc_right_center_3d, pt2, math.pi)

        return sketch.profiles.item(0)

    return _sketch_and_cut(
        design, body, face, draw_slot, depth_mm,
        "slot",
        extra_info={
            "face_index": face_idx,
            "length_mm": length_mm,
            "width_mm": width_mm,
            "angle_deg": angle_deg,
        },
    )


def handle_list_bodies(params):
    """Return every solid/surface body in the root component.

    Each entry exposes the body's display ``name`` and a 1-based
    ``index`` that matches the ``face_index`` convention used by the
    cutout tools. Iteration is read-only — no ``computeAll()`` and no
    mutation. The order follows the BRepBodies collection (positional,
    not a stable identifier).

    Returns:
        dict with 'bodies' key: a list of {'name', 'index'} objects.

    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN): if no design is open.
    """
    design = _get_active_design()
    bodies = []
    root = design.rootComponent
    b_rep_bodies = root.bRepBodies

    for i in range(b_rep_bodies.count):
        body = b_rep_bodies.item(i)
        bodies.append({
            "name": body.name,
            "index": i + 1,
        })

    return {"bodies": bodies}


def handle_get_document_info(params):
    """Return metadata about the active document.

    Fields:
      - name: document display name
      - units: normalized length unit ("mm" or "cm"); other units
        (e.g. "in", "ft") are passed through verbatim
      - design_type: "ParametricDesign" or "DirectDesign"
      - material_library: name of the first loaded material library,
        or "" if none are loaded

    The lookup is read-only and does not trigger ``computeAll()``.

    Returns:
        dict with name, units, design_type, material_library.

    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN): if no document is open.
    """
    app = adsk.core.Application.get()
    doc = app.activeDocument
    if doc is None:
        raise FusionAPIError(NO_ACTIVE_DESIGN, "No active document open")

    design = adsk.fusion.Design.cast(app.activeProduct)
    if design is None:
        raise FusionAPIError(NO_ACTIVE_DESIGN, "No active design open")

    units = _normalize_length_units(str(doc.unitsManager.defaultLengthUnits))

    design_type = _normalize_design_type(design.designType)

    material_library = ""
    try:
        libs = app.materialLibraries
        if libs.count > 0:
            material_library = libs.item(0).name or ""
    except Exception:
        material_library = ""

    return {
        "name": doc.name,
        "units": units,
        "design_type": design_type,
        "material_library": material_library,
    }


def _normalize_length_units(raw_unit):
    """Map Fusion 360 length-unit strings to the documented enum.

    The spec enumerates "mm" and "cm" as the expected values. Other
    length units (in, ft, m, …) are passed through unchanged so the
    call never silently lies about the actual document units.
    """
    if raw_unit == "mm" or raw_unit == "cm":
        return raw_unit
    return raw_unit


def _normalize_design_type(design_type):
    """Map ``Design.designType`` to the documented string form.

    The Fusion 360 ``DesignTypes`` enum exposes only
    ``ParametricDesignType`` and ``DirectDesignType``. We map both to
    stable strings; the spec's "PlasticDesign" was a forward-looking
    value that does not exist in the current API.
    """
    try:
        if design_type == adsk.fusion.DesignTypes.ParametricDesignType:
            return "ParametricDesign"
        if design_type == adsk.fusion.DesignTypes.DirectDesignType:
            return "DirectDesign"
    except Exception:
        pass
    return str(design_type)


def handle_get_body_info(params):
    """Return physical properties of a named body.

    Args:
        body_name (str): exact name of the body to inspect.

    Returns:
        dict with face_count (int), bounding_box (mm, with min/max
        x/y/z), volume_cm3 (float), material (str or None), and
        body_type ("SolidBody" or "SurfaceBody").

    Raises:
        FusionAPIError(INVALID_PARAMETER): empty or missing body_name,
            or no body with that name exists.
        FusionAPIError(NO_ACTIVE_DESIGN): no design is open.
    """
    body_name = params.get("body_name")
    if not isinstance(body_name, str) or body_name.strip() == "":
        raise FusionAPIError(
            INVALID_PARAMETER,
            "body_name is required and must be a non-empty string",
        )

    design = _get_active_design()
    body = resolve_body(design, body_name)

    bbox = body.boundingBox
    bounding_box = {
        "min": {
            "x": cm_to_mm(bbox.minPoint.x),
            "y": cm_to_mm(bbox.minPoint.y),
            "z": cm_to_mm(bbox.minPoint.z),
        },
        "max": {
            "x": cm_to_mm(bbox.maxPoint.x),
            "y": cm_to_mm(bbox.maxPoint.y),
            "z": cm_to_mm(bbox.maxPoint.z),
        },
    }

    material = None
    if body.material is not None:
        try:
            material = body.material.name
        except Exception:
            material = None

    body_type = "SolidBody" if bool(body.isSolid) else "SurfaceBody"

    return {
        "face_count": int(body.faces.count),
        "bounding_box": bounding_box,
        "volume_cm3": float(body.volume),
        "material": material,
        "body_type": body_type,
    }


def handle_list_features(params):
    """Return features from the root component timeline.

    The Fusion 360 Python API does not expose a per-feature creation
    timestamp, so the response's ``timestamp`` field is captured at
    handler call time (``utcnow().isoformat() + "Z"``). Document this
    so consumers do not read it as "when the feature was created".

    The array is capped at 200 entries; if the design has more the
    response includes a top-level ``truncated: true`` flag.

    Returns:
        dict with 'features' list and 'truncated' bool.

    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN): no design is open.
    """
    design = _get_active_design()
    features = design.rootComponent.features
    total = features.count
    cap = 200
    truncated = total > cap

    captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entries = []
    upper = min(total, cap)
    for i in range(upper):
        feature = features.item(i)
        raw_type = str(feature.objectType)
        short_type = raw_type.split(".")[-1] if raw_type else ""
        entries.append({
            "name": feature.name,
            "type": short_type,
            "is_suppressed": bool(feature.isSuppressed),
            "timestamp": captured_at,
        })

    return {
        "features": entries,
        "truncated": truncated,
    }


def handle_list_sketches(params):
    """Return sketches in the root component.

    Each entry exposes the sketch's display name, the count of
    contained profiles, and an array of ``entityToken`` strings for
    the entities the sketch references (typically its reference
    plane). When a sketch has no reference plane (e.g. direct
    modeling or surface-based sketches) the array is empty.

    Returns:
        dict with 'sketches' list.

    Raises:
        FusionAPIError(NO_ACTIVE_DESIGN): no design is open.
    """
    design = _get_active_design()
    sketches = design.rootComponent.sketches

    entries = []
    for i in range(sketches.count):
        sketch = sketches.item(i)
        referenced = []
        ref_plane = sketch.referencePlane
        if ref_plane is not None:
            try:
                token = ref_plane.entityToken
            except Exception:
                token = None
            if token:
                referenced.append(token)

        entries.append({
            "name": sketch.name,
            "profile_count": int(sketch.profiles.count),
            "referenced_geometry": referenced,
        })

    return {"sketches": entries}


# Handler registry: maps JSON-RPC method names to handler functions
HANDLERS = {
    "get_active_design_parameters": handle_get_active_design_parameters,
    "measure_clearance": handle_measure_clearance,
    "update_user_parameter": handle_update_user_parameter,
    "create_circular_cutout": handle_create_circular_cutout,
    "create_rectangular_cutout": handle_create_rectangular_cutout,
    "create_slot_cutout": handle_create_slot_cutout,
    "list_bodies": handle_list_bodies,
    "get_document_info": handle_get_document_info,
    "get_body_info": handle_get_body_info,
    "list_features": handle_list_features,
    "list_sketches": handle_list_sketches,
}
