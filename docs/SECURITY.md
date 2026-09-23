# Security model

SignalDesk assumes generated SQL and uploaded filenames are hostile input.

## Upload controls

- Only CSV and Parquet extensions are accepted.
- The declared media type must match the extension allowlist.
- Files are streamed in fixed-size chunks and stopped at the configured byte limit.
- The supplied name is reduced to display metadata. Storage uses a random internal key.
- Resolved storage paths are checked to remain inside the configured upload directory.
- Partial and empty files are removed.

These checks do not replace malware scanning. Add scanning and file quarantine before accepting files from untrusted public users.

## Model boundary

Only the dataset description, schema, compact statistics, representative values, business context, and relevant conversation context reach the model. Source rows are not included wholesale. Provider output passes through Pydantic validation, then SQL validation; neither stage grants execution authority.

## SQL controls

The SQL safety service parses with SQLGlot, rejects multiple statements and comments, accepts only read-only query forms, blocks filesystem and extension operations, enforces table and column allowlists, and caps result size. DuckDB execution runs against the current dataset database in read-only mode with an interrupt timer.

Rejected and failed queries retain a user-safe code and message in history. Raw database errors are not sent to the browser.

## Result controls

Verification rejects empty or malformed results, non-finite numbers, missing planned fields, invalid percentage calculations, and unavailable date ranges. A warning is attached when record filters retain an unusually small share of the source. Only one correction is allowed, and both attempts are recorded.

CSV export prefixes spreadsheet formula characters to prevent formula injection when a result is opened in desktop spreadsheet software.

## Deployment boundary

The included Compose file is for local development. It uses known local database credentials and exposes ports on the host. Before a shared deployment, provide secrets through a managed store, terminate TLS, restrict origins, add authentication and authorization, set resource limits, scan uploads, and disable development API documentation where appropriate.
