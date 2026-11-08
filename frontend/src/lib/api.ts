/**
 * Thin client for `POST /analyze`.
 *
 * The request is aborted after {@link REQUEST_TIMEOUT_MS} so an oversized upload
 * or a stuck server cannot leave the UI spinning forever. Failures are classified
 * with an {@link ApiErrorKind} so the UI can localize them.
 */

import type { AnalysisResponse } from "@/types";

/** Abort the upload after this many milliseconds. */
export const REQUEST_TIMEOUT_MS = 60_000;

/**
 * Discriminant describing why an API call failed.
 *
 * The UI maps each kind to a localized message; only `server` carries a
 * backend-provided detail that is displayed verbatim.
 */
export type ApiErrorKind =
  | "timeout"
  | "validation"
  | "network"
  | "unknown"
  | "server";

/**
 * Error carrying an {@link ApiErrorKind} discriminant plus diagnostic text.
 *
 * The `message` is diagnostic only (except for `server` errors, where it holds
 * the backend detail); user-facing strings live in the locale files.
 */
export class ApiError extends Error {
  public readonly kind: ApiErrorKind;

  constructor(kind: ApiErrorKind, message: string) {
    super(message);
    this.kind = kind;
    this.name = "ApiError";
  }
}

export interface AnalyzeFilesArgs {
  userFile: File;
  referenceFile: File;
  daw: string;
}

/**
 * Upload both files and return the analysis payload.
 *
 * @param args Files to analyze plus the target DAW identifier.
 * @returns Parsed `AnalysisResponse`.
 * @throws ApiError With a discriminant describing why the request failed
 * (timeout, validation, network, server, or unknown).
 */
export async function analyzeFiles({
  userFile,
  referenceFile,
  daw,
}: AnalyzeFilesArgs): Promise<AnalysisResponse> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  const formData = new FormData();
  formData.append("user_file", userFile);
  formData.append("reference_file", referenceFile);
  formData.append("daw", daw);

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw await readApiError(response);
    }

    return (await response.json()) as AnalysisResponse;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("timeout", "Request aborted after timeout");
    }
    throw new ApiError("network", String(error));
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/**
 * Map an error response body to a typed {@link ApiError}.
 *
 * @param response Failed response.
 * @returns A `validation` error for a `detail` array, a `server` error carrying
 * the backend `detail` string, or an `unknown` error when the body is not JSON.
 */
async function readApiError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as { detail?: unknown } | null;
    if (payload && payload.detail) {
      if (Array.isArray(payload.detail)) {
        return new ApiError("validation", "Request validation failed");
      }
      return new ApiError("server", String(payload.detail));
    }
  } catch {
    // Non-JSON body: fall through to the generic error.
  }
  return new ApiError("unknown", `Unexpected ${response.status} response`);
}
