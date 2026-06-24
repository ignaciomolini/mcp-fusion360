# Delta for Design Introspection

## MODIFIED Requirements

### Requirement: Get Body Info

The system SHALL return physical properties of a named body as a JSON object including `face_count` (int, actual count), `bounding_box` (object with `min` and `max` x/y/z in mm), `volume_cm3` (number), `material` (string or `null`), and `body_type` (string: `"SolidBody"` or `"SurfaceBody"`). The body SHALL be resolved by exact name match. `face_count` SHALL always reflect the actual total. Per-face geometry is governed by the sibling "Get Body Info with Face Geometry" requirement.
(Previously: declared a 100-entry per-face cap on a deliberately-omitted `faces` array; cap now enforced by the new requirement, redundant sentence removed.)

#### Scenario: Solid body with assigned material

- GIVEN a body `Plate` with 6 faces, material `Steel`, volume 50 cm³
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

## ADDED Requirements

### Requirement: Get Body Info with Face Geometry

The system SHALL include a top-level `faces` array in the `get_body_info` response, enumerating per-face metadata up to 100 entries. Each entry SHALL include `index` (1-based integer, position in `BRepBody.faces`), `normal` (object `{x, y, z}` unit-length, or `null` when `BRepFace.evaluator.getNormalAtPoint` raises — e.g. imported B-splines or degenerate faces), `centroid` (object `{x, y, z}` in mm, bounding-box center), and `area_mm2` (float). When the body has more than 100 faces, the response SHALL include only the first 100 and a top-level `faces_truncated: true` flag. `face_count` SHALL always reflect the actual total. Normal computation SHALL be wrapped in `try/except` so a single bad face does not abort the enumeration.

#### Scenario: Faces enumerated for a body within the cap

- GIVEN a body `Plate` with 6 faces (1 top, 1 bottom, 4 sides)
- WHEN `get_body_info` is called with `body_name: "Plate"`
- THEN the response contains a `faces` array with 6 entries
- AND each entry has `index` (1–6), `normal` (object or null), `centroid` (`{x, y, z}` in mm), and `area_mm2` (float ≥ 0)
- AND `face_count` is 6
- AND `faces_truncated` is absent or `false`

#### Scenario: Face with non-computable normal returns null

- GIVEN a body `ImportedPart` with at least one face whose `getNormalAtPoint` raises
- WHEN `get_body_info` is called with `body_name: "ImportedPart"`
- THEN that face's entry has `normal: null`
- AND `centroid` and `area_mm2` are still populated
- AND other faces in the array have non-null `normal` objects

#### Scenario: Faces array truncated at 100

- GIVEN a body with 500 faces
- WHEN `get_body_info` is called
- THEN the response contains a `faces` array with exactly 100 entries
- AND the response contains `faces_truncated: true` at the top level
- AND `face_count` is 500

#### Scenario: Body with zero faces returns empty array

- GIVEN a body `Empty` with 0 faces
- WHEN `get_body_info` is called with `body_name: "Empty"`
- THEN the response contains a `faces` array with 0 entries
- AND `face_count: 0`
- AND `faces_truncated` is absent or `false`
