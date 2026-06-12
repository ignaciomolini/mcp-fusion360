# Cutout Modeling Specification

## Purpose

Create sketch-based extrusion cutouts (circular, rectangular, slot) on a specified face of a target body. All dimensions are in millimeters at the tool interface; Component A converts to centimeters for the Fusion API.

## Requirements

### Requirement: Create Circular Cutout

The system SHALL create a circular cutout on a specified face of a target body. Parameters: `target_body` (string), `face_index` (int), `diameter_mm` (float), `depth_mm` (float). The system SHALL validate `target_body` exists, `face_index` is within bounds, and dimensions are positive. The cutout SHALL be a sketch circle extruded as a cut feature.

#### Scenario: Circular cutout created successfully

- GIVEN a body `Panel` with at least 3 faces
- WHEN `create_circular_cutout` is called with `target_body: "Panel"`, `face_index: 0`, `diameter_mm: 10.0`, `depth_mm: 5.0`
- THEN a circular hole of 10 mm diameter and 5 mm depth exists on face 0 of `Panel`

#### Scenario: Invalid face index

- GIVEN a body `Panel` with 3 faces (indices 0-2)
- WHEN `create_circular_cutout` is called with `face_index: 5`
- THEN the response contains error code `-32001` with "face_index 5 out of range for body 'Panel' (0-2)"

#### Scenario: Negative diameter rejected

- WHEN `create_circular_cutout` is called with `diameter_mm: -5.0`
- THEN the response contains error code `-32001` with "diameter_mm must be positive"

#### Scenario: Target body not found

- WHEN `create_circular_cutout` is called with `target_body: "Missing"`
- THEN the response contains error code `-32001` with "Body 'Missing' not found"

### Requirement: Create Rectangular Cutout

The system SHALL create a rectangular cutout on a specified face. Parameters: `target_body` (string), `face_index` (int), `width_mm` (float), `height_mm` (float), `depth_mm` (float), `angle_deg` (float, default 0). The cutout SHALL be a centered rectangle extruded as a cut feature, rotated by `angle_deg` around the face center.

#### Scenario: Rectangular cutout created successfully

- GIVEN a body `Plate` with at least 1 face
- WHEN `create_rectangular_cutout` is called with `target_body: "Plate"`, `face_index: 0`, `width_mm: 20.0`, `height_mm: 10.0`, `depth_mm: 3.0`
- THEN a 20x10 mm rectangular hole of 3 mm depth exists on face 0

#### Scenario: Rectangular cutout with rotation

- WHEN `create_rectangular_cutout` is called with `angle_deg: 45.0`
- THEN the rectangle is rotated 45 degrees around the face center

#### Scenario: Zero width rejected

- WHEN `create_rectangular_cutout` is called with `width_mm: 0`
- THEN the response contains error code `-32001` with "width_mm must be positive"

### Requirement: Create Slot Cutout

The system SHALL create a slot (obround) cutout on a specified face. Parameters: `target_body` (string), `face_index` (int), `length_mm` (float), `width_mm` (float), `depth_mm` (float), `angle_deg` (float, default 0). The cutout SHALL be a slot profile (rectangle with semicircular ends) extruded as a cut feature, rotated by `angle_deg`.

#### Scenario: Slot cutout created successfully

- GIVEN a body `Bracket` with at least 1 face
- WHEN `create_slot_cutout` is called with `target_body: "Bracket"`, `face_index: 0`, `length_mm: 30.0`, `width_mm: 8.0`, `depth_mm: 4.0`
- THEN a slot of 30 mm length and 8 mm width, 4 mm deep, exists on face 0

#### Scenario: Length shorter than width rejected

- WHEN `create_slot_cutout` is called with `length_mm: 5.0`, `width_mm: 10.0`
- THEN the response contains error code `-32001` with "length_mm must be >= width_mm for a valid slot"

#### Scenario: Default angle is zero

- WHEN `create_slot_cutout` is called without `angle_deg`
- THEN the slot is created with 0 degree rotation

### Requirement: Unit Conversion

The system SHALL convert all millimeter inputs to centimeters before passing values to the Fusion API. 1 mm = 0.1 cm. The conversion SHALL be applied to diameter, width, height, length, and depth parameters.

#### Scenario: mm to cm conversion for circular cutout

- WHEN `create_circular_cutout` is called with `diameter_mm: 10.0`, `depth_mm: 5.0`
- THEN the Fusion API receives radius = 0.5 cm and depth = 0.5 cm
