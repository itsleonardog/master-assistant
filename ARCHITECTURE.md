# Architecture

Master Assistant compares an unmastered track with a reference master, derives measurable
differences, and translates them into actionable, DAW-specific mastering advice.

## Data flow

```text
target audio ──┐
               ├──> analysis metrics ──> rule engine ──> suggestions ──> DAW adapter
reference audio ┘
```

Audio analysis is kept separate from decision-making and presentation. The API orchestrates
these layers; it does not implement analysis or DAW-specific behavior itself.

## Module map

| Module | Responsibility |
| --- | --- |
| `master_assistant.analysis.loudness` | Measures integrated LUFS, true peak, and loudness range. |
| `master_assistant.analysis.spectrum` | Profiles spectral balance and tonal differences against the reference. |
| `master_assistant.analysis.stereo` | Measures stereo width, correlation, and mid/side balance. |
| `master_assistant.analysis.transients` | Characterizes attack, punch, and crest factor. |
| `master_assistant.suggestions.rule_engine` | Converts analysis deltas and reference targets into prioritized suggestions. |
| `master_assistant.daw.base` | Defines the `DawAdapter` interface for DAW-specific instruction export. |
| `master_assistant.api.main` | Creates the FastAPI app and exposes HTTP endpoints such as `/health`. |
| `master_assistant.models.schemas` | Holds Pydantic models for requests, metrics, and suggestions. |
| `tests/` | Pytest suite covering the API and, later, the analysis and rule-engine layers. |

The analysis, rule-engine, and DAW modules are intentionally empty scaffolds at this stage.

## Conventions

- **Python 3.11+** is required. Use modern syntax such as `X | None` and built-in generics.
- **Type hints everywhere**, including return types. Add `from __future__ import annotations`
  to modules that benefit from deferred evaluation.
- **Ruff** is the formatter and linter baseline: line length 100, target Python 3.11,
  rules `E`, `F`, `I`, `UP`, and `B`.
- **Pure analysis functions**: accept explicit inputs (paths or NumPy arrays) and return
  typed result objects; avoid global state and file-system side effects outside I/O helpers.
- **Boundaries use Pydantic**: define request and response models in
  `master_assistant/models/schemas.py` rather than passing untyped dictionaries through layers.
- **DAW isolation**: DAW-specific logic belongs in adapters implementing `DawAdapter`; core
  analysis and the rule engine must remain DAW-agnostic.
- **Minimal dependencies**: do not add packages beyond those declared in `pyproject.toml`
  without updating the dependency list and this document.
- **Tests live in `tests/`** and run with `pytest`; every new public behavior should have at
  least one focused test.
- **Docstrings** describe each module's responsibility and any non-obvious units or ranges.
