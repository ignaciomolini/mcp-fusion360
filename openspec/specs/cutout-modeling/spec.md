# Cutout Modeling Specification

## Purpose

Create sketch-based extrusion cutouts (circular, rectangular, slot) on a specified face of a target body. All dimensions are in millimeters at the tool interface; Component A converts to centimeters for the Fusion API.

**Source**: Created from `openspec/changes/fusion360-mcp-server/specs/cutout-modeling/spec.md` (the original base spec) merged with the delta from `openspec/changes/face-index-and-runtime-coverage/specs/cutout-modeling/spec.md` (change `face-index-and-runtime-coverage`, archived 2026-06-24). The previous change's base spec used `face_index: 0` in the happy-path scenarios (a bug — the implementation uses 1-based indexing); the delta corrected this to `face_index: 1`, which is reflected here. The delta also added an optional `face_selector` to all three cutout tools and a new "Face Resolution Order" requirement. This is the first time the `cutout-modeling` capability has been promoted to permanent specs.

## Requirements

### Requirement: Create Circular Cutout

The system SHALL create a circular cutout on a face of a target body. Parameters: `target_body` (string), `face_index` (int, **1-based, deprecated** — use `face_selector`), `face_selector` (object, optional — see "Face Resolution Order"), `diameter_mm` (float), `depth_mm` (float). The system SHALL validate `target_body` exists, dimensions are positive, and exactly one of `face_index` or `face_selector` is provided.
(Previously: `face_index` was the only face identifier.)

#### Scenario: Circular cutout created successfully

- GIVEN a body `Panel` with at least 3 faces
- WHEN `create_circular_cutout` is called with `target_body: "Panel"`, `face_index: 1`, `diameter_mm: 10.0`, `depth_mm: 5.0`
- THEN a circular hole of 10 mm diameter and 5 mm depth exists on face 1 of `Panel`

#### Scenario: Invalid face index

- GIVEN a body `Panel` with 3 faces (indices 1–3)
- WHEN `create_circular_cutout` is called with `face_index: 5`
- THEN the response contains error code `-32001` with "face_index 5 out of range for body 'Panel' (1-3)"

#### Scenario: Negative diameter rejected

- WHEN `create_circular_cutout` is called with `diameter_mm: -5.0`
- THEN the response contains error code `-32001` with "diameter_mm must be positive"

#### Scenario: Target body not found

- WHEN `create_circular_cutout` is called with `target_body: "Missing"`
- THEN the response contains error code `-32001` with "Body 'Missing' not found"

### Requirement: Create Rectangular Cutout

The system SHALL create a rectangular cutout on a specified face. Parameters: `target_body` (string), `face_index` (int, **1-based, deprecated** — use `face_selector`), `face_selector` (object, optional — see "Face Resolution Order"), `width_mm` (float), `height_mm` (float), `depth_mm` (float), `angle_deg` (float, default 0). The cutout SHALL be a centered rectangle extruded as a cut feature, rotated by `angle_deg` around the face center.
(Previously: `face_index` was the only face identifier.)

#### Scenario: Rectangular cutout created successfully

- GIVEN a body `Plate` with at least 1 face
- WHEN `create_rectangular_cutout` is called with `target_body: "Plate"`, `face_index: 1`, `width_mm: 20.0`, `height_mm: 10.0`, `depth_mm: 3.0`
- THEN a 20x10 mm rectangular hole of 3 mm depth exists on face 1

#### Scenario: Rectangular cutout with rotation

- WHEN `create_rectangular_cutout` is called with `angle_deg: 45.0`
- THEN the rectangle is rotated 45 degrees around the face center

#### Scenario: Zero width rejected

- WHEN `create_rectangular_cutout` is called with `width_mm: 0`
- THEN the response contains error code `-32001` with "width_mm must be positive"

### Requirement: Create Slot Cutout

The system SHALL create a slot (obround) cutout on a specified face. Parameters: `target_body` (string), `face_index` (int, **1-based, deprecated** — use `face_selector`), `face_selector` (object, optional — see "Face Resolution Order"), `length_mm` (float), `width_mm` (float), `depth_mm` (float), `angle_deg` (float, default 0). The cutout SHALL be a slot profile extruded as a cut feature, rotated by `angle_deg`.
(Previously: `face_index` was the only face identifier.)

#### Scenario: Slot cutout created successfully

- GIVEN a body `Bracket` with at least 1 face
- WHEN `create_slot_cutout` is called with `target_body: "Bracket"`, `face_index: 1`, `length_mm: 30.0`, `width_mm: 8.0`, `depth_mm: 4.0`
- THEN a slot of 30 mm length, 8 mm width, 4 mm deep, exists on face 1

#### Scenario: Length shorter than width rejected

- WHEN `create_slot_cutout` is called with `length_mm: 5.0`, `width_mm: 10.0`
- THEN the response contains error code `-32001` with "length_mm must be >= width_mm for a valid slot"

#### Scenario: Default angle is zero

- WHEN `create_slot_cutout` is called without `angle_deg`
- THEN the slot is created with 0 degree rotation

### Requirement: Face Resolution Order

`face_selector` = `{normal?: {x,y,z} unit vector, tolerance_degrees?: number (default 5), centroid?: {x,y,z} mm, tolerance_mm?: number (default 0.5)}`. At least one of `normal`/`centroid` SHALL be present. Resolution:

| Inputs | Result |
|--------|--------|
| `face_index` + `face_selector` | Use `face_index` (deprecation-period precedence) |
| `face_selector` only | Match by `normal` within `tolerance_degrees`; tiebreak by `centroid` distance. If no `normal`, match by `centroid` within `tolerance_mm` |
| `face_index` only | Validate range, use `body.faces.item(index - 1)` (unchanged) |
| Multiple matches | Pick face with centroid closest to `selector.centroid`; else largest `area_mm2` |
| No match | Error `-32001` "no face matched selector" |
| Neither provided | Error `-32001` "face_index or face_selector is required" |

Helper: `resolve_face(body, face_index=None, face_selector=None)` in `Fusion360MCP/tools.py`, called by all three cutout handlers. Reference: `BRepFace.evaluator.getNormalAtPoint` wrapped in `try/except`; on failure `normal` is `null` and the selector skips that face.

#### Scenario: face_selector.normal matches exactly one face

- GIVEN a body `Plate` where only face 1 has normal `{x: 0, y: 0, z: 1}` (others differ)
- WHEN `resolve_face` is called with `face_selector: {normal: {x: 0, y: 0, z: 1}}`
- THEN the helper returns face 1

#### Scenario: face_selector.normal matches multiple faces — centroid tiebreaker

- GIVEN a body `Slab` with two faces of normal `{x: 0, y: 0, z: 1}`: face 1 at centroid `{x: 0, y: 0, z: 5}` (area 100 mm²) and face 2 at centroid `{x: 0, y: 0, z: -5}` (area 400 mm²)
- WHEN `resolve_face` is called with `face_selector: {normal: {x: 0, y: 0, z: 1}, centroid: {x: 0, y: 0, z: 5}}`
- THEN the helper returns face 1 (closest centroid)

#### Scenario: face_selector with no matching face returns clear error

- GIVEN a body `Plate` with no face whose normal is within 5° of `{x: 1, y: 0, z: 0}`
- WHEN any cutout tool is called with `face_selector: {normal: {x: 1, y: 0, z: 0}}`
- THEN the response contains error code `-32001` with "no face matched selector"

#### Scenario: face_index and face_selector both provided — face_index wins

- GIVEN a body `Plate` where face 1 has normal `{x: 0, y: 0, z: 1}` and face 3 has normal `{x: 0, y: 1, z: 0}`
- WHEN `create_circular_cutout` is called with `target_body: "Plate"`, `face_index: 1`, `face_selector: {normal: {x: 0, y: 1, z: 0}}`, `diameter_mm: 10.0`, `depth_mm: 5.0`
- THEN the cutout lands on face 1 (face_index wins; selector ignored)

### Requirement: Unit Conversion

The system SHALL convert all millimeter inputs to centimeters before passing values to the Fusion API. 1 mm = 0.1 cm. The conversion SHALL be applied to diameter, width, height, length, and depth parameters.

#### Scenario: mm to cm conversion for circular cutout

- WHEN `create_circular_cutout` is called with `diameter_mm: 10.0`, `depth_mm: 5.0`
- THEN the Fusion API receives radius = 0.5 cm and depth = 0.5 cm
