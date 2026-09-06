"""
Market / Industry dashboard router.

Endpoints
---------
GET /market/sectors
    Returns the full L1 sector index (name, path, sub-industries, total_stocks).
    Cached 4 h in the scraping service.

GET /market/sector/{path:path}
    Returns stocks listed on any screener.in /market/... page.
    `path` can be a L1 code (e.g. "IN08") or a full sub-path (e.g. "IN08/IN0801").
    Results cached 4 h. Pass ?force=true to bypass.
"""
from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.data_fetch import (
    IndustryNode,
    IndustryOverviewRow,
    SectorInfo,
    fetch_industry_overview,
    fetch_industry_stocks,
    fetch_sector_index,
)
from backend.app.services.ai_agent import run_sector_analysis

router = APIRouter()


# ── Sector index ───────────────────────────────────────────────────────────────

@router.get("/sectors")
def get_sector_index(force: bool = False) -> list[dict[str, Any]]:
    """
    Return the full L1 sector tree scraped from screener.in/market/.

    Each entry contains:
      code, name, path, total_stocks,
      sub_industries: [{name, path, stock_count}]

    Cached 4 hours. Pass ?force=true to re-scrape immediately.
    """
    sectors = fetch_sector_index(force=force)
    if not sectors:
        raise HTTPException(
            status_code=503,
            detail="Could not load sector index from screener.in — service may be rate-limiting.",
        )
    return [_sector_to_dict(s) for s in sectors]


@router.get("/overview")
def get_industry_overview(force: bool = False) -> list[dict[str, Any]]:
    """
    Return the /market/ comparison table — all 188 industries with aggregate metrics:
    No. of Companies, Total Market Cap, Median Market Cap, Median P/E,
    Wtd. Avg Sales Growth, Wtd. Avg OPM, Wtd. Avg ROCE, Median 1Y Return.

    Cached 4 hours. Pass ?force=true to re-scrape.
    """
    rows = fetch_industry_overview(force=force)
    if not rows:
        raise HTTPException(
            status_code=503,
            detail="Could not load industry overview from screener.in.",
        )
    return [dataclasses.asdict(r) for r in rows]


@router.get("/sector-analysis")
def get_sector_analysis(force: bool = False) -> dict[str, Any]:
    """
    Return Gemini's daily sector rotation guidance for all 12 L1 sectors.

    Fetches the 188-industry overview (from cache if fresh) and passes it to
    Gemini for BUY/HOLD/AVOID signals per sector + top-5 buy/avoid industries.

    Cached 24 hours in-process. Pass ?force=true to regenerate immediately.
    """
    rows = fetch_industry_overview()   # uses its own 4h cache
    if not rows:
        raise HTTPException(
            status_code=503,
            detail="Industry overview not available — cannot run sector analysis.",
        )

    result = run_sector_analysis(rows, force=force)
    if not result:
        raise HTTPException(
            status_code=503,
            detail="Sector analysis unavailable — Gemini API key not set or model unavailable.",
        )
    return result


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _node_to_dict(node: IndustryNode) -> dict[str, Any]:
    # Sort children by total_stocks descending so larger sub-industries come first
    sorted_children = sorted(node.children, key=lambda c: c.total_stocks, reverse=True)
    return {
        "name":        node.name,
        "path":        node.path,
        "depth":       node.depth,
        "stock_count": node.stock_count,
        "total_stocks": node.total_stocks,
        "children":    [_node_to_dict(c) for c in sorted_children],
    }


def _sector_to_dict(s: SectorInfo) -> dict[str, Any]:
    # Sort L2 children by total_stocks descending
    sorted_children = sorted(s.children, key=lambda c: c.total_stocks, reverse=True)
    return {
        "code":         s.code,
        "name":         s.name,
        "path":         s.path,
        "total_stocks": s.total_stocks_display,
        "children":     [_node_to_dict(c) for c in sorted_children],
        "flat_industries": [_node_to_dict(n) for n in s.flat_industries],
    }


# ── Sector / industry stock listing ───────────────────────────────────────────

@router.get("/sector/{path:path}")
def get_industry_stocks(
    path: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Return stocks on a screener.in market page.

    `path` — the URL segment(s) after /market/, e.g.:
      - "IN08"            → all IT sector stocks
      - "IN08/IN0801"     → IT sub-industry stocks

    Trailing slash is normalised automatically.
    Response: {title, path, stocks: [...], error, fetched_at}
    """
    # Normalise to /market/{path}/
    clean = path.strip("/")
    market_path = f"/market/{clean}/"

    result = fetch_industry_stocks(market_path, force=force)

    if result.error and not result.stocks:
        raise HTTPException(status_code=503, detail=result.error)

    return dataclasses.asdict(result)
