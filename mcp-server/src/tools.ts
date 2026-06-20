import { z } from "zod";
import { FusionClient } from "./jsonrpc-client.js";
import type { McpToolResult } from "./types.js";

// ---------------------------------------------------------------------------
// Tool: get_active_design_parameters
// ---------------------------------------------------------------------------

export const getActiveDesignParametersShape = {};

export async function handleGetActiveDesignParameters(
  client: FusionClient,
): Promise<McpToolResult> {
  return client.call("get_active_design_parameters");
}

// ---------------------------------------------------------------------------
// Tool: measure_clearance
// ---------------------------------------------------------------------------

export const measureClearanceShape = {
  body1_name: z.string().describe("Name of the first solid body"),
  body2_name: z.string().describe("Name of the second solid body"),
};

export async function handleMeasureClearance(
  client: FusionClient,
  args: { body1_name: string; body2_name: string },
): Promise<McpToolResult> {
  return client.call("measure_clearance", args);
}

// ---------------------------------------------------------------------------
// Tool: update_user_parameter
// ---------------------------------------------------------------------------

export const updateUserParameterShape = {
  parameter_name: z.string().describe("Name of the user parameter to update"),
  new_expression: z
    .string()
    .describe("New expression value (e.g. '50 mm', '3.5 cm')"),
};

export async function handleUpdateUserParameter(
  client: FusionClient,
  args: { parameter_name: string; new_expression: string },
): Promise<McpToolResult> {
  return client.call("update_user_parameter", args);
}

// ---------------------------------------------------------------------------
// Tool: create_circular_cutout
// ---------------------------------------------------------------------------

export const createCircularCutoutShape = {
  target_body: z.string().describe("Name of the body to cut into"),
  face_index: z.number().int().describe("1-based index of the face on the target body"),
  diameter_mm: z.number().describe("Diameter of the circular cutout in millimeters"),
  depth_mm: z.number().describe("Depth of the cutout in millimeters"),
};

export async function handleCreateCircularCutout(
  client: FusionClient,
  args: {
    target_body: string;
    face_index: number;
    diameter_mm: number;
    depth_mm: number;
  },
): Promise<McpToolResult> {
  return client.call("create_circular_cutout", args);
}

// ---------------------------------------------------------------------------
// Tool: create_rectangular_cutout
// ---------------------------------------------------------------------------

export const createRectangularCutoutShape = {
  target_body: z.string().describe("Name of the body to cut into"),
  face_index: z.number().int().describe("1-based index of the face on the target body"),
  width_mm: z.number().describe("Width of the rectangular cutout in millimeters"),
  height_mm: z.number().describe("Height of the rectangular cutout in millimeters"),
  depth_mm: z.number().describe("Depth of the cutout in millimeters"),
  angle_deg: z.number().default(0).describe("Rotation angle in degrees (default: 0)"),
};

export async function handleCreateRectangularCutout(
  client: FusionClient,
  args: {
    target_body: string;
    face_index: number;
    width_mm: number;
    height_mm: number;
    depth_mm: number;
    angle_deg?: number;
  },
): Promise<McpToolResult> {
  return client.call("create_rectangular_cutout", args);
}

// ---------------------------------------------------------------------------
// Tool: create_slot_cutout
// ---------------------------------------------------------------------------

export const createSlotCutoutShape = {
  target_body: z.string().describe("Name of the body to cut into"),
  face_index: z.number().int().describe("1-based index of the face on the target body"),
  length_mm: z.number().describe("Length of the slot in millimeters"),
  width_mm: z.number().describe("Width of the slot in millimeters"),
  depth_mm: z.number().describe("Depth of the cutout in millimeters"),
  angle_deg: z.number().default(0).describe("Rotation angle in degrees (default: 0)"),
};

export async function handleCreateSlotCutout(
  client: FusionClient,
  args: {
    target_body: string;
    face_index: number;
    length_mm: number;
    width_mm: number;
    depth_mm: number;
    angle_deg?: number;
  },
): Promise<McpToolResult> {
  return client.call("create_slot_cutout", args);
}

// ---------------------------------------------------------------------------
// Tool: list_bodies
// ---------------------------------------------------------------------------

export const listBodiesShape = {};

export async function handleListBodies(
  client: FusionClient,
): Promise<McpToolResult> {
  return client.call("list_bodies");
}

// ---------------------------------------------------------------------------
// Tool: get_document_info
// ---------------------------------------------------------------------------

export const getDocumentInfoShape = {};

export async function handleGetDocumentInfo(
  client: FusionClient,
): Promise<McpToolResult> {
  return client.call("get_document_info");
}

// ---------------------------------------------------------------------------
// Tool: get_body_info
// ---------------------------------------------------------------------------

export const getBodyInfoShape = {
  body_name: z
    .string()
    .min(1)
    .describe("Name of the body to inspect (exact match)"),
};

export async function handleGetBodyInfo(
  client: FusionClient,
  args: { body_name: string },
): Promise<McpToolResult> {
  return client.call("get_body_info", args);
}

// ---------------------------------------------------------------------------
// Tool: list_features
// ---------------------------------------------------------------------------

export const listFeaturesShape = {};

export async function handleListFeatures(
  client: FusionClient,
): Promise<McpToolResult> {
  return client.call("list_features");
}

// ---------------------------------------------------------------------------
// Tool: list_sketches
// ---------------------------------------------------------------------------

export const listSketchesShape = {};

export async function handleListSketches(
  client: FusionClient,
): Promise<McpToolResult> {
  return client.call("list_sketches");
}