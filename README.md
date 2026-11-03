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

Once the frontend has been built (see below), the UI is served from the same
origin at <http://127.0.0.1:8000/>.

## Frontend (dev)

The UI is a Vite + React + TypeScript single page app in `frontend/`, styled with
Tailwind CSS and shadcn/ui, with charts rendered by Recharts. It needs Node.js
20.19+ (or 22.12+).

```bash
cd frontend
npm install          # first run only
npm run dev          # dev server on :5173, proxies /analyze and /health to :8000
```

In another shell, from the repository root:

```bash
.venv/bin/uvicorn master_assistant.api.main:app --reload --port 8000
```

Then open <http://127.0.0.1:5173/>: hot reload applies to the React sources while
API calls are forwarded to uvicorn, so `POST /analyze` works without CORS setup.

## Frontend (build)

```bash
cd frontend
npm run build        # output lands in backend/master_assistant/api/static/
cd ..
.venv/bin/uvicorn master_assistant.api.main:app --port 8000
# open http://127.0.0.1:8000/
```

The build empties `backend/master_assistant/api/static/` first and writes
`index.html` plus hashed files under `assets/`. FastAPI mounts that directory at
`/`, so a single origin serves both the UI and the API.

## Run the tests

```bash
pytest
```

## Project layout

```text
backend/master_assistant/
├── analysis/       # Loudness, spectrum, stereo, and transient measurements
├── api/            # FastAPI application, HTTP endpoints, and the built UI
├── daw/            # DAW adapter interfaces
├── models/         # Pydantic schemas shared across modules
└── suggestions/    # Rule engine translating measurements into suggestions
frontend/           # Vite + React + TypeScript sources (build target: api/static/)
tests/              # Pytest suite
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for module responsibilities and project conventions.
