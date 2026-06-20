# Delta for Parameter Management

## MODIFIED Requirements

### Requirement: Get Active Design Parameters

The system SHALL return all User Parameters from the active design as a JSON array. Each parameter SHALL include `name` (string), `expression` (string), `value` (number in Fusion internal units), `unit` (string: "cm" for lengths, "deg" for angles), `comment` (string or null), and `is_favorite` (boolean). The new metadata fields (`comment`, `is_favorite`) are additive; existing fields and their semantics SHALL be preserved.
(Previously: original requirement exposed only `name`, `expression`, `value`, and `unit`. A planned `role` field was dropped during design verification — the Fusion 360 API exposes `role` only on `ModelParameter`, not on `UserParameter`.)

#### Scenario: Returns all user parameters

- GIVEN an active design with 3 user parameters: `Width` (40 mm), `Thickness` (25 mm), `Angle` (90 deg)
- WHEN `get_active_design_parameters` is called
- THEN the response contains 3 entries with name, expression, value, and unit
- AND `Width` has `unit: "cm"` and `value: 4.0`

#### Scenario: Empty design returns empty array

- GIVEN an active design with no user parameters
- WHEN `get_active_design_parameters` is called
- THEN the response contains an empty parameters array

#### Scenario: No active design returns error

- GIVEN no document is open in Fusion 360
- WHEN `get_active_design_parameters` is called
- THEN the response contains error code `-32002`

#### Scenario: Returns comment and is_favorite fields

- GIVEN a parameter `Width` with comment "outer width in mm" and `is_favorite: false`
- WHEN `get_active_design_parameters` is called
- THEN the response includes `comment: "outer width in mm"` and `is_favorite: false` for `Width`

#### Scenario: Favorite parameter has is_favorite true

- GIVEN a parameter `Thickness` marked as favorite
- WHEN `get_active_design_parameters` is called
- THEN `Thickness` has `is_favorite: true` in the response

#### Scenario: Parameter without comment

- GIVEN a parameter `Angle` with no comment set
- WHEN `get_active_design_parameters` is called
- THEN `Angle` has `comment: null` in the response
