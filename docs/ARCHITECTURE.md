# Architecture

SignalDesk separates application metadata, uploaded rows, and model context on purpose.

## Request flow

1. The Next.js client uploads a file to FastAPI.
2. The API streams it to a generated storage key and asks DuckDB to create an isolated local database.
3. Compact profile records go to PostgreSQL; source rows stay in the uploaded file and DuckDB database.
4. A question and limited conversation context are combined with the dataset profile.
5. The planning provider returns a strict Pydantic `AnalysisPlan`.
6. If the plan is sufficiently clear, the SQL provider returns DuckDB SQL.
7. SQLGlot parses and validates that SQL against the one allowed table and its known columns.
8. The API runs the query with a timer, verifies its result, and builds the final answer from returned values.
9. The query run, validation outcome, attempts, usage, and answer are stored for history and export.

The language model never receives the complete dataset and never executes code.

## Service boundaries

`frontend` owns interaction state and presentation. It does not generate SQL or infer analytical results.

`backend/app/api` defines HTTP contracts and transaction boundaries. `backend/app/services` contains upload, profiling, planning, generation, safety, execution, verification, answer, chart, and evaluation logic.

PostgreSQL stores durable workspace metadata. DuckDB performs analytical work against a per-dataset database. This keeps large tabular rows out of the transactional database while preserving a useful audit trail.

## Provider behavior

Both AI stages have interfaces with OpenAI and deterministic implementations. An empty `OPENAI_API_KEY` selects the fallback. Provider responses are validated before any downstream step. SQL is treated as untrusted regardless of provider.

The fallback makes local development and tests useful without pretending to cover arbitrary language. The interface always labels which mode produced the result.

## Persistence

The `postgres_data` Docker volume holds application metadata. The `uploads` volume holds source files and DuckDB databases. Removing containers keeps both volumes; `docker compose down -v` removes them.

## Scaling notes

The current synchronous execution path is simple and observable. A multi-user deployment should add authenticated ownership checks, object storage, background evaluation jobs, quotas, centralized logs, and per-tenant encryption keys before exposure to untrusted users.
