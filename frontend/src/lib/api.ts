/**
 * Thin client for `POST /analyze`.
 *
 * The request is aborted after {@link REQUEST_TIMEOUT_MS} so an oversized upload
 * or a stuck server cannot leave the UI spinning forever. Error messages mirror
 * the wording of the legacy `app.js` controller.
 */

import type { AnalysisResponse } from "@/types";

/** Abort the upload after this many milliseconds. */
export const REQUEST_TIMEOUT_MS = 60_000;

/** Message shown when the abort controller fires. */
export const TIMEOUT_MESSAGE = "Timeout: il file è troppo grande o il server non risponde";

/** Message shown for a Pydantic 422 validation error. */
export const VALIDATION_MESSAGE = "Compila tutti i campi richiesti.";

/** Message shown when the server returns an unparseable error body. */
export const UNKNOWN_ERROR_MESSAGE = "Errore sconosciuto";

/** Error carrying a user-facing message. */
export class ApiError extends Error {
  constructor(message: string) {
    super(message);
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
 * @throws ApiError With a user-facing message for timeouts, network failures,
 * and non-2xx responses.
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
      throw new ApiError(await readErrorMessage(response));
    }

    return (await response.json()) as AnalysisResponse;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError(TIMEOUT_MESSAGE);
    }
    throw new ApiError(`Impossibile contattare il server: ${String(error)}`);
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/**
 * Map an error response body to a user-facing message.
 *
 * @param response Failed response.
 * @returns The `detail` string, the validation message for a `detail` array, or
 * a generic fallback when the body is not JSON.
 */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown } | null;
    if (payload && payload.detail) {
      return Array.isArray(payload.detail) ? VALIDATION_MESSAGE : String(payload.detail);
    }
  } catch {
    // Non-JSON body: fall through to the generic message.
  }
  return UNKNOWN_ERROR_MESSAGE;
}
