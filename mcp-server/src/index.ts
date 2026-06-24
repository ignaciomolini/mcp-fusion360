#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { FusionClient } from "./jsonrpc-client.js";
import {
  getActiveDesignParametersShape,
  handleGetActiveDesignParameters,
  measureClearanceShape,
  handleMeasureClearance,
  updateUserParameterShape,
  handleUpdateUserParameter,
  createCircularCutoutShape,
  handleCreateCircularCutout,
  createRectangularCutoutShape,
  handleCreateRectangularCutout,
  createSlotCutoutShape,
  handleCreateSlotCutout,
  listBodiesShape,
  handleListBodies,
  getDocumentInfoShape,
  handleGetDocumentInfo,
  getBodyInfoShape,
  handleGetBodyInfo,
  listFeaturesShape,
  handleListFeatures,
  listSketchesShape,
  handleListSketches,
} from "./tools.js";

const server = new McpServer({
  name: "mcp-fusion360",
  version: "0.1.0",
});

const client = new FusionClient();

// Tool registrations — each call wires a Zod schema + handler to the MCP server

server.tool(
  "get_active_design_parameters",
  "Get all user parameters in the active Fusion 360 design.",
  async () => handleGetActiveDesignParameters(client),
);

server.tool(
  "measure_clearance",
  "Measure the minimum distance between two solid bodies.",
  measureClearanceShape,
  async (args) => handleMeasureClearance(client, args),
);

server.tool(
  "update_user_parameter",
  "Update a user parameter and recompute the design.",
  updateUserParameterShape,
  async (args) => handleUpdateUserParameter(client, args),
);

server.tool(
  "create_circular_cutout",
  "Create a circular hole/cutout on a face. Use `face_selector` instead (preferred).",
  createCircularCutoutShape,
  async (args) => handleCreateCircularCutout(client, args),
);

server.tool(
  "create_rectangular_cutout",
  "Create a rectangular cutout on a face. Use `face_selector` instead (preferred).",
  createRectangularCutoutShape,
  async (args) => handleCreateRectangularCutout(client, args),
);

server.tool(
  "create_slot_cutout",
  "Create a slot (obround) cutout on a face. Use `face_selector` instead (preferred).",
  createSlotCutoutShape,
  async (args) => handleCreateSlotCutout(client, args),
);

server.tool(
  "list_bodies",
  "List all solid/surface bodies in the root component.",
  async () => handleListBodies(client),
);

server.tool(
  "get_document_info",
  "Get active document metadata (name, units, design type, material library).",
  async () => handleGetDocumentInfo(client),
);

server.tool(
  "get_body_info",
  "Get physical properties of a named body (face count, bounding box, volume, material, type).",
  getBodyInfoShape,
  async (args) => handleGetBodyInfo(client, args),
);

server.tool(
  "list_features",
  "List features in the root component timeline (capped at 200).",
  async () => handleListFeatures(client),
);

server.tool(
  "list_sketches",
  "List sketches in the root component (name, profile count, referenced geometry).",
  async () => handleListSketches(client),
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // eslint-disable-next-line no-console
  console.error("Fusion 360 MCP Server connected via stdio");
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error("Fatal error starting Fusion 360 MCP Server:", err);
  process.exit(1);
});