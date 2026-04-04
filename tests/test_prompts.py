"""Tests for rozkoduj_mcp.prompts."""

from rozkoduj_mcp.prompts import deep_dive, find_opportunities, morning_briefing


class TestPrompts:
    def test_morning_briefing_returns_messages(self) -> None:
        messages = morning_briefing()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert "market_pulse" in messages[0].content.text  # type: ignore[union-attr]
        assert "movers" in messages[0].content.text  # type: ignore[union-attr]
        assert "calendar" in messages[0].content.text  # type: ignore[union-attr]

    def test_deep_dive_includes_symbol(self) -> None:
        messages = deep_dive("AAPL")
        assert len(messages) == 1
        assert messages[0].role == "user"
        text = messages[0].content.text  # type: ignore[union-attr]
        assert "AAPL" in text
        assert "score" in text
        assert "analyze" in text
        assert "fundamentals" in text
        assert "buzz" in text
        assert "multitf" in text

    def test_find_opportunities_default_market(self) -> None:
        messages = find_opportunities()
        assert len(messages) == 1
        text = messages[0].content.text  # type: ignore[union-attr]
        assert "america" in text
        assert "smart_screen" in text

    def test_find_opportunities_custom_market(self) -> None:
        messages = find_opportunities(market="crypto")
        text = messages[0].content.text  # type: ignore[union-attr]
        assert "crypto" in text
