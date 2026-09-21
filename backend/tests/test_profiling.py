from pathlib import Path

from app.services.profiling import profile_dataset


def test_profiles_csv_columns_and_statistics(tmp_path: Path) -> None:
    source = tmp_path / "orders.csv"
    source.write_text("order_id,amount,ordered_at,region\n1,10,2026-01-01,North\n2,20,2026-01-02,South\n3,,2026-01-03,North\n")

    profile = profile_dataset(source)

    assert profile["row_count"] == 3
    assert profile["column_count"] == 4
    amount = next(column for column in profile["columns"] if column["name"] == "amount")
    assert amount["null_count"] == 1
    assert amount["statistics"]["median"] == 15
