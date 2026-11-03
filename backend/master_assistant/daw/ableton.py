"""Render DAW-agnostic suggestions as Ableton Live native-device instructions.

Every instruction relies only on devices bundled with Ableton Live 11/12, so the
user can apply it without third-party plugins: Utility, Limiter, EQ Eight, Glue
Compressor, Compressor and Saturator. The adapter never mutates a suggestion and
never talks to Live; it only formats text.

Missing ``action_params`` fall back to documented defaults, which are sensible
starting points rather than measured values:

- ``eq_cut`` / ``eq_boost``: ``q`` defaults to :data:`DEFAULT_Q`.
- ``limiter``: ``ceiling_dbtp`` defaults to -1.0 dB and ``reduction_needed_db``
  to 0.0 dB.
- ``stereo_narrow``: ``below_hz`` defaults to :data:`DEFAULT_BASS_MONO_HZ`.
- ``compressor``: ``target_lra_lu`` defaults to :data:`DEFAULT_TARGET_LRA_LU`.
- ``gain``: ``gain_db`` is mandatory and raises :class:`ValueError` when absent.
  ``eq_cut`` / ``eq_boost`` require ``freq_hz`` and ``gain_db`` for the same
  reason: a bell band without a frequency would render an unusable instruction.

Rendered text is a single line prefixed with ``"Ableton: "`` and carries no
markdown, so it can be pasted into a chat, a note or a CLI log unchanged.
"""

from __future__ import annotations

from master_assistant.daw.base import DawAdapter
from master_assistant.models.schemas import Suggestion

DEFAULT_Q = 1.0
DEFAULT_CEILING_DBTP = -1.0
DEFAULT_REDUCTION_NEEDED_DB = 0.0
DEFAULT_BASS_MONO_HZ = 120.0
DEFAULT_TARGET_LRA_LU = 4.0


class AbletonAdapter(DawAdapter):
    """Render suggestions as Ableton Live native-device instructions."""

    def render(self, suggestion: Suggestion) -> str:
        """Return a one-line Ableton instruction for a suggestion.

        Args:
            suggestion: DAW-agnostic suggestion whose ``action_type`` selects the
                device and whose ``action_params`` supply the numbers.

        Returns:
            A single-line instruction, prefixed with ``"Ableton: "`` and free of
            markdown.

        Raises:
            ValueError: If ``action_type`` is not supported, if a ``gain``
                suggestion omits ``gain_db``, or if an ``eq_cut``/``eq_boost``
                suggestion omits ``freq_hz`` or ``gain_db``.
        """
        action_type = suggestion.action_type
        params = suggestion.action_params

        if action_type == "gain":
            gain_db = self._require(params, "gain_db", action_type)
            return f"Ableton: Utility — Gain: {gain_db:+.1f} dB (prima del limiter)."

        if action_type == "limiter":
            ceiling_dbtp = params.get("ceiling_dbtp", DEFAULT_CEILING_DBTP)
            reduction_needed_db = params.get("reduction_needed_db", DEFAULT_REDUCTION_NEEDED_DB)
            return (
                f"Ableton: Limiter — Ceiling: {ceiling_dbtp:.1f} dB, "
                "poi verifica il True Peak con un meter. "
                f"Riduzione necessaria: {reduction_needed_db:.1f} dB."
            )

        if action_type in {"eq_cut", "eq_boost"}:
            return self._render_eq(params, action_type)

        if action_type == "stereo_narrow":
            below_hz = params.get("below_hz", DEFAULT_BASS_MONO_HZ)
            return f"Ableton: Utility — Bass Mono: On, Frequency = {below_hz:.0f} Hz."

        if action_type == "stereo_widen":
            return "Ableton: Utility — Width: >100% (oppure Mid/Side plugin)."

        if action_type == "compressor":
            target_lra_lu = params.get("target_lra_lu", DEFAULT_TARGET_LRA_LU)
            return (
                "Ableton: Glue Compressor / Compressor — riduci Ratio e/o alza Threshold; "
                f"target LRA {target_lra_lu:.1f} LU. "
                "È un intervento sul mix, non sul master."
            )

        if action_type == "deesser":
            return "Ableton: EQ Eight — High Shelf cut 6–8 kHz (oppure de-esser third-party)."

        if action_type == "saturation":
            return "Ableton: Saturator — Drive basso, Dry/Wet 20–30%."

        raise ValueError(f"Unsupported action_type for Ableton: {action_type}")

    @staticmethod
    def _render_eq(params: dict[str, float], action_type: str) -> str:
        """Render an EQ Eight bell band from frequency, gain, and optional Q.

        Args:
            params: Action parameters holding ``freq_hz`` and ``gain_db``; ``q``
                is optional and defaults to :data:`DEFAULT_Q`.
            action_type: Either ``"eq_cut"`` or ``"eq_boost"``, used only to
                build a precise error message.

        Returns:
            A one-line EQ Eight instruction.

        Raises:
            ValueError: If ``freq_hz`` or ``gain_db`` is missing.
        """
        freq_hz = AbletonAdapter._require(params, "freq_hz", action_type)
        gain_db = AbletonAdapter._require(params, "gain_db", action_type)
        q = params.get("q", DEFAULT_Q)
        return (
            "Ableton: EQ Eight — Band 1: Bell, "
            f"Frequency = {freq_hz:.0f} Hz, Gain = {gain_db:+.1f} dB, Q = {q:.1f}."
        )

    @staticmethod
    def _require(params: dict[str, float], key: str, action_type: str) -> float:
        """Read a mandatory action parameter.

        Args:
            params: ``Suggestion.action_params`` mapping.
            key: Parameter name that must be present.
            action_type: Action type, used only in the error message.

        Returns:
            The parameter value.

        Raises:
            ValueError: If ``key`` is absent from ``params``.
        """
        value = params.get(key)
        if value is None:
            raise ValueError(f"Ableton {action_type} suggestions require '{key}' in action_params.")
        return value
