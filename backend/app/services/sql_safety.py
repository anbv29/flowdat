import re
from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from app.core.errors import AppError

COMMENT_PATTERN = re.compile(r"--|/\*|\*/")
FILESYSTEM_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_parquet",
    "glob",
    "parquet_scan",
    "csv_scan",
    "sqlite_scan",
    "postgres_scan",
    "httpfs",
}
FORBIDDEN_EXPRESSIONS = tuple(
    expression
    for name in (
        "Insert",
        "Update",
        "Delete",
        "Drop",
        "Alter",
        "Create",
        "Command",
        "Copy",
        "Merge",
        "Transaction",
        "Attach",
    )
    if (expression := getattr(exp, name, None)) is not None
)


@dataclass(frozen=True)
class ValidatedSQL:
    sql: str
    limit_applied: bool
    max_rows: int


class SQLSafetyService:
    def __init__(self, allowed_table: str, allowed_columns: set[str], max_rows: int = 500) -> None:
        self.allowed_table = allowed_table.lower()
        self.allowed_columns = {column.lower() for column in allowed_columns}
        self.max_rows = max_rows

    def validate(self, sql: str) -> ValidatedSQL:
        candidate = sql.strip()
        if not candidate:
            raise self._error("empty_sql", "No query was generated.")
        if COMMENT_PATTERN.search(candidate):
            raise self._error(
                "sql_comments_rejected",
                "Comments are not permitted in generated queries.",
            )

        try:
            statements = parse(candidate, read="duckdb")
        except ParseError as exc:
            raise self._error(
                "invalid_sql",
                "The generated query could not be parsed safely.",
            ) from exc
        if len(statements) != 1:
            raise self._error(
                "multiple_statements",
                "Only one read-only query can run at a time.",
            )

        statement = statements[0]
        if not isinstance(statement, exp.Query) or statement.find(FORBIDDEN_EXPRESSIONS):
            raise self._error(
                "statement_not_allowed",
                "Only read-only SELECT queries are permitted.",
            )
        self._validate_functions(statement)
        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        self._validate_tables(statement, cte_names)
        self._validate_columns(statement)

        limit_applied = self._enforce_limit(statement)
        return ValidatedSQL(
            sql=statement.sql(dialect="duckdb", pretty=True),
            limit_applied=limit_applied,
            max_rows=self.max_rows,
        )

    def _validate_functions(self, statement: exp.Expression) -> None:
        for function in statement.find_all(exp.Func):
            name = (
                function.name.lower()
                if isinstance(function, exp.Anonymous)
                else function.sql_name().lower()
            )
            if name in FILESYSTEM_FUNCTIONS:
                raise self._error(
                    "filesystem_access_rejected",
                    "Queries cannot read files or external data sources.",
                )

    def _validate_tables(self, statement: exp.Expression, cte_names: set[str]) -> None:
        tables = {table.name.lower() for table in statement.find_all(exp.Table)}
        unknown = sorted(tables - {self.allowed_table} - cte_names)
        if unknown:
            raise self._error(
                "unknown_tables",
                "The query refers to data outside the selected dataset.",
                {"tables": unknown},
            )

    def _validate_columns(self, statement: exp.Expression) -> None:
        derived_names = {
            alias.alias.lower() for alias in statement.find_all(exp.Alias) if alias.alias
        }
        unknown = sorted(
            {
                column.name
                for column in statement.find_all(exp.Column)
                if column.name != "*"
                and column.name.lower() not in self.allowed_columns
                and column.name.lower() not in derived_names
            }
        )
        if unknown:
            raise self._error(
                "unknown_columns",
                "The query refers to fields that are not in the selected dataset.",
                {"columns": unknown},
            )

    def _enforce_limit(self, statement: exp.Query) -> bool:
        limit = statement.args.get("limit")
        if limit is None:
            statement.limit(self.max_rows, copy=False)
            return True
        expression = limit.expression
        try:
            requested = int(expression.name)
        except (AttributeError, TypeError, ValueError):
            statement.limit(self.max_rows, copy=False)
            return True
        if requested > self.max_rows:
            statement.limit(self.max_rows, copy=False)
            return True
        return False

    @staticmethod
    def _error(code: str, message: str, details: dict | None = None) -> AppError:
        return AppError(code, message, details=details)
