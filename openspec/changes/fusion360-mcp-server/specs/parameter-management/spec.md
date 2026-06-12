# Parameter Management Specification

## Purpose

Read and write User Parameters in the active Fusion 360 design. Supports listing all parameters and updating a parameter with automatic rollback on `computeAll()` failure.

## Requirements

### Requirement: Get Active Design Parameters

The system SHALL return all User Parameters from the active design as a JSON array. Each parameter SHALL include `name` (string), `expression` (string), `value` (number in Fusion internal units), and `unit` (string: "cm" for lengths, "deg" for angles).

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

### Requirement: Update User Parameter with Rollback

The system SHALL modify a user parameter's expression and trigger `design.computeAll()`. Before mutation, the system SHALL snapshot all current parameter expressions. If `computeAll()` fails, the system SHALL restore all parameters from the snapshot and return an error. The timeout for `computeAll()` SHALL be 30 seconds (configurable).

#### Scenario: Parameter updated successfully

- GIVEN a parameter `Width` with expression `"40 mm"`
- WHEN `update_user_parameter` is called with `parameter_name: "Width"`, `new_expression: "50 mm"`
- THEN the parameter expression changes to `"50 mm"`
- AND `computeAll()` is triggered
- AND the response confirms success

#### Scenario: Rollback on computeAll failure

- GIVEN parameters `Width` = `"40 mm"` and `Height` = `"30 mm"`
- WHEN `update_user_parameter` is called with an expression that breaks the timeline
- AND `computeAll()` throws an exception
- THEN `Width` is restored to `"40 mm"`
- AND `Height` remains `"30 mm"`
- AND the response contains error code `-32000` with the Fusion API error message

#### Scenario: Parameter not found

- GIVEN no parameter named `NonExistent` exists
- WHEN `update_user_parameter` is called with `parameter_name: "NonExistent"`
- THEN the response contains error code `-32001` with "Parameter 'NonExistent' not found"

#### Scenario: Invalid expression format

- GIVEN a parameter `Width` exists
- WHEN `update_user_parameter` is called with `new_expression: "not_a_number"`
- THEN the response contains error code `-32001` with an expression validation error
