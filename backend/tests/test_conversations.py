from app.api.conversations import conversation_title


def test_conversation_title_compacts_whitespace() -> None:
    assert conversation_title("  Revenue   by region?  ") == "Revenue by region?"


def test_conversation_title_is_bounded() -> None:
    title = conversation_title("A very long question " * 10)
    assert len(title) == 62
    assert title.endswith("…")
