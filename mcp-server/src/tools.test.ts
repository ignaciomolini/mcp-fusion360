/**
 * Unit tests for the tool handlers in tools.ts.
 *
 * Component B is the TypeScript MCP wrapper. It does not import
 * `adsk` (the Fusion 360 API) and runs as a plain Node process,
 * so we can mock FusionClient.call and assert the JSON-RPC method
 * name + args that each handler forwards.
 *
 * Component A (the Python add-in) is not exercised here — it can
 * only be verified inside a running Fusion 360 instance.
 */

import { describe, expect, it, vi } from "vitest";

import type { FusionClient } from "./jsonrpc-client.js";
import {
  FaceSelectorSchema,
  handleCreateCircularCutout,
  handleCreateRectangularCutout,
  handleCreateSlotCutout,
  handleGetActiveDesignParameters,
  handleGetBodyInfo,
  handleGetDocumentInfo,
  handleListBodies,
  handleListFeatures,
  handleListSketches,
  handleMeasureClearance,
  handleUpdateUserParameter,
} from "./tools.js";

/**
 * Build a FusionClient stub whose `.call()` returns a canned
 * successful MCP result and records every invocation.
 */
function makeMockClient(response: unknown = { ok: true }): {
  client: FusionClient;
  call: ReturnType<typeof vi.fn>;
} {
  const call = vi.fn().mockResolvedValue({
    isError: false,
    content: [{ type: "text", text: JSON.stringify(response) }],
  });
  const client = { call } as unknown as FusionClient;
  return { client, call };
}

// ---------------------------------------------------------------------------
// Pre-existing tools (smoke tests; they were working before this change)
// ---------------------------------------------------------------------------

describe("pre-existing tools", () => {
  it("get_active_design_parameters forwards to the same JSON-RPC method", async () => {
    const { client, call } = makeMockClient();
    await handleGetActiveDesignParameters(client);
    expect(call).toHaveBeenCalledWith("get_active_design_parameters");
    expect(call).toHaveBeenCalledTimes(1);
  });

  it("measure_clearance forwards body1_name and body2_name", async () => {
    const { client, call } = makeMockClient();
    await handleMeasureClearance(client, {
      body1_name: "Box1",
      body2_name: "Box2",
    });
    expect(call).toHaveBeenCalledWith("measure_clearance", {
      body1_name: "Box1",
      body2_name: "Box2",
    });
  });

  it("update_user_parameter forwards name and new expression", async () => {
    const { client, call } = makeMockClient();
    await handleUpdateUserParameter(client, {
      parameter_name: "Width",
      new_expression: "50 mm",
    });
    expect(call).toHaveBeenCalledWith("update_user_parameter", {
      parameter_name: "Width",
      new_expression: "50 mm",
    });
  });

  it("create_circular_cutout forwards all four params", async () => {
    const { client, call } = makeMockClient();
    await handleCreateCircularCutout(client, {
      target_body: "Panel",
      face_index: 1,
      diameter_mm: 10,
      depth_mm: 5,
    });
    expect(call).toHaveBeenCalledWith("create_circular_cutout", {
      target_body: "Panel",
      face_index: 1,
      diameter_mm: 10,
      depth_mm: 5,
    });
  });

  it("create_rectangular_cutout forwards all five params", async () => {
    const { client, call } = makeMockClient();
    await handleCreateRectangularCutout(client, {
      target_body: "Panel",
      face_index: 1,
      width_mm: 20,
      height_mm: 10,
      depth_mm: 5,
      angle_deg: 45,
    });
    expect(call).toHaveBeenCalledWith("create_rectangular_cutout", {
      target_body: "Panel",
      face_index: 1,
      width_mm: 20,
      height_mm: 10,
      depth_mm: 5,
      angle_deg: 45,
    });
  });

  it("create_slot_cutout forwards all five params", async () => {
    const { client, call } = makeMockClient();
    await handleCreateSlotCutout(client, {
      target_body: "Panel",
      face_index: 1,
      length_mm: 30,
      width_mm: 8,
      depth_mm: 5,
      angle_deg: 0,
    });
    expect(call).toHaveBeenCalledWith("create_slot_cutout", {
      target_body: "Panel",
      face_index: 1,
      length_mm: 30,
      width_mm: 8,
      depth_mm: 5,
      angle_deg: 0,
    });
  });
});

// ---------------------------------------------------------------------------
// New introspection tools (the focus of this change)
// ---------------------------------------------------------------------------

describe("list_bodies", () => {
  it("calls the list_bodies JSON-RPC method with no params", async () => {
    const { client, call } = makeMockClient();
    await handleListBodies(client);
    expect(call).toHaveBeenCalledWith("list_bodies");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

describe("get_document_info", () => {
  it("calls the get_document_info JSON-RPC method with no params", async () => {
    const { client, call } = makeMockClient();
    await handleGetDocumentInfo(client);
    expect(call).toHaveBeenCalledWith("get_document_info");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

describe("get_body_info", () => {
  it("forwards the body_name argument to the JSON-RPC method", async () => {
    const { client, call } = makeMockClient();
    await handleGetBodyInfo(client, { body_name: "Plate" });
    expect(call).toHaveBeenCalledWith("get_body_info", {
      body_name: "Plate",
    });
  });

  it("forwards a different body_name unchanged", async () => {
    const { client, call } = makeMockClient();
    await handleGetBodyInfo(client, { body_name: "Bracket" });
    expect(call).toHaveBeenCalledWith("get_body_info", {
      body_name: "Bracket",
    });
  });
});

describe("list_features", () => {
  it("calls the list_features JSON-RPC method with no params", async () => {
    const { client, call } = makeMockClient();
    await handleListFeatures(client);
    expect(call).toHaveBeenCalledWith("list_features");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

describe("list_sketches", () => {
  it("calls the list_sketches JSON-RPC method with no params", async () => {
    const { client, call } = makeMockClient();
    await handleListSketches(client);
    expect(call).toHaveBeenCalledWith("list_sketches");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// get_active_design_parameters — the additive delta
// ---------------------------------------------------------------------------

describe("get_active_design_parameters (delta)", () => {
  it("still calls the same JSON-RPC method name and no args", async () => {
    // The Python handler is the one that adds the comment/is_favorite
    // fields. The TypeScript shape and handler are unchanged.
    const { client, call } = makeMockClient();
    await handleGetActiveDesignParameters(client);
    expect(call).toHaveBeenCalledWith("get_active_design_parameters");
    expect(call).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// FaceSelectorSchema — face_index-and-runtime-coverage change
// ---------------------------------------------------------------------------

describe("FaceSelectorSchema", () => {
  it("rejects an empty selector (no normal or centroid)", () => {
    const result = FaceSelectorSchema.safeParse({});
    expect(result.success).toBe(false);
  });

  it("accepts a normal-only selector", () => {
    const result = FaceSelectorSchema.safeParse({
      normal: { x: 0, y: 0, z: 1 },
    });
    expect(result.success).toBe(true);
  });

  it("accepts a centroid-only selector", () => {
    const result = FaceSelectorSchema.safeParse({
      centroid: { x: 5, y: 0, z: 0 },
    });
    expect(result.success).toBe(true);
  });

  it("defaults tolerance_degrees to 5 when not provided", () => {
    const parsed = FaceSelectorSchema.parse({
      normal: { x: 0, y: 0, z: 1 },
    });
    expect(parsed.tolerance_degrees).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// face_selector forwarding — the three cutout tools
// ---------------------------------------------------------------------------

describe("face_selector forwarding", () => {
  it("create_circular_cutout forwards face_selector to client.call", async () => {
    const { client, call } = makeMockClient();
    const selector = { normal: { x: 0, y: 0, z: 1 } };
    await handleCreateCircularCutout(client, {
      target_body: "Panel",
      face_selector: selector,
      diameter_mm: 10,
      depth_mm: 5,
    });
    expect(call).toHaveBeenCalledWith("create_circular_cutout", {
      target_body: "Panel",
      face_selector: selector,
      diameter_mm: 10,
      depth_mm: 5,
    });
  });

  it("create_rectangular_cutout forwards face_selector to client.call", async () => {
    const { client, call } = makeMockClient();
    const selector = { normal: { x: 0, y: 0, z: 1 }, centroid: { x: 0, y: 0, z: 5 } };
    await handleCreateRectangularCutout(client, {
      target_body: "Plate",
      face_selector: selector,
      width_mm: 20,
      height_mm: 10,
      depth_mm: 3,
      angle_deg: 45,
    });
    expect(call).toHaveBeenCalledWith("create_rectangular_cutout", {
      target_body: "Plate",
      face_selector: selector,
      width_mm: 20,
      height_mm: 10,
      depth_mm: 3,
      angle_deg: 45,
    });
  });

  it("create_slot_cutout forwards face_selector to client.call", async () => {
    const { client, call } = makeMockClient();
    const selector = { centroid: { x: 0, y: 0, z: 5 } };
    await handleCreateSlotCutout(client, {
      target_body: "Bracket",
      face_selector: selector,
      length_mm: 30,
      width_mm: 8,
      depth_mm: 4,
      angle_deg: 0,
    });
    expect(call).toHaveBeenCalledWith("create_slot_cutout", {
      target_body: "Bracket",
      face_selector: selector,
      length_mm: 30,
      width_mm: 8,
      depth_mm: 4,
      angle_deg: 0,
    });
  });
});
