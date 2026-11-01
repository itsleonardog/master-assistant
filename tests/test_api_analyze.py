"""End-to-end tests for ``POST /analyze``.

The tests drive the real FastAPI app through ``TestClient`` with in-memory WAV
uploads, so they cover the multipart parsing, the temporary-file lifecycle, the
analysis stack, the rule engine, and the Ableton adapter in one pass.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from httpx import Response

from _fixtures import _mono_noise, _stereo_noise, _wav_bytes
from master_assistant.api import main as api_main
from master_assistant.api.main import app

DURATION_S = 6.0


def _post_analyze(user: bytes | None, reference: bytes | None, daw: str = "ableton") -> Response:
    """Post a multipart analysis request, omitting the files that are ``None``.

    Args:
        user: Raw WAV bytes of the unmastered track, or ``None`` to omit it.
        reference: Raw WAV bytes of the reference master, or ``None`` to omit it.
        daw: Target DAW identifier.

    Returns:
        The HTTP response returned by the endpoint.
    """
    files: dict[str, tuple[str, bytes, str]] = {}
    if user is not None:
        files["user_file"] = ("user.wav", user, "audio/wav")
    if reference is not None:
        files["reference_file"] = ("reference.wav", reference, "audio/wav")

    with TestClient(app) as client:
        if files:
            return client.post("/analyze", files=files, data={"daw": daw})
        return client.post("/analyze", data={"daw": daw})


def test_identical_files_return_no_suggestions() -> None:
    """Two identical stereo uploads must return a full report and no advice."""
    audio = _wav_bytes(_stereo_noise(DURATION_S, seed=1))

    response = _post_analyze(audio, audio)

    assert response.status_code == 200
    payload = response.json()
    assert payload["daw"] == "ableton"
    assert payload["suggestions"] == []
    assert payload["rendered_suggestions"] == []
    report = payload["report"]
    assert set(report) == {
        "user_loudness",
        "reference_loudness",
        "loudness_delta",
        "spectrum",
        "stereo",
        "warnings",
    }
    assert report["loudness_delta"]["integrated_lufs_delta"] == pytest.approx(0.0, abs=1e-9)
    assert report["stereo"] is not None
    assert report["warnings"] == []


def test_gain_difference_renders_ableton_instruction() -> None:
    """A +6 dB user upload must yield advice rendered for Ableton."""
    reference = _stereo_noise(DURATION_S, seed=2)

    response = _post_analyze(_wav_bytes(reference * 10.0 ** (6.0 / 20.0)), _wav_bytes(reference))

    assert response.status_code == 200
    payload = response.json()
    assert payload["report"]["loudness_delta"]["integrated_lufs_delta"] == pytest.approx(
        6.0, abs=0.5
    )
    assert len(payload["suggestions"]) >= 1
    assert any(suggestion["action_type"] == "gain" for suggestion in payload["suggestions"])
    assert any(text.startswith("Ableton: ") for text in payload["rendered_suggestions"])
    assert len(payload["rendered_suggestions"]) == len(payload["suggestions"])


def test_mono_user_skips_stereo_with_warning() -> None:
    """A mono upload against a stereo reference must return no stereo report."""
    response = _post_analyze(
        _wav_bytes(_mono_noise(DURATION_S, seed=3)),
        _wav_bytes(_stereo_noise(DURATION_S, seed=4)),
    )

    assert response.status_code == 200
    report = response.json()["report"]
    assert report["stereo"] is None
    assert report["warnings"]


def test_corrupt_user_file_returns_400() -> None:
    """Bytes that are not audio must map to a 400 that mentions reading the file."""
    reference = _wav_bytes(_stereo_noise(DURATION_S, seed=5))

    response = _post_analyze(b"this is definitely not audio" * 200, reference)

    assert response.status_code == 400
    assert "read" in response.json()["detail"].lower()


def test_unsupported_daw_returns_400() -> None:
    """Only ``ableton`` is supported; other identifiers must be rejected."""
    audio = _wav_bytes(_stereo_noise(DURATION_S, seed=6))

    response = _post_analyze(audio, audio, daw="fl_studio")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Unsupported DAW" in detail
    assert "fl_studio" in detail


def test_missing_user_file_returns_422() -> None:
    """The user upload is required, so FastAPI validation must reject the request."""
    reference = _wav_bytes(_stereo_noise(DURATION_S, seed=7))

    response = _post_analyze(None, reference)

    assert response.status_code == 422


def test_failed_request_leaves_endpoint_usable() -> None:
    """A 400 caused by an unreadable user file must not break later requests.

    This is the practical consequence of the ``finally`` cleanup: the reference
    temp file of the failed request is removed, and nothing leaks into the next
    call. The test asserts the observable behavior rather than the temp directory
    contents, which are covered directly by
    :func:`test_temp_files_are_removed_when_analysis_fails`.
    """
    reference = _wav_bytes(_stereo_noise(DURATION_S, seed=8))

    failed = _post_analyze(b"garbage" * 500, reference)
    succeeded = _post_analyze(reference, reference)

    assert failed.status_code == 400
    assert succeeded.status_code == 200
    assert succeeded.json()["suggestions"] == []


def test_temp_files_are_removed_when_analysis_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure inside the analysis must still delete both temporary files."""
    recorded: list[Path] = []
    original_save = api_main._save_upload_to_temp

    async def save_and_record(upload: UploadFile, suffix: str) -> Path:
        path = await original_save(upload, suffix)
        recorded.append(path)
        return path

    def fail_analysis(user_path: Path, reference_path: Path) -> None:
        raise ValueError("boom")

    monkeypatch.setattr(api_main, "_save_upload_to_temp", save_and_record)
    monkeypatch.setattr(api_main, "analyze_pair", fail_analysis)
    audio = _wav_bytes(_stereo_noise(DURATION_S, seed=9))

    response = _post_analyze(audio, audio)

    assert response.status_code == 400
    assert response.json()["detail"] == "boom"
    assert len(recorded) == 2
    assert all(not path.exists() for path in recorded)


def test_oversized_upload_returns_413(monkeypatch: pytest.MonkeyPatch) -> None:
    """The size guard must reject an upload above the configured limit."""
    monkeypatch.setattr(api_main, "MAX_FILE_SIZE_MB", 0)
    audio = _wav_bytes(_stereo_noise(DURATION_S, seed=10))

    response = _post_analyze(audio, audio)

    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]
