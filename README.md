# SignalDesk

SignalDesk is a local analytics workspace for CSV and Parquet files. It profiles a dataset, turns a plain-language question into a typed analysis plan, generates guarded DuckDB SQL, and returns a written answer with evidence, a table, a suitable chart, assumptions, and the exact query that ran.

The interface is deliberately quiet: warm neutrals, compact controls, one muted accent, and glass surfaces used for structure rather than decoration.

## What is included

- A dataset library with secure upload and a one-click ecommerce sample
- Column profiling for types, completeness, cardinality, numeric summaries, date ranges, and representative values
- A three-panel analysis workspace with conversation history and responsive mobile tabs
- A two-stage analysis pipeline: validated plan first, SQL generation second
- OpenAI Responses API support behind provider interfaces, with a clearly labelled deterministic fallback
- SQLGlot validation, schema allowlists, row limits, timeouts, result verification, and one correction attempt
- Line, bar, donut, histogram, scatter, KPI, and table presentation rules
- Query history, saved insights, CSV export, and dataset deletion
- A 24-case ecommerce benchmark and an evaluation dashboard
- PostgreSQL migrations, Docker Compose, backend/frontend unit tests, and a Playwright journey

## Quick start

Docker Desktop is the shortest route to the complete application:

```powershell
docker compose up --build -d
docker compose ps
```

Open [http://localhost:3000](http://localhost:3000). The API health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health), and interactive API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

The backend applies migrations and seeds the evaluation cases when its container starts. An API key is optional; without one, the workspace shows `Local fallback` and uses the deterministic planner and SQL generator.

To stop the stack:

```powershell
docker compose down
```

Use `docker compose down -v` only when you intentionally want to remove the local database and uploaded-file volumes.

## Configuration

The checked-in examples describe every application setting:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env.local
```

For Docker Compose, set optional values in a root `.env` file or edit the compose environment. The most useful settings are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | empty | Enables the OpenAI provider |
| `OPENAI_MODEL` | `gpt-6-astra` | Model used by both provider stages |
| `MAX_UPLOAD_MB` | `100` | Streamed upload limit |
| `MAX_RESULT_ROWS` | `500` | Maximum returned rows |
| `QUERY_TIMEOUT_SECONDS` | `10` | DuckDB execution timeout |
| `MODEL_INPUT_COST_PER_MILLION_USD` | `0` | Optional evaluation cost estimate |
| `MODEL_OUTPUT_COST_PER_MILLION_USD` | `0` | Optional evaluation cost estimate |

Cost fields default to zero because model pricing changes. Set the rates that apply to your account when you want evaluation cost estimates.

## Run without containers

Start PostgreSQL and create a `signaldesk` database, then prepare the API:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In another terminal:

```powershell
npm install
npm run dev
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` and use `cp` instead of `Copy-Item`.

## Checks

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m pytest tests

cd ..
npm run lint
npm run test
npm run build
npm run test:e2e
```

The Playwright journey expects the Docker stack (or equivalent local services) to be running. Install its browser once with `npm exec playwright install chromium`.

## Product walkthrough

1. Open **Datasets** and upload a CSV or Parquet file, or choose **Explore sample data**.
2. Review the profile and data preview. The original file remains local and only compact metadata is available to the planner.
3. Choose **Ask a question**. SignalDesk records a structured plan before generating SQL.
4. Read the verified answer in the centre panel; inspect filters, assumptions, and generated SQL in the context panel.
5. Export result rows, save an insight, or continue with a suggested follow-up.
6. Use **History** for the audit trail and **Evaluations** to run the benchmark against a ready dataset.

## Repository map

```text
backend/                 FastAPI, SQLAlchemy, DuckDB, SQLGlot, providers, tests
backend/data/            Ecommerce sample and evaluation benchmark
backend/migrations/      Alembic metadata migration
frontend/                Next.js App Router interface and component tests
frontend/e2e/            Playwright revenue journey
docs/                    Architecture, security, and API notes
docker-compose.yml       PostgreSQL, API, and web application
```

The deeper design notes live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md), and [docs/API.md](docs/API.md).

## Current boundaries

SignalDesk is a single-workspace local application. The schema includes users, but authentication and tenant isolation are not wired into this build. The deterministic fallback intentionally handles a smaller set of analytical phrasing than the OpenAI provider. Evaluation runs are synchronous, which is appropriate for the bundled benchmark but should move to a worker queue before running large suites for multiple users.
