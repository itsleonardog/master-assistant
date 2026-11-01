"""FastAPI application exposing the Master Assistant API.

``POST /analyze`` orchestrates the analysis, rule-engine, and DAW adapter layers
for two uploaded audio files. It adds no signal processing and no DAW-specific
logic of its own: it only validates the target DAW, streams the uploads to
temporary files, calls :func:`analyze_pair` and :func:`generate_suggestions`, and
renders the result through the requested :class:`DawAdapter`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from master_assistant.analysis.comparison import analyze_pair
from master_assistant.analysis.errors import AudioReadError
from master_assistant.daw.ableton import AbletonAdapter
from master_assistant.daw.base import DawAdapter
from master_assistant.models.schemas import AnalysisResponse, HealthResponse
from master_assistant.suggestions.rule_engine import generate_suggestions

MAX_FILE_SIZE_MB = 200
SUPPORTED_DAWS = ("ableton",)
_UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
_TEMP_SUFFIX = ".wav"
_STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Master Assistant", version="0.1.0")


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return service liveness status."""
    return HealthResponse(status="ok")


@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
async def analyze(
    user_file: Annotated[UploadFile, File(description="Traccia non masterizzata")],
    reference_file: Annotated[UploadFile, File(description="Traccia di riferimento")],
    daw: Annotated[str, Form(description="DAW di destinazione")] = "ableton",
) -> AnalysisResponse:
    """Analyze an unmastered upload against a reference master.

    Both uploads are copied to temporary files, analyzed, and deleted before the
    response leaves the endpoint, whatever the outcome: no audio is retained
    beyond the request lifetime.

    Args:
        user_file: Multipart upload of the unmastered track.
        reference_file: Multipart upload of the reference master.
        daw: Target DAW identifier; only ``"ableton"`` is supported.

    Returns:
        AnalysisResponse with the comparison report, the DAW-agnostic
        suggestions, the same suggestions rendered for ``daw`` in the same
        order, and the echoed DAW identifier.

    Raises:
        HTTPException: 400 when the DAW is unsupported or an upload cannot be
            read or rendered, and 413 when an upload exceeds
            :data:`MAX_FILE_SIZE_MB`.
    """
    adapter = _get_adapter(daw)
    temp_paths: list[Path] = []
    try:
        user_path = await _save_upload_to_temp(user_file, suffix=_TEMP_SUFFIX)
        temp_paths.append(user_path)
        reference_path = await _save_upload_to_temp(reference_file, suffix=_TEMP_SUFFIX)
        temp_paths.append(reference_path)

        report = analyze_pair(user_path, reference_path)
        suggestions = generate_suggestions(report)
        return AnalysisResponse(
            report=report,
            suggestions=suggestions,
            rendered_suggestions=[adapter.render(suggestion) for suggestion in suggestions],
            daw=daw,
        )
    except AudioReadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for path in temp_paths:
            path.unlink(missing_ok=True)


def _get_adapter(daw: str) -> DawAdapter:
    """Return the DAW adapter registered for a DAW identifier.

    Args:
        daw: Target DAW identifier, for example ``"ableton"``.

    Returns:
        The adapter that renders suggestions for ``daw``.

    Raises:
        HTTPException: With status 400 when ``daw`` is not supported.
    """
    if daw == "ableton":
        return AbletonAdapter()
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported DAW: {daw}. Supported: {list(SUPPORTED_DAWS)}",
    )


async def _save_upload_to_temp(upload: UploadFile, suffix: str) -> Path:
    """Copy an upload to a named temporary file while enforcing the size limit.

    The upload is read in :data:`_UPLOAD_CHUNK_SIZE_BYTES` chunks so an oversized
    file never has to be held in memory as a whole.

    Args:
        upload: Multipart upload to persist.
        suffix: Suffix for the temporary file name, for example ``".wav"``.

    Returns:
        Path of the temporary file holding the upload bytes. The caller owns it
        and must delete it.

    Raises:
        HTTPException: With status 413 when the upload exceeds
            :data:`MAX_FILE_SIZE_MB`. The partially written file is removed
            before raising.
    """
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(temp.name)
    total_bytes = 0
    try:
        with temp:
            while chunk := await upload.read(_UPLOAD_CHUNK_SIZE_BYTES):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (max {MAX_FILE_SIZE_MB} MB)",
                    )
                temp.write(chunk)
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    return path


# The static mount and the root redirect are registered last on purpose: FastAPI
# matches routes in registration order, so a mount declared here cannot shadow
# ``/health``, ``/analyze``, or the generated ``/docs`` endpoints.
app.mount("/app", StaticFiles(directory=_STATIC_DIR, html=True), name="app")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect to the UI."""
    return RedirectResponse(url="/app/")
