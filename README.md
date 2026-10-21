# Master Assistant

Master Assistant analyzes an unmastered track against a reference master and produces
DAW-specific mastering suggestions.

This repository currently contains the project scaffolding only: the API is live, while
the analysis, suggestion, and DAW modules are placeholders that define the intended
boundaries.

## Requirements

- Python 3.11 or newer

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `python3.11` is not on your `PATH`, point the first command at any Python 3.11+
interpreter instead (for example `/usr/local/bin/python3.11`).

## Run the API

```bash
uvicorn master_assistant.api.main:app --reload
```

The health endpoint is available at <http://127.0.0.1:8000/health> and returns:

```json
{"status": "ok"}
```

## Run the tests

```bash
pytest
```

## Project layout

```text
backend/master_assistant/
├── analysis/       # Loudness, spectrum, stereo, and transient measurements
├── api/            # FastAPI application and HTTP endpoints
├── daw/            # DAW adapter interfaces
├── models/         # Pydantic schemas shared across modules
└── suggestions/    # Rule engine translating measurements into suggestions
tests/              # Pytest suite
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities and project conventions.
