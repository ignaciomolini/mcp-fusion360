# Geometry Analysis Specification

## Purpose

Measure minimum distance or interference between two named bodies in the active Fusion 360 design using the Fusion `measureManager` API.

## Requirements

### Requirement: Measure Clearance Between Bodies

The system SHALL calculate the minimum distance between two bodies identified by name. The system SHALL resolve body names from `design.rootComponent.bodies`. The result SHALL include the distance value in millimeters and an `is_interfering` boolean flag.

#### Scenario: Bodies with positive clearance

- GIVEN two bodies `Bracket` and `Frame` separated by 5 mm
- WHEN `measure_clearance` is called with `body1_name: "Bracket"`, `body2_name: "Frame"`
- THEN the response contains `distance_mm: 5.0` and `is_interfering: false`

#### Scenario: Bodies in interference

- GIVEN two bodies `Pin` and `Hole` that overlap by 0.5 mm
- WHEN `measure_clearance` is called
- THEN the response contains `distance_mm: -0.5` and `is_interfering: true`

#### Scenario: Body not found

- GIVEN no body named `Ghost` exists in the active design
- WHEN `measure_clearance` is called with `body2_name: "Ghost"`
- THEN the response contains error code `-32001` with "Body 'Ghost' not found"

#### Scenario: Same body for both parameters

- GIVEN a body `Bracket` exists
- WHEN `measure_clearance` is called with `body1_name: "Bracket"`, `body2_name: "Bracket"`
- THEN the response contains error code `-32001` with "body1_name and body2_name must be different"

#### Scenario: No active design

- GIVEN no document is open
- WHEN `measure_clearance` is called
- THEN the response contains error code `-32002`
