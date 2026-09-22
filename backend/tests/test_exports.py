from app.api.query_runs import safe_csv_value


def test_csv_export_escapes_spreadsheet_formulas() -> None:
    assert safe_csv_value("=HYPERLINK('bad')") == "'=HYPERLINK('bad')"
    assert safe_csv_value("normal text") == "normal text"
    assert safe_csv_value(42) == 42
