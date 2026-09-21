# SignalDesk

SignalDesk is a focused workspace for exploring tabular data. Upload a CSV or Parquet file, review its shape and quality, then ask practical questions and inspect the SQL behind each answer.

The application is being built in working slices. The first slice covers secure upload, profiling, and dataset preview; analysis planning and guarded query execution follow next.

## Repository layout

```text
frontend/   Next.js application
backend/    FastAPI service and data pipeline
```

## Product principles

- Answers should be traceable to returned rows and generated SQL.
- Uploaded data stays outside model prompts; only schema and compact statistics are shared.
- Ambiguity is visible. Small uncertainties become assumptions, while material ones become one concise question.
- The interface favours calm density over dashboard clutter.

## What works now

- CSV and Parquet upload with extension, media-type, and size validation
- Generated storage names that never reuse a supplied filename as a path
- DuckDB-backed profiling for types, nulls, distinct values, numeric summaries, date ranges, and samples
- PostgreSQL metadata models and an initial Alembic migration
- Dataset listing, profile retrieval, deletion, and a one-click ecommerce sample
- A responsive dataset library with visible upload, profiling, empty, and error states

## Run with Docker

Docker Compose is the shortest route to a complete local environment:

```bash
docker compose up --build
```

Open `http://localhost:3000`. The API reference is available at `http://localhost:8000/docs` in development.

## Run the services separately

Start PostgreSQL, then prepare the API from `backend`:

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` instead. Copy `backend/.env.example` to `backend/.env` before changing database or upload settings.

In another terminal, prepare the interface:

```bash
npm install
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env.local` if the API does not run on port 8000.

## Checks

```bash
cd backend && pytest && ruff check .
npm run lint
npm run test
npm run build
```

## Architecture notes

Uploaded files are streamed to a generated key inside the configured upload directory. DuckDB reads the stored file and creates an isolated local table used for profiling and, in later slices, guarded analysis. PostgreSQL holds application metadata and compact profiles; it does not hold the source rows. The browser speaks only to the FastAPI contract and never constructs database queries.

The language-model layer is deliberately absent from this first slice. The next slice will introduce a provider interface and strictly validated analysis plans before any SQL generation is connected.

## Security boundary

The original filename is retained only as display metadata. It is stripped to its basename and never used to construct a storage path. Uploads are limited by extension, media type, and streamed byte count. Generated SQL will be treated as untrusted input and checked independently before DuckDB sees it.
