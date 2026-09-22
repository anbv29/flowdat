import json
from pathlib import Path


def test_benchmark_has_required_coverage() -> None:
    path = Path(__file__).parents[1] / "data" / "evaluation_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    categories = {item["category"] for item in cases}
    assert len(cases) >= 20
    assert {
        "simple_aggregation",
        "grouped_comparison",
        "time_series",
        "percentage_change",
        "ranking",
        "ambiguous",
        "impossible",
        "unknown_column",
        "unsafe_sql",
    } <= categories
    assert len({item["name"] for item in cases}) == len(cases)
