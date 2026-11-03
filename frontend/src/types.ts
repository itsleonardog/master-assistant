/**
 * TypeScript mirrors of the Pydantic contracts in
 * `backend/master_assistant/models/schemas.py`.
 *
 * Field names are kept identical to the JSON payload so the API response can be
 * used without an adapter layer.
 */

export type SuggestionSeverity = "info" | "minor" | "major" | "critical";

export type SuggestionCategory = "loudness" | "eq" | "dynamics" | "stereo" | "peak";

export type SuggestionActionType =
  | "eq_cut"
  | "eq_boost"
  | "compressor"
  | "limiter"
  | "stereo_narrow"
  | "stereo_widen"
  | "gain"
  | "deesser"
  | "saturation";

/** `ok` means aligned with the reference; `minor`/`major` flag a deviation. */
export type BandSeverity = "ok" | "minor" | "major";

export interface LoudnessMetrics {
  integrated_lufs: number;
  short_term_max_lufs: number;
  momentary_max_lufs: number;
  loudness_range_lu: number;
  true_peak_dbtp: number;
  sample_peak_dbfs: number;
  crest_factor_db: number;
  duration_s: number;
}

/** Every field is `user - reference`; duration is intentionally absent. */
export interface LoudnessDelta {
  integrated_lufs_delta: number;
  short_term_max_lufs_delta: number;
  momentary_max_lufs_delta: number;
  loudness_range_lu_delta: number;
  true_peak_dbtp_delta: number;
  sample_peak_dbfs_delta: number;
  crest_factor_db_delta: number;
}

export interface BandDelta {
  name: string;
  freq_hz: number;
  user_db: number;
  reference_db: number;
  delta_db: number;
  severity: BandSeverity;
}

export interface SpectralComparison {
  bands: BandDelta[];
  tilt_delta_db_per_octave: number;
  top_problems: BandDelta[];
}

export interface StereoBandDelta {
  name: string;
  freq_hz: number;
  user_correlation: number;
  reference_correlation: number;
  correlation_delta: number;
  user_side_to_mid_db: number;
  reference_side_to_mid_db: number;
  side_to_mid_delta_db: number;
  severity: BandSeverity;
}

export interface StereoComparison {
  bands: StereoBandDelta[];
  overall_correlation_delta: number;
  overall_side_to_mid_delta_db: number;
  width_hz_delta: number;
  top_problems: StereoBandDelta[];
}

export interface ComparisonReport {
  user_loudness: LoudnessMetrics;
  reference_loudness: LoudnessMetrics;
  loudness_delta: LoudnessDelta;
  spectrum: SpectralComparison;
  /** `null` when either file is mono: mid/side metrics are undefined. */
  stereo: StereoComparison | null;
  warnings: string[];
}

export interface Suggestion {
  id: string;
  priority: number;
  severity: SuggestionSeverity;
  category: SuggestionCategory;
  title: string;
  explanation: string;
  action_type: SuggestionActionType;
  action_params: Record<string, number>;
  measured: Record<string, number>;
  target: Record<string, number>;
}

export interface AnalysisResponse {
  report: ComparisonReport;
  suggestions: Suggestion[];
  /** Same advice already rendered for `daw`, in the same order. */
  rendered_suggestions: string[];
  daw: string;
}

/** Payload of a FastAPI validation error (422). */
export interface ValidationErrorPayload {
  detail: Array<{ loc: (string | number)[]; msg: string; type: string }> | string;
}
