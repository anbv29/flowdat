"""Create SignalDesk metadata tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260921_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    json = postgresql.JSONB()
    timestamps = [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]
    op.create_table("users", sa.Column("id", uuid, primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("display_name", sa.String(120), nullable=False), *timestamps)
    op.create_table("datasets", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("name", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("storage_key", sa.String(255), nullable=False, unique=True), sa.Column("media_type", sa.String(120), nullable=False), sa.Column("size_bytes", sa.BigInteger(), nullable=False), sa.Column("row_count", sa.BigInteger(), nullable=False), sa.Column("column_count", sa.Integer(), nullable=False), sa.Column("profile_status", sa.String(32), nullable=False), sa.Column("profile", json, nullable=False), *timestamps)
    op.create_table("dataset_columns", sa.Column("id", uuid, primary_key=True), sa.Column("dataset_id", uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("data_type", sa.String(64), nullable=False), sa.Column("semantic_type", sa.String(32), nullable=False), sa.Column("nullable", sa.Boolean(), nullable=False), sa.Column("null_count", sa.BigInteger(), nullable=False), sa.Column("distinct_count", sa.BigInteger(), nullable=False), sa.Column("statistics", json, nullable=False), sa.Column("sample_values", json, nullable=False))
    op.create_table("conversations", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("dataset_id", uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("business_context", sa.Text()), *timestamps)
    op.create_table("messages", sa.Column("id", uuid, primary_key=True), sa.Column("conversation_id", uuid, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("payload", json), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("query_runs", sa.Column("id", uuid, primary_key=True), sa.Column("conversation_id", uuid, sa.ForeignKey("conversations.id", ondelete="SET NULL")), sa.Column("dataset_id", uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False), sa.Column("user_question", sa.Text(), nullable=False), sa.Column("analysis_plan", json), sa.Column("sql", sa.Text()), sa.Column("validation_outcome", json), sa.Column("execution_status", sa.String(32), nullable=False), sa.Column("execution_time_ms", sa.Float()), sa.Column("row_count", sa.BigInteger()), sa.Column("correction_attempts", json, nullable=False), sa.Column("answer", json), sa.Column("model_identifier", sa.String(120)), sa.Column("prompt_version", sa.String(64)), sa.Column("token_usage", json), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)))
    op.create_table("saved_insights", sa.Column("id", uuid, primary_key=True), sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("dataset_id", uuid, sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False), sa.Column("query_run_id", uuid, sa.ForeignKey("query_runs.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("note", sa.Text()), *timestamps)
    op.create_table("evaluation_cases", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("question", sa.Text(), nullable=False), sa.Column("category", sa.String(64), nullable=False), sa.Column("expected", json, nullable=False), sa.Column("active", sa.Boolean(), nullable=False), *timestamps)
    op.create_table("evaluation_runs", sa.Column("id", uuid, primary_key=True), sa.Column("evaluation_case_id", uuid, sa.ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False), sa.Column("query_run_id", uuid, sa.ForeignKey("query_runs.id", ondelete="SET NULL")), sa.Column("status", sa.String(32), nullable=False), sa.Column("scores", json, nullable=False), sa.Column("latency_ms", sa.Float()), sa.Column("estimated_cost_usd", sa.Float()), sa.Column("failure_reason", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    for table in ["evaluation_runs", "evaluation_cases", "saved_insights", "query_runs", "messages", "conversations", "dataset_columns", "datasets", "users"]:
        op.drop_table(table)
