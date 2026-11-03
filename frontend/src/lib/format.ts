/**
 * Formatting and validation helpers shared by the UI components.
 *
 * Every formatter degrades to an em dash instead of throwing, so a missing or
 * non-finite metric never breaks the rendering of a whole section.
 */

/** Absolute loudness delta (LU) below which a value counts as aligned. */
export const OK_DELTA_DB = 0.5;

/** Threshold (LU) above which an integrated-LUFS delta is flagged red. */
export const LUFS_DELTA_THRESHOLD_DB = 2.0;

/** Threshold (dB) above which a true-peak delta is flagged red. */
export const TRUE_PEAK_DELTA_THRESHOLD_DB = 1.0;

/** Threshold (LU) above which a loudness-range delta is flagged red. */
export const LRA_DELTA_THRESHOLD_DB = 2.0;

/** Extensions accepted by the client-side validation. */
export const ACCEPTED_EXTENSIONS = [".wav", ".flac", ".aiff", ".aif", ".mp3", ".ogg"] as const;

export const EM_DASH = "\u2014";

/** Classes applied to an "aligned" value. */
const COLOR_OK = "text-emerald-600 dark:text-emerald-400";
/** Classes applied to a value that is close but not aligned. */
const COLOR_WARN = "text-amber-600 dark:text-amber-400";
/** Classes applied to a value that exceeds its threshold. */
const COLOR_BAD = "text-red-600 dark:text-red-400";

/**
 * Format a number with a fixed number of decimals.
 *
 * @param value Number to format.
 * @param digits Number of decimals.
 * @returns Formatted number, or an em dash when unavailable.
 */
export function formatNumber(value: number | null | undefined, digits: number): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return EM_DASH;
  }
  return value.toFixed(digits);
}

/**
 * Format a byte count as megabytes with one decimal.
 *
 * @param size File size in bytes.
 * @returns Human readable size, or an em dash when unavailable.
 */
export function formatBytes(size: number | null | undefined): string {
  if (typeof size !== "number" || !Number.isFinite(size) || size < 0) {
    return EM_DASH;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format a duration in seconds as `mm:ss`.
 *
 * @param seconds Duration in seconds.
 * @returns Formatted duration, or an em dash when unavailable.
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || !Number.isFinite(seconds) || seconds <= 0) {
    return EM_DASH;
  }
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

/**
 * Pick the text colour class for a loudness delta.
 *
 * @param delta User minus reference value.
 * @param threshold Absolute delta at or above which the value is red.
 * @returns Tailwind classes, or an empty string when the delta is unavailable.
 */
export function deltaColorClass(delta: number | null | undefined, threshold: number): string {
  if (typeof delta !== "number" || !Number.isFinite(delta)) {
    return "";
  }
  const magnitude = Math.abs(delta);
  if (magnitude < OK_DELTA_DB) {
    return COLOR_OK;
  }
  if (magnitude < threshold) {
    return COLOR_WARN;
  }
  return COLOR_BAD;
}

/**
 * Return the lowercased extension of a file name, including the dot.
 *
 * @param name File name.
 * @returns Extension such as `.wav`, or an empty string.
 */
export function fileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  return index === -1 ? "" : name.slice(index).toLowerCase();
}

/**
 * Tell whether a file has an extension the backend can analyze.
 *
 * @param file Candidate file.
 * @returns `true` when the extension is supported.
 */
export function isAudioFile(file: File | null | undefined): boolean {
  return !!file && (ACCEPTED_EXTENSIONS as readonly string[]).includes(fileExtension(file.name));
}

/**
 * Format an X-axis frequency tick.
 *
 * @param freq Frequency in Hz.
 * @returns `100`, `1k`, or `10k`.
 */
export function formatFrequencyTick(freq: number): string {
  return freq >= 1000 ? `${freq / 1000}k` : String(freq);
}

/**
 * Find the index of the band whose center frequency is closest to a target.
 *
 * @param bands Objects carrying `freq_hz`.
 * @param freq Target frequency in Hz.
 * @returns Index of the nearest band.
 */
export function nearestBandIndex(bands: ReadonlyArray<{ freq_hz: number }>, freq: number): number {
  let best = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  bands.forEach((band, index) => {
    const distance = Math.abs(band.freq_hz - freq);
    if (distance < bestDistance) {
      best = index;
      bestDistance = distance;
    }
  });
  return best;
}
