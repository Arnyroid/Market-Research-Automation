"""
Trades router — manual trade entry, file upload import, and portfolio view.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.db import SessionLocal, get_db
from backend.app.models import Portfolio, Trade

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class TradeCreate(BaseModel):
    trade_date: str        # YYYY-MM-DD
    symbol: str
    exchange: str = "BSE"
    company_name: str | None = None
    trade_type: str        # BUY | SELL
    quantity: int
    price: float
    brokerage: float = 0.0
    notes: str | None = None


class TradeOut(BaseModel):
    id: int
    trade_date: str
    symbol: str
    exchange: str
    company_name: str | None
    trade_type: str
    quantity: int
    price: float
    brokerage: float
    realized_pnl: float | None = None

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    id: int
    symbol: str
    exchange: str
    company_name: str | None
    total_quantity: int
    avg_buy_price: float
    total_invested: float
    current_price: float | None
    current_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None

    model_config = {"from_attributes": True}


# ── Trade endpoints ───────────────────────────────────────────────────────────

@router.get("", response_model=list[TradeOut])
def list_trades(symbol: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Trade)
    if symbol:
        q = q.filter(Trade.symbol == symbol)
    return q.order_by(Trade.trade_date.desc()).all()


@router.post("", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def add_trade(payload: TradeCreate, db: Session = Depends(get_db)):
    if payload.trade_type.upper() not in ("BUY", "SELL"):
        raise HTTPException(status_code=400, detail="trade_type must be BUY or SELL")

    trade = Trade(
        trade_date=payload.trade_date,
        symbol=payload.symbol,
        exchange=payload.exchange.upper(),
        company_name=payload.company_name,
        trade_type=payload.trade_type.upper(),
        quantity=payload.quantity,
        price=payload.price,
        brokerage=payload.brokerage,
        notes=payload.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    _recalculate_portfolio(payload.symbol, payload.exchange.upper(), db)
    return trade


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_trades(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accept a CSV or XLSX file and bulk-insert trades."""
    import io
    import pandas as pd

    content = await file.read()
    fname = (file.filename or "").lower()

    try:
        if fname.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Only .csv and .xlsx files are supported")
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    # Normalise column names
    df.columns = df.columns.str.lower().str.strip()
    rename = {
        "date": "trade_date", "scrip_code": "symbol", "scrip": "symbol",
        "code": "symbol", "type": "trade_type", "action": "trade_type",
        "qty": "quantity", "rate": "price", "company": "company_name",
        "name": "company_name",
    }
    df = df.rename(columns=rename)

    required = {"trade_date", "symbol", "quantity", "price", "trade_type"}
    missing = required - set(df.columns)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns: {missing}")

    imported = 0
    symbols_touched: set[tuple[str, str]] = set()

    for _, row in df.iterrows():
        try:
            exch = str(row.get("exchange", "BSE")).upper()
            trade = Trade(
                trade_date=str(row["trade_date"])[:10],
                symbol=str(row["symbol"]).strip(),
                exchange=exch,
                company_name=str(row.get("company_name", "")) or None,
                trade_type=str(row["trade_type"]).upper().strip(),
                quantity=int(row["quantity"]),
                price=float(row["price"]),
                brokerage=float(row.get("brokerage", 0) or 0),
                notes=str(row.get("notes", "")) or None,
            )
            db.add(trade)
            symbols_touched.add((trade.symbol, trade.exchange))
            imported += 1
        except Exception:
            continue  # skip malformed rows

    db.commit()
    for sym, exch in symbols_touched:
        _recalculate_portfolio(sym, exch, db)

    return {"imported": imported, "skipped": len(df) - imported}


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    symbol, exchange = trade.symbol, trade.exchange
    db.delete(trade)
    db.commit()
    _recalculate_portfolio(symbol, exchange, db)


# ── Portfolio endpoints ───────────────────────────────────────────────────────

@router.get("/portfolio", response_model=list[PortfolioOut])
def get_portfolio(db: Session = Depends(get_db)):
    return db.query(Portfolio).filter(Portfolio.total_quantity > 0).all()


class PortfolioAnalysisOut(BaseModel):
    status: str                      # "ok" | "no_holdings" | "no_api_key"
    generated_at: str | None = None
    overall_health: str | None = None   # "strong" | "moderate" | "weak" | "critical"
    summary: str | None = None
    positions: list[dict] | None = None  # per-holding advice
    rebalance_notes: str | None = None
    risk_notes: str | None = None
    disclaimer: str | None = None


@router.post("/portfolio/analyse", response_model=PortfolioAnalysisOut, status_code=200)
def analyse_portfolio(db: Session = Depends(get_db)):
    """
    Run a portfolio-level AI analysis: reads all holdings, fetches live
    indicators for each, and calls Gemini for buy-more / trim / hold advice.
    Runs synchronously (client waits) since it's explicitly user-triggered.
    """
    from datetime import datetime
    from backend.app.core.config import get_settings
    from backend.app.services.ai_agent import _fmt
    from backend.app.services.data_fetch import fetch_news
    from backend.app.services.indicators import compute_indicators
    from backend.app.models import RiskProfile
    import json, re as _re

    cfg = get_settings()
    if not cfg.gemini_api_key:
        return PortfolioAnalysisOut(
            status="no_api_key",
            summary="GEMINI_API_KEY is not configured — add it to your .env file and restart.",
        )

    holdings = db.query(Portfolio).filter(Portfolio.total_quantity > 0).all()
    if not holdings:
        return PortfolioAnalysisOut(
            status="no_holdings",
            summary="No holdings found. Add some transactions first.",
        )

    # ── Build per-holding context ─────────────────────────────────────────────
    total_invested   = sum(h.total_invested for h in holdings)
    total_value      = sum(h.current_value or h.total_invested for h in holdings)
    total_pnl        = total_value - total_invested
    total_pnl_pct    = round(total_pnl / total_invested * 100, 2) if total_invested else 0

    position_blocks: list[str] = []
    for h in holdings:
        snap = compute_indicators(h.symbol, h.exchange, db)
        weight = round((h.total_invested / total_invested) * 100, 1) if total_invested else 0
        pnl_pct = h.unrealized_pnl_pct or 0

        block = f"""
### {h.symbol} ({h.exchange}) — {h.company_name or h.symbol}
Portfolio weight:   {weight}%
Qty held:           {h.total_quantity}
Avg buy price:      ₹{h.avg_buy_price:.2f}
Current price:      ₹{_fmt(h.current_price)}
Unrealized P&L:     ₹{_fmt(h.unrealized_pnl)} ({pnl_pct:+.2f}%)
RSI (14):           {_fmt(snap.rsi_14)}
SMA-20:             ₹{_fmt(snap.sma_20)}
EMA-20:             ₹{_fmt(snap.ema_20)}
Price vs SMA-20:    {_fmt(snap.price_vs_sma20_pct)}%
Volatility (30d):   {_fmt(snap.realized_volatility_30d)}%
Signal audit:
{snap.signal_context or "  Insufficient data."}""".strip()
        position_blocks.append(block)

    risk = db.query(RiskProfile).first()
    risk_ctx = (
        f"Time horizon: {risk.time_horizon}, "
        f"Loss tolerance: {risk.loss_tolerance}, "
        f"Experience: {risk.experience_level}"
    ) if risk else "Time horizon: medium, Loss tolerance: medium, Experience: intermediate"

    portfolio_summary = (
        f"Total invested: ₹{total_invested:,.2f} across {len(holdings)} holdings | "
        f"Current value: ₹{total_value:,.2f} | "
        f"Unrealized P&L: ₹{total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)"
    )

    positions_text = "\n\n".join(position_blocks)

    system_prompt = """\
You are a senior Indian equity portfolio advisor.
You give concrete, actionable portfolio management advice based solely on the data provided.
Rules:
- For each holding give one of: BUY_MORE, HOLD, TRIM, EXIT
- BUY_MORE = strong bullish signals, price pulled back, within user risk tolerance
- HOLD     = mixed or neutral signals, no clear action needed
- TRIM     = overbought / overweight / moderate loss — reduce position size
- EXIT     = bearish signals dominant, stop-loss breached, or loss exceeds tolerance
- Consider portfolio concentration: flag if any single holding > 30% of portfolio
- Consider correlation: flag if multiple holdings move together (same sector)
- Always include specific reasoning tied to the indicator data
- Respond ONLY with valid JSON matching the schema. No markdown fences.
"""

    user_prompt = f"""Analyse my Indian equity portfolio and provide actionable advice.

## Portfolio Overview
{portfolio_summary}

## User Risk Profile
{risk_ctx}

## Individual Holdings (with live indicators)
{positions_text}

## Response schema (return ONLY this JSON, no markdown, no extra text)
{{
  "overall_health": "<strong|moderate|weak|critical>",
  "summary": "<3-4 sentence overall portfolio assessment>",
  "positions": [
    {{
      "symbol": "<SYMBOL>",
      "action": "<BUY_MORE|HOLD|TRIM|EXIT>",
      "reasoning": "<1-2 sentences on why>"
    }}
  ],
  "rebalance_notes": "<1-2 sentences on concentration/diversification>",
  "risk_notes": "<1-2 sentences on overall risk level and what to watch>",
  "disclaimer": "This is educational analysis only, not financial advice. Consult a SEBI-registered advisor before making investment decisions."
}}"""

    # ── Call Gemini ───────────────────────────────────────────────────────────
    from google import genai
    from google.genai import types as genai_types
    from loguru import logger

    client = genai.Client(api_key=cfg.gemini_api_key)
    gen_cfg = genai_types.GenerateContentConfig(
        system_instruction=system_prompt,
        max_output_tokens=2048,
        temperature=0.2,
    )

    models_to_try = [cfg.gemini_model]
    if cfg.gemini_model_fallback and cfg.gemini_model_fallback != cfg.gemini_model:
        models_to_try.append(cfg.gemini_model_fallback)

    raw_text: str | None = None
    for model_name in models_to_try:
        try:
            resp = client.models.generate_content(
                model=model_name, contents=user_prompt, config=gen_cfg,
            )
            raw_text = (resp.text or "").strip()
            if raw_text:
                break
            logger.warning(f"Portfolio analysis: empty response from {model_name}")
        except Exception as exc:
            err = str(exc)
            if "503" in err or "UNAVAILABLE" in err or "429" in err:
                logger.warning(f"Portfolio analysis: {model_name} overloaded, trying fallback")
            else:
                logger.error(f"Portfolio analysis: Gemini error: {exc}")
                raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}")

    if not raw_text:
        raise HTTPException(status_code=503, detail="Gemini models unavailable — try again later")

    # ── Parse response ────────────────────────────────────────────────────────
    clean = raw_text
    if "```" in clean:
        parts = clean.split("```")
        clean = parts[1].lstrip("json").strip() if len(parts) >= 3 else parts[1].strip()
    if clean.startswith("```"):
        clean = clean[3:].lstrip("json").strip()

    structured: dict | None = None
    try:
        structured = json.loads(clean)
    except json.JSONDecodeError:
        m = _re.search(r'\{.*\}', clean, _re.DOTALL)
        if m:
            try:
                structured = json.loads(m.group())
            except json.JSONDecodeError:
                pass

    if not structured:
        logger.error(f"Portfolio analysis: unparseable response: {raw_text[:300]}")
        raise HTTPException(status_code=502, detail="Could not parse Gemini response — try again")

    health = structured.get("overall_health", "moderate")
    if health not in ("strong", "moderate", "weak", "critical"):
        health = "moderate"

    return PortfolioAnalysisOut(
        status="ok",
        generated_at=datetime.utcnow().isoformat(),
        overall_health=health,
        summary=structured.get("summary", ""),
        positions=structured.get("positions", []),
        rebalance_notes=structured.get("rebalance_notes", ""),
        risk_notes=structured.get("risk_notes", ""),
        disclaimer=structured.get("disclaimer", ""),
    )


# ── Internal helper ───────────────────────────────────────────────────────────

def _recalculate_portfolio(symbol: str, exchange: str, db: Session) -> None:
    """
    FIFO recalculation — rebuild the portfolio row from all trades,
    then fetch the live price and compute unrealized P&L.
    """
    from backend.app.services.data_fetch import fetch_quote

    trades = (
        db.query(Trade)
        .filter(Trade.symbol == symbol, Trade.exchange == exchange)
        .order_by(Trade.trade_date.asc())
        .all()
    )

    qty = 0
    invested = 0.0
    company_name: str | None = None

    for t in trades:
        if t.trade_type == "BUY":
            qty += t.quantity
            invested += t.quantity * t.price + t.brokerage
            if not company_name and t.company_name:
                company_name = t.company_name
        elif t.trade_type == "SELL" and qty > 0:
            avg = invested / qty
            sell_qty = min(t.quantity, qty)
            # Realized P&L = (sell price - FIFO avg cost) × qty, minus brokerage
            realized = round((t.price - avg) * sell_qty - t.brokerage, 2)
            t.realized_pnl = realized
            invested -= sell_qty * avg
            qty -= sell_qty

    row = db.query(Portfolio).filter(
        Portfolio.symbol == symbol, Portfolio.exchange == exchange
    ).first()

    if qty == 0:
        if row:
            db.delete(row)
        db.commit()
        return

    avg_price = round(invested / qty, 2) if qty > 0 else 0.0

    if row is None:
        row = Portfolio(symbol=symbol, exchange=exchange)
        db.add(row)

    row.total_quantity  = qty
    row.avg_buy_price   = avg_price
    row.total_invested  = round(invested, 2)
    if company_name:
        row.company_name = company_name

    # ── Fetch live price and compute P&L ─────────────────────────────────────
    try:
        quote = fetch_quote(symbol, exchange)
        if quote and quote.ltp:
            ltp                  = quote.ltp
            current_value        = round(ltp * qty, 2)
            unrealized_pnl       = round(current_value - invested, 2)
            unrealized_pnl_pct   = round((unrealized_pnl / invested) * 100, 2) if invested else 0.0
            row.current_price    = ltp
            row.current_value    = current_value
            row.unrealized_pnl   = unrealized_pnl
            row.unrealized_pnl_pct = unrealized_pnl_pct
    except Exception:
        pass  # P&L stays null — not fatal

    db.commit()
