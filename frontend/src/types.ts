// ─── DamSafe — Shared TypeScript Types ───────────────────────────────────────

export type Project = {
  id: string;
  name: string;
  site_key: string;
  synthetic: boolean;
  description?: string;
  verified_bounds_wgs84: [number, number, number, number] | null;
  computation_crs?: string | null;
  vertical_reference?: string | null;
  source_url?: string | null;
};

export type Dataset = {
  id: string;
  name: string;
  kind: string;
  version: number;
  sha256: string;
  bytes?: number;
  provenance: {
    status: string;
    units: string;
    agency?: string;
    acquisition_date?: string | null;
    source_url?: string;
    licence?: string;
  };
  inspection: { issues: { code: string; message: string }[] };
};

export type Finding = { code: string; message: string };

export type Readiness = { missing: Finding[]; warnings: Finding[] };

export type Scenario = {
  id: string;
  name: string;
  sha256: string;
  created_at?: string;
  evidence_status?: string;
  snapshot: {
    input_mode: string;
    scenario?: {
      forcing?: { mode?: string };
      start_time?: string;
      end_time?: string;
    };
  };
};

export type Job = {
  id: string;
  state: string;
  body: { result?: Readiness; kind?: string; created_at?: string };
};

export type Engine = {
  engine: 'dflowfm' | 'dualsphysics';
  available: boolean;
  reason?: string;
  image_id?: string;
};

export type HealthStatus = {
  status: string;
  database: string;
  postgis?: string | null;
  preview: boolean;
  phase?: string;
  engines: Engine[];
};

export type NumericalRun = {
  id: string;
  state: string;
  input: {
    request: { engine: string; case_kind: string; scenario_id?: string };
    evidence_status?: string;
    case_classification?: string;
    configuration_hash?: string;
  };
  result: {
    error?: string;
    reason?: string;
    progress?: {
      stage?: string;
      elapsed_seconds?: number;
      cells_done?: number;
      cells_total?: number;
      frame?: number;
      frames_total?: number;
    };
    normalization?: {
      frames: number;
      cells: number;
      duration_seconds: number;
      normalized_sha256?: string;
    };
    postprocessing?: { product_sha256?: string; source_normalized_sha256?: string };
  };
};

export type ResultMetadata = {
  run_id: string;
  source_run_id: string;
  cached: boolean;
  engine: string | null;
  model_version: string | null;
  case_kind: string;
  input_mode: string;
  execution_origin: string;
  units: Record<string, string | null>;
  crs: string | null;
  vertical_datum: string | null;
  nodata_value: { floating: string; wet: number; valid: number };
  source_time_units: string | null;
  source_local_time: string | null;
  start_time: string | null;
  simulation_elapsed_seconds: [number, number];
  output_frame_count: number;
  cell_count: number;
  wet_threshold_m: number;
  arrival_precision: string;
  cell_semantics: string;
  nodata_encoding: string;
};

export type ResultCell = {
  cell: number;
  x: number;
  y: number;
  area_m2: number;
  bed_m: number;
  polygon?: [number, number][];
};

export type ResultFrame = {
  frame: number;
  elapsed_s: number;
  values: (number | null)[];
  states: ('WET' | 'DRY' | 'NODATA')[];
};

export type ResultWindow = {
  state: string;
  field?: string;
  cells: ResultCell[];
  frames: ResultFrame[];
};

export type ProductArea = {
  baseline_water: string;
  threshold_m: number;
  area_semantics: string;
  frames: { frame: number; elapsed_s: number; flooded_area_m2: number; unknown_area_m2: number }[];
};

export type LocationSeries = {
  state: string;
  name?: string;
  cell?: number;
  x?: number;
  y?: number;
  arrival_elapsed_s?: number | null;
  series: { frame: number; elapsed_s: number; depth_m: number | null; state: string }[];
};

export type Ensemble = {
  id: string;
  name: string;
  status: string;
  run_ids: string[];
  frequency_semantics: string;
};

export type ObsResult = {
  execution_state: string;
  provenance_type: string;
  observation_id: string;
  flooded_area_km2?: number | null;
  permanent_water_area_km2?: number | null;
  notes?: string;
  acquisition_time?: string | null;
  scene_info?: { scene_id: string; relative_orbit: number; orbit_direction: string } | null;
  grid_matrix?: number[][] | null;
};

export type ValidationResult = {
  run_id?: string;
  status?: string;
  agreement?: {
    TP: number; FP: number; FN: number; TN: number;
    IoU: number; precision: number; recall: number; F1: number;
  };
  note?: string;
  limitation?: string;
  [key: string]: unknown;
};

export type GaugeResult = {
  station_id: string;
  status: string;
  note?: string;
  run_id?: string;
  [key: string]: unknown;
};

export type ExposureResult = {
  run_id?: string;
  site_key?: string;
  status?: string;
  settlements?: { count?: number; status: string; note?: string };
  agricultural_area_km2?: { value?: number; status: string; note?: string };
  roads_km?: { value?: number; status: string; note?: string };
  critical_infrastructure?: { status: string; items?: unknown[]; note?: string };
  risk_zones?: { status: string; zones?: { level: string; cells: number }[]; note?: string };
  [key: string]: unknown;
};

export type Page =
  | 'dashboard'
  | 'study-area'
  | 'data-setup'
  | 'scenario-builder'
  | 'simulation'
  | 'results'
  | 'validation'
  | 'impact'
  | 'reports';
