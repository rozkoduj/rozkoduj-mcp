"""Tests for rozkoduj_mcp.resources."""

import json

from rozkoduj_mcp.resources import get_fields, get_markets, get_operators


class TestResources:
    def test_markets_returns_valid_json(self) -> None:
        data = json.loads(get_markets())
        assert isinstance(data, list)
        assert len(data) > 10
        ids = {m["id"] for m in data}
        assert "america" in ids
        assert "crypto" in ids
        assert "forex" in ids
        assert "poland" in ids

    def test_markets_have_required_keys(self) -> None:
        data = json.loads(get_markets())
        for market in data:
            assert "id" in market
            assert "name" in market

    def test_fields_returns_valid_json(self) -> None:
        data = json.loads(get_fields())
        assert isinstance(data, list)
        assert len(data) > 20
        ids = {f["id"] for f in data}
        assert "RSI" in ids
        assert "close" in ids
        assert "price_earnings_ttm" in ids

    def test_fields_have_required_keys(self) -> None:
        data = json.loads(get_fields())
        for field in data:
            assert "id" in field
            assert "name" in field
            assert "category" in field

    def test_operators_returns_valid_json(self) -> None:
        data = json.loads(get_operators())
        assert isinstance(data, list)
        assert len(data) > 5
        ids = {o["id"] for o in data}
        assert "greater" in ids
        assert "less" in ids
        assert "in_range" in ids
        assert "crosses_above" in ids

    def test_operators_have_required_keys(self) -> None:
        data = json.loads(get_operators())
        for op in data:
            assert "id" in op
            assert "name" in op
            assert "example" in op
