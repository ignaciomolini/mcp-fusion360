/** JSON-RPC 2.0 request sent from Component B to Component A. */
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
  id: number | string;
}

/** JSON-RPC 2.0 error object returned by Component A. */
export interface JsonRpcError {
  code: number;
  message: string;
  data?: {
    fusion_trace?: string;
    detail?: string;
  };
}

/** JSON-RPC 2.0 response from Component A. */
export interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: unknown;
  error?: JsonRpcError;
}

/** MCP CallToolResult compatible type for tool responses. */
export interface McpToolResult {
  [x: string]: unknown;
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
}

/** A point in 3D space, used for bounding box corners. */
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

/** Axis-aligned bounding box with min/max corners in millimeters. */
export interface BoundingBox {
  min: Point3D;
  max: Point3D;
}

/** Per-face geometry entry returned inside `BodyInfo.faces`.
 *  `normal` is `null` when the underlying BRepFace has no analytic
 *  normal (e.g. imported B-spline or degenerate face). */
export interface FaceGeometry {
  index: number;
  normal: Point3D | null;
  centroid: Point3D;
  area_mm2: number;
}

/** Client-supplied face selector passed to cutout tools. At least one of
 *  `normal` / `centroid` must be present. */
export interface FaceSelector {
  normal?: Point3D;
  centroid?: Point3D;
  tolerance_degrees?: number;
  tolerance_mm?: number;
}

/** Result of `get_body_info`. Documentation-only — the MCP `registerTool`
 *  API does not require typed results; the runtime payload is whatever
 *  Component A returns. */
export interface BodyInfo {
  face_count: number;
  bounding_box: BoundingBox;
  volume_cm3: number;
  material: string | null;
  body_type: "SolidBody" | "SurfaceBody";
  faces?: FaceGeometry[];
  faces_truncated?: boolean;
}

/** Result of `list_bodies`. */
export interface ListBodiesResult {
  bodies: Array<{ name: string; index: number }>;
}

/** Result of `get_document_info`. */
export interface DocumentInfo {
  name: string;
  units: string;
  design_type: "ParametricDesign" | "DirectDesign" | string;
  material_library: string;
}

/** Single feature entry from `list_features`. */
export interface FeatureSummary {
  name: string;
  type: string;
  is_suppressed: boolean;
  timestamp: string;
}

/** Result of `list_features`. */
export interface ListFeaturesResult {
  features: FeatureSummary[];
  truncated: boolean;
}

/** Single sketch entry from `list_sketches`. */
export interface SketchSummary {
  name: string;
  profile_count: number;
  referenced_geometry: string[];
}

/** Result of `list_sketches`. */
export interface ListSketchesResult {
  sketches: SketchSummary[];
}