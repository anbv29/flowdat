# API reference

The default base URL is `http://localhost:8000/api/v1`. FastAPI publishes an interactive OpenAPI document at `/docs` outside production mode.

Errors use one stable envelope:

```json
{
  "error": {
    "code": "unknown_columns",
    "message": "The generated query references columns outside this dataset.",
    "details": {}
  }
}
```

## System

- `GET /health` — service readiness

## Datasets

- `POST /datasets` — multipart CSV or Parquet upload and profiling
- `POST /datasets/sample` — copy and profile the bundled ecommerce sample
- `GET /datasets` — recent datasets
- `GET /datasets/{dataset_id}` — profile, columns, and safe preview rows
- `DELETE /datasets/{dataset_id}` — remove metadata and local files

## Conversations and planning

- `POST /conversations` — create a conversation for one dataset
- `GET /conversations?dataset_id=...` — list dataset conversations
- `GET /conversations/{conversation_id}/messages` — retrieve messages
- `POST /conversations/{conversation_id}/messages` — add a user question
- `POST /conversations/{conversation_id}/plans` — create a validated analysis plan and query run

## Execution and history

- `POST /query-runs/{query_run_id}/execute` — validate, run, verify, and answer
- `GET /query-runs` — list recent runs; accepts `dataset_id` and `limit`
- `GET /query-runs/{query_run_id}/export` — export completed result rows as CSV

Plan creation can return `clarification_needed: true`. In that case the caller should present `clarification_question` rather than execute the run.

## Insights

- `POST /insights` — save a completed query run with a title and optional note
- `GET /insights` — list saved insights
- `DELETE /insights/{insight_id}` — remove an insight

## Evaluations

- `POST /evaluations/run?dataset_id=...` — run active benchmark cases against a ready dataset
- `GET /evaluations/summary` — latest score per case and failed-case detail

Evaluation cost remains zero unless input and output rates are configured. This avoids embedding pricing assumptions in application code.
