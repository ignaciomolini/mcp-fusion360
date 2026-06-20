# Design Introspection Specification

## Purpose

Read-only discovery of bodies, features, sketches, and document metadata in the active Fusion 360 design. Enables an LLM agent to inspect design state before issuing mutating tool calls.

## Requirements

### Requirement: List Bodies

The system SHALL return all solid bodies in `design.rootComponent.bodies` as a JSON array. Each entry SHALL include `name` (string) and `index` (1-based integer). The enumeration SHALL be read-only and SHALL NOT trigger `computeAll()` or modify the design.

#### Scenario: Active design with multiple bodies

- GIVEN an active design with 3 bodies: `Plate`, `Bracket`, `Pin`
- WHEN `list_bodies` is called
- THEN the response contains 3 entries with `name` and `index` (1, 2, 3 respectively)

#### Scenario: Active design with no bodies

- GIVEN an active design with no solid bodies
- WHEN `list_bodies` is called
- THEN the response contains an empty bodies array

#### Scenario: No active design

- GIVEN no document is open in Fusion 360
- WHEN `list_bodies` is called
- THEN the response contains error code `-32002`

#### Scenario: Very long body list

- GIVEN an active design with 500 bodies
- WHEN `list_bodies` is called
- THEN the response contains 500 entries within the 30s timeout

### Requirement: Get Document Info

The system SHALL return metadata about the active document as a JSON object including `name` (string), `units` (string: `"mm"` or `"cm"`), `design_type` (string: `"ParametricDesign"` or `"DirectDesign"`), and `material_library` (string). The lookup SHALL NOT trigger `computeAll()`.
(`"PlasticDesign"` was removed during design verification — the Fusion 360 `DesignTypes` enum has only `ParametricDesignType` and `DirectDesignType`.)

#### Scenario: Document info returned

- GIVEN an active design named "Escritorio" with display units in mm
- WHEN `get_document_info` is called
- THEN the response contains `name: "Escritorio"`, `units: "mm"`, `design_type: "ParametricDesign"`, and a non-empty `material_library`

#### Scenario: No active design

- GIVEN no document is open
- WHEN `get_document_info` is called
- THEN the response contains error code `-32002`

### Requirement: Get Body Info

The system SHALL return physical properties of a named body as a JSON object including `face_count` (int, actual count), `bounding_box` (object with `min` and `max` x/y/z in millimeters), `volume_cm3` (number, in cubic centimeters), `material` (string or `null`), and `body_type` (string: `"SolidBody"` or `"SurfaceBody"`). The system SHALL resolve the body by exact name match. Per-face enumeration SHALL be capped at 100 entries; `face_count` SHALL always reflect the actual count.

#### Scenario: Solid body with assigned material

- GIVEN a body `Plate` with 6 faces, material `Steel`, and volume 50 cm³
- WHEN `get_body_info` is called with `body_name: "Plate"`
- THEN the response contains `face_count: 6`, `volume_cm3: 50`, `material: "Steel"`, `body_type: "SolidBody"`
- AND `bounding_box` has `min`/`max` x/y/z in mm

#### Scenario: Body with no material assigned

- GIVEN a body `Plate` with no material
- WHEN `get_body_info` is called
- THEN the response contains `material: null`

#### Scenario: Body not found

- GIVEN no body named `Missing` exists
- WHEN `get_body_info` is called with `body_name: "Missing"`
- THEN the response contains error code `-32001` with "Body 'Missing' not found"

#### Scenario: Empty body name rejected

- WHEN `get_body_info` is called with `body_name: ""`
- THEN the response contains error code `-32001`

#### Scenario: No active design

- GIVEN no document is open
- WHEN `get_body_info` is called
- THEN the response contains error code `-32002`

#### Scenario: High face-count body

- GIVEN a body with 500 faces
- WHEN `get_body_info` is called
- THEN the response contains `face_count: 500` and completes within the 30s timeout

### Requirement: List Features

The system SHALL return all features in `design.rootComponent.features` as a JSON array. Each entry SHALL include `name` (string), `type` (string: `"ExtrudeFeature"`, `"CutFeature"`, `"FilletFeature"`, `"ChamferFeature"`, `"RevolveFeature"`, `"HoleFeature"`, etc.), `is_suppressed` (boolean), and `timestamp` (ISO 8601 string). The array SHALL be capped at 200 entries; if the timeline has more, the response SHALL include `truncated: true` at the top level.

#### Scenario: Active design with mixed features

- GIVEN a design with 5 features: 2 extrusions, 1 fillet, 1 cut, 1 hole
- WHEN `list_features` is called
- THEN the response contains 5 entries with `name`, `type`, `is_suppressed`, and `timestamp`

#### Scenario: Active design with no features

- GIVEN a design with no features
- WHEN `list_features` is called
- THEN the response contains an empty features array

#### Scenario: Timeline truncated at 200

- GIVEN a design with 300 features
- WHEN `list_features` is called
- THEN the response contains 200 entries AND `truncated: true`

#### Scenario: Suppressed feature flagged

- GIVEN a feature `OldHole` that is suppressed
- WHEN `list_features` is called
- THEN `OldHole` has `is_suppressed: true`

#### Scenario: No active design

- GIVEN no document is open
- WHEN `list_features` is called
- THEN the response contains error code `-32002`

### Requirement: List Sketches

The system SHALL return all sketches in `design.rootComponent.sketches` as a JSON array. Each entry SHALL include `name` (string), `profile_count` (int), and `referenced_geometry` (array of strings naming the planes or faces the sketch references). The enumeration SHALL be read-only and SHALL NOT trigger `computeAll()`.

#### Scenario: Active design with sketches

- GIVEN a design with 2 sketches: `Sketch1` referencing the XY plane with 1 profile, `Sketch2` referencing a body face with 2 profiles
- WHEN `list_sketches` is called
- THEN the response contains 2 entries with `name`, `profile_count`, and `referenced_geometry`

#### Scenario: Active design with no sketches

- GIVEN a design with no sketches
- WHEN `list_sketches` is called
- THEN the response contains an empty sketches array

#### Scenario: No active design

- GIVEN no document is open
- WHEN `list_sketches` is called
- THEN the response contains error code `-32002`
