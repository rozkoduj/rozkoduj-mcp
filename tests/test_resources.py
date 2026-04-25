"""Tests for rozkoduj_mcp.resources."""

import json

from rozkoduj_mcp.resources import (
    get_fields,
    get_freshness_contract,
    get_markets,
    get_operators,
)


class TestResources:
    def test_markets_returns_valid_json(self) -> None:
        data = json.loads(get_markets())
        assert isinstance(data, list)
        assert len(data) > 10
        ids = {m["id"] for m in data}
        assert "us" in ids
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
        assert "pe_ttm" in ids

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

    def test_freshness_contract_returns_valid_json(self) -> None:
        data = json.loads(get_freshness_contract())
        assert isinstance(data, dict)
        assert data["version"] == 1
        assert "summary" in data
        assert "fields" in data
        assert "guidance_for_agents" in data

    def test_freshness_contract_documents_all_fields(self) -> None:
        data = json.loads(get_freshness_contract())
        names = {f["name"] for f in data["fields"]}
        assert names == {"data_date", "freshness", "staleness_seconds", "fetched_at"}

    def test_freshness_contract_lists_freshness_values(self) -> None:
        data = json.loads(get_freshness_contract())
        freshness_field = next(f for f in data["fields"] if f["name"] == "freshness")
        assert set(freshness_field["values"]) == {"LIVE", "RECENT", "STALE", "UNKNOWN"}
