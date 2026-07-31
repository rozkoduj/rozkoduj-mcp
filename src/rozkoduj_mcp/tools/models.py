"""Typed output models for the tools.

The MCP SDK builds each tool's ``output_schema`` from its return annotation and
publishes it in ``tools/list``, so a typed model gives the calling model the
field names up front instead of leaving them to be parsed out of a docstring.

``extra="allow"`` on every model: a field this code does not know about yet is
passed through rather than dropped. Optional stays optional: a nullable field
is declared nullable even when it is populated in practice.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Mirror(BaseModel):
    """Base for every mirrored response model."""

    model_config = ConfigDict(extra="allow")


class LockedInfo(_Mirror):
    """Fields withheld for the caller's tier, carried inside a normal 200."""

    fields: list[str]
    required_tier: str
    unlock_url: str
    reason: str


# ─── strategy / leaderboard ────────────────────────────────────────────────


class Strategy(_Mirror):
    """One published strategy. ``best_run`` stays an open object on purpose:
    pinning the metric set here would make every added metric a breaking
    change in code that only forwards it."""

    algorithm_uid: str
    slug: str
    name: dict[str, str] = Field(default_factory=dict, description="i18n: {en, pl}")
    description: dict[str, str] = Field(default_factory=dict, description="i18n")
    family: str | None = None
    variant: str | None = None
    version: str | None = None
    aliases: list[dict[str, str]] = Field(
        default_factory=list, description="i18n alias maps"
    )
    visibility: str = "public"
    is_active: bool = True
    best_run: dict[str, Any] | None = None
    created_at: str
    updated_at: str
    locked: LockedInfo | None = None


class StrategyPage(_Mirror):
    """One page of the leaderboard."""

    items: list[Strategy]
    total: int
    limit: int
    offset: int


# ─── research ──────────────────────────────────────────────────────────────


class ArticleHit(_Mirror):
    """A passage from a public research article. Cite by linking
    ``https://www.rozkoduj.com/<locale>/research/<slug>``."""

    slug: str
    locale: str
    title: str
    description: str | None = None
    chunk_index: int
    chunk_text: str
    parent_text: str | None = None
    context_prefix: str | None = None


class KnowledgeHit(_Mirror):
    """A passage from the deeper knowledge base (paid tiers)."""

    doc_id: str
    chunk_index: int
    title: str
    chunk_text: str
    parent_text: str | None = None
    context_prefix: str | None = None


class ResearchResult(_Mirror):
    """Two ranked passage lists for one query. ``knowledge`` is empty and
    ``locked`` is populated when the caller's tier does not include it."""

    query: str
    articles: list[ArticleHit]
    knowledge: list[KnowledgeHit]
    locked: LockedInfo | None = None


# ─── instruments ───────────────────────────────────────────────────────────


class Instrument(_Mirror):
    """Catalog identity row."""

    listing_slug: str
    ticker: str | None = None
    display_name: str | None = None
    asset_class: str | None = None
    exchange_label: str | None = None
    currency: str | None = None
    sector: str | None = None
    status: str | None = None
    last_close: float | None = None
    prev_close: float | None = None
    last_close_at: str | None = None


class InstrumentStats(_Mirror):
    """Buy-and-hold facts plus the six-axis character fingerprint."""

    asof_date: str
    cagr: float | None = None
    volatility_pct: float | None = None
    max_drawdown: float | None = None
    time_underwater_pct: float | None = None
    kaufman_er: float | None = None
    trend_share_pct: float | None = None
    fingerprint_axes: Any = None
    verdict: Any = None


class InstrumentResult(_Mirror):
    """One response shape for both halves of the ``instrument`` tool.

    The tool answers two questions behind one name - the catalog without
    ``symbol``, one dossier with it - and the two payloads share no keys. The
    honest type is a union, but the SDK wraps unions in ``{"result": ...}``,
    which would change what every existing client reads off the wire for a
    purely internal typing win. Splitting into two tools is the other clean
    answer and was rejected for the same reason, plus one more: the published
    surface is deliberately one tool per pillar.

    So both groups live here as optional, and the discriminator is which group
    is populated: ``items`` for the catalog, ``listing_slug`` for the dossier.
    That publishes every field name - the thing docstring-only fields could not
    do - and accepts weaker per-field enforcement as the price of not moving
    the wire.
    """

    # Catalog page (no `symbol` argument).
    items: list[Instrument] | None = None
    total: int | None = None
    limit: int | None = None
    offset: int | None = None

    # One instrument's dossier (`symbol` given). `stats` is null for freshly
    # added instruments that the analytics pass has not covered yet.
    listing_slug: str | None = None
    ticker: str | None = None
    display_name: str | None = None
    asset_class: str | None = None
    exchange_label: str | None = None
    currency: str | None = None
    sector: str | None = None
    status: str | None = None
    last_close: float | None = None
    prev_close: float | None = None
    last_close_at: str | None = None
    stats: InstrumentStats | None = None
