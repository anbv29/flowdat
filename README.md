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

Setup and operating instructions will be expanded alongside the working vertical slices.
