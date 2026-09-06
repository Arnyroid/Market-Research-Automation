import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { RefreshCw, AlertTriangle, TrendingUp, Bell, PlusCircle } from "lucide-react";
import { pricesApi, OHLCVBar } from "../api/prices";
import { analysisApi, Analysis } from "../api/analysis";

// ── Constants ─────────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  low:    "badge-low",
  medium: "badge-medium",
  high:   "badge-high",
};

const REC_STYLE: Record<string, string> = {
  BUY:   "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30",
  HOLD:  "bg-blue-500/15 text-blue-400 border border-blue-500/30",
  SELL:  "bg-red-500/15 text-red-400 border border-red-500/30",
  AVOID: "bg-yellow-500/15 text-yellow-400 border border-yellow-500/30",
};

const REC_ICON: Record<string, string> = {
  BUY: "▲", HOLD: "◆", SELL: "▼", AVOID: "⊘",
};

// ── Indicator computations (client-side, from raw OHLCV) ─────────────────────

/** Simple moving average over `period` bars */
function sma(closes: number[], period: number): (number | null)[] {
  return closes.map((_, i) => {
    if (i < period - 1) return null;
    const slice = closes.slice(i - period + 1, i + 1);
    return slice.reduce((a, b) => a + b, 0) / period;
  });
}

/** Wilder-style EMA over `period` bars */
function ema(closes: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const out: (number | null)[] = new Array(closes.length).fill(null);
  let prev: number | null = null;
  for (let i = 0; i < closes.length; i++) {
    if (i < period - 1) { out[i] = null; continue; }
    if (prev === null) {
      // Seed with SMA of first `period` bars
      prev = closes.slice(0, period).reduce((a, b) => a + b, 0) / period;
      out[i] = prev;
    } else {
      prev = closes[i] * k + prev * (1 - k);
      out[i] = prev;
    }
  }
  return out;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function IndicatorTile({ label, value, sub }: { label: string; value: string | null; sub?: string }) {
  return (
    <div className="card py-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white">
        {value ?? <span className="text-gray-600 text-sm">—</span>}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

/** Small pill toggle for chart overlay lines */
function OverlayToggle({
  label, color, active, onClick,
}: { label: string; color: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium border transition-opacity ${
        active ? "opacity-100" : "opacity-30"
      }`}
      style={{ borderColor: color, color }}
    >
      <span className="inline-block w-5 h-0.5 rounded" style={{ background: color }} />
      {label}
    </button>
  );
}

/** Return true if the analysis is absent or was generated on a previous calendar day */
function isStale(a: Analysis | null): boolean {
  if (!a) return true;
  const today = new Date().toISOString().slice(0, 10);
  return a.generated_at.slice(0, 10) < today;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function StockDetailPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const [sp]       = useSearchParams();
  const exchange   = (sp.get("exchange") ?? "NSE").toUpperCase();
  const navigate   = useNavigate();

  const [history, setHistory]       = useState<OHLCVBar[]>([]);
  const [analysis, setAnalysis]     = useState<Analysis | null>(null);
  const [quote, setQuote]           = useState<import("../api/prices").Quote | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [aiError, setAiError]       = useState<string | null>(null);

  // Chart overlay toggles
  const [showSMA20, setShowSMA20] = useState(true);
  const [showEMA20, setShowEMA20] = useState(true);
  const [showDMA50, setShowDMA50] = useState(true);
  const [showDMA200, setShowDMA200] = useState(true);

  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Shared poll loop ──────────────────────────────────────────────────────
  const startPolling = useCallback((newerThan: string | null) => {
    if (!symbol) return;
    const started  = Date.now();
    const MAX_WAIT = 45_000;
    let   attempts = 0;

    const poll = async () => {
      attempts++;
      if (Date.now() - started > MAX_WAIT) {
        setAiError("Analysis is taking longer than expected — try the button again.");
        setRefreshing(false);
        return;
      }
      const a = await analysisApi.getLatest(symbol, exchange).catch(() => null);
      if (a && (!newerThan || a.generated_at > newerThan)) {
        setAnalysis(a);
        setRefreshing(false);
      } else {
        const delay = Math.min(2_000 + attempts * 500, 5_000);
        pollTimer.current = setTimeout(poll, delay);
      }
    };
    pollTimer.current = setTimeout(poll, 4_000);
  }, [symbol, exchange]);

  // Cancel polls on symbol change
  useEffect(() => {
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current); };
  }, [symbol, exchange]);

  // ── On mount: load data + auto-trigger stale analysis ────────────────────
  useEffect(() => {
    if (!symbol) return;
    if (pollTimer.current) clearTimeout(pollTimer.current);

    pricesApi.getHistory(symbol, exchange, 300).then(setHistory).catch(console.error);
    pricesApi.getQuote(symbol, exchange).then(setQuote).catch(() => null);

    analysisApi.getLatest(symbol, exchange)
      .then(existing => {
        setAnalysis(existing);
        if (isStale(existing)) {
          setRefreshing(true); setAiError(null);
          analysisApi.refresh(symbol, exchange)
            .then(() => startPolling(existing?.generated_at ?? null))
            .catch(err => { setAiError(err.message ?? "Could not start analysis"); setRefreshing(false); });
        }
      })
      .catch(() => {
        setAnalysis(null);
        setRefreshing(true); setAiError(null);
        analysisApi.refresh(symbol, exchange)
          .then(() => startPolling(null))
          .catch(err => { setAiError(err.message ?? "Could not start analysis"); setRefreshing(false); });
      });
  }, [symbol, exchange]);

  // ── Manual refresh button ─────────────────────────────────────────────────
  async function handleRefresh() {
    if (!symbol || refreshing) return;
    if (pollTimer.current) clearTimeout(pollTimer.current);
    setRefreshing(true); setAiError(null);
    try {
      await analysisApi.refresh(symbol, exchange);
      startPolling(analysis?.generated_at ?? null);
    } catch (err: any) {
      setAiError(err.message ?? "Failed to queue analysis");
      setRefreshing(false);
    }
  }

  // ── Chart data with all overlays ─────────────────────────────────────────
  const closes  = history.map(b => b.close);
  const sma20   = sma(closes, 20);
  const ema20   = ema(closes, 20);
  const dma50   = sma(closes, 50);
  const dma200  = sma(closes, 200);

  const chartData = history.map((b, i) => ({
    date:   b.timestamp.slice(0, 10),
    close:  b.close,
    sma20:  sma20[i]  !== null ? parseFloat(sma20[i]!.toFixed(2))  : undefined,
    ema20:  ema20[i]  !== null ? parseFloat(ema20[i]!.toFixed(2))  : undefined,
    dma50:  dma50[i]  !== null ? parseFloat(dma50[i]!.toFixed(2))  : undefined,
    dma200: dma200[i] !== null ? parseFloat(dma200[i]!.toFixed(2)) : undefined,
  }));

  // ── Indicator snapshot (from latest analysis) ─────────────────────────────
  const snap = analysis?.indicators_snapshot as Record<string, number | null> | null;
  const ltp  = snap?.current_price;
  const pct1 = snap?.pct_change_1d;

  const hasOverlays  = closes.length >= 20;
  const hasDMA50     = closes.length >= 50;
  const hasDMA200    = closes.length >= 200;

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-white">
              {quote?.company_name || symbol}
            </h1>
            <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded font-medium">{exchange}</span>
            {analysis?.risk_flag && (
              <span className={RISK_BADGE[analysis.risk_flag] ?? "badge-medium"}>
                {analysis.risk_flag.toUpperCase()} RISK
              </span>
            )}
          </div>
          <p className="font-mono text-sm text-gray-500 mt-0.5">{symbol}</p>
          {(quote?.ltp ?? ltp) && (
            <p className="text-3xl font-bold text-white mt-2">
              ₹{(quote?.ltp ?? ltp)!.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              {(quote?.pct_change ?? pct1) != null && (
                <span className={`text-base ml-3 ${(quote?.pct_change ?? pct1)! >= 0 ? "gain" : "loss"}`}>
                  {(quote?.pct_change ?? pct1)! >= 0 ? "▲" : "▼"} {Math.abs((quote?.pct_change ?? pct1)!).toFixed(2)}%
                </span>
              )}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/alerts?symbol=${symbol}&exchange=${exchange}`)}
            className="btn-ghost flex items-center gap-1.5 text-sm"
            title="Add alert for this stock"
          >
            <Bell size={15} />
            Add Alert
          </button>
          <button
            onClick={() => navigate(`/portfolio?addTrade=${symbol}&exchange=${exchange}`)}
            className="btn-ghost flex items-center gap-1.5 text-sm"
            title="Log a trade for this stock"
          >
            <PlusCircle size={15} />
            Add Trade
          </button>
          <button onClick={handleRefresh} disabled={refreshing} className="btn-primary">
            <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Generating…" : "Refresh Insight"}
          </button>
        </div>
      </div>

      {/* Price chart */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-400">
            Price History — {hasDMA200 ? "300" : hasDMA50 ? "300" : "300"} days
          </h2>
          {hasOverlays && (
            <div className="flex items-center gap-2 flex-wrap">
              <OverlayToggle label="SMA-20"  color="#f59e0b" active={showSMA20}  onClick={() => setShowSMA20(v => !v)} />
              <OverlayToggle label="EMA-20"  color="#a78bfa" active={showEMA20}  onClick={() => setShowEMA20(v => !v)} />
              {hasDMA50  && <OverlayToggle label="DMA-50"  color="#fb923c" active={showDMA50}  onClick={() => setShowDMA50(v => !v)} />}
              {hasDMA200 && <OverlayToggle label="DMA-200" color="#f87171" active={showDMA200} onClick={() => setShowDMA200(v => !v)} />}
            </div>
          )}
        </div>

        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fill: "#6b7280", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={v => `₹${v.toLocaleString("en-IN")}`}
                width={72}
              />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ color: "#9ca3af", fontSize: 11 }}
                formatter={(v: number, name: string) => {
                  const labelMap: Record<string, string> = {
                    close: "Close", sma20: "SMA-20", ema20: "EMA-20",
                    dma50: "DMA-50", dma200: "DMA-200",
                  };
                  return [`₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, labelMap[name] ?? name];
                }}
              />

              {/* Close price — always shown */}
              <Line
                type="monotone"
                dataKey="close"
                stroke="#3b82f6"
                dot={false}
                strokeWidth={2}
                name="close"
              />

              {/* SMA-20 overlay */}
              {hasOverlays && showSMA20 && (
                <Line
                  type="monotone"
                  dataKey="sma20"
                  stroke="#f59e0b"
                  dot={false}
                  strokeWidth={1.5}
                  strokeDasharray="4 2"
                  name="sma20"
                  connectNulls
                />
              )}

              {/* EMA-20 overlay */}
              {hasOverlays && showEMA20 && (
                <Line
                  type="monotone"
                  dataKey="ema20"
                  stroke="#a78bfa"
                  dot={false}
                  strokeWidth={1.5}
                  strokeDasharray="2 2"
                  name="ema20"
                  connectNulls
                />
              )}

              {/* DMA-50 overlay */}
              {hasDMA50 && showDMA50 && (
                <Line
                  type="monotone"
                  dataKey="dma50"
                  stroke="#fb923c"
                  dot={false}
                  strokeWidth={1.5}
                  name="dma50"
                  connectNulls
                />
              )}

              {/* DMA-200 overlay */}
              {hasDMA200 && showDMA200 && (
                <Line
                  type="monotone"
                  dataKey="dma200"
                  stroke="#f87171"
                  dot={false}
                  strokeWidth={2}
                  name="dma200"
                  connectNulls
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-gray-600">
            <TrendingUp size={28} className="mb-2" />
            <p className="text-sm">No price history yet.</p>
            <p className="text-xs mt-1">Add this symbol to your watchlist — prices populate during market hours.</p>
          </div>
        )}
      </div>

      {/* Indicator tiles */}
      {snap && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
          <IndicatorTile
            label="RSI (14)"
            value={snap.rsi_14?.toFixed(1) ?? null}
            sub={snap.rsi_14 != null
              ? snap.rsi_14 > 70 ? "Overbought" : snap.rsi_14 < 30 ? "Oversold" : "Neutral"
              : undefined}
          />
          <IndicatorTile
            label="SMA-20"
            value={snap.sma_20 != null ? `₹${snap.sma_20.toLocaleString("en-IN")}` : null}
            sub={snap.price_vs_sma20_pct != null
              ? `${snap.price_vs_sma20_pct > 0 ? "+" : ""}${snap.price_vs_sma20_pct.toFixed(1)}% vs price`
              : undefined}
          />
          <IndicatorTile
            label="DMA-50"
            value={snap.sma_50 != null ? `₹${snap.sma_50.toLocaleString("en-IN")}` : null}
            sub={snap.sma_200 != null && snap.sma_50 != null
              ? snap.sma_50 > snap.sma_200 ? "Golden cross ✓" : "Death cross ✗"
              : undefined}
          />
          <IndicatorTile
            label="DMA-200"
            value={snap.sma_200 != null ? `₹${snap.sma_200.toLocaleString("en-IN")}` : null}
            sub={snap.sma_200 != null && snap.current_price != null
              ? snap.current_price > snap.sma_200 ? "Above (bullish)" : "Below (bearish)"
              : undefined}
          />
          <IndicatorTile
            label="EMA-20"
            value={snap.ema_20 != null ? `₹${snap.ema_20.toLocaleString("en-IN")}` : null}
          />
          <IndicatorTile
            label="5-day Change"
            value={snap.pct_change_5d != null
              ? `${snap.pct_change_5d > 0 ? "+" : ""}${snap.pct_change_5d.toFixed(2)}%`
              : null}
          />
          <IndicatorTile
            label="Volatility (30d ann.)"
            value={snap.realized_volatility_30d != null
              ? `${snap.realized_volatility_30d.toFixed(1)}%`
              : null}
          />
        </div>
      )}

      {/* AI Insight panel */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">AI Insight</h2>
          {analysis?.generated_at && !refreshing && (
            <span className="text-xs text-gray-500">
              {new Date(analysis.generated_at).toLocaleDateString("en-IN", {
                day: "2-digit", month: "short", year: "numeric",
              })}
            </span>
          )}
          {refreshing && (
            <span className="text-xs text-gray-500 flex items-center gap-1.5">
              <RefreshCw size={11} className="animate-spin" /> Analysing…
            </span>
          )}
        </div>

        {aiError && (
          <div className="flex items-center gap-2 text-red-400 text-sm mb-4 bg-red-900/20 rounded-lg px-3 py-2">
            <AlertTriangle size={14} /> {aiError}
          </div>
        )}

        {analysis?.structured_output ? (
          <div>
            {/* Recommendation badge */}
            {analysis.structured_output.recommendation && (
              <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold mb-4 ${REC_STYLE[analysis.structured_output.recommendation] ?? REC_STYLE.HOLD}`}>
                <span>{REC_ICON[analysis.structured_output.recommendation]}</span>
                {analysis.structured_output.recommendation}
              </div>
            )}

            {/* Summary */}
            <p className="text-gray-200 text-sm leading-relaxed mb-3">
              {analysis.structured_output.summary}
            </p>

            {/* Rationale */}
            {analysis.structured_output.rationale && (
              <div className="bg-gray-800/50 rounded-lg px-4 py-3 mb-4">
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1 font-semibold">Why this recommendation</p>
                <p className="text-gray-300 text-sm leading-relaxed">{analysis.structured_output.rationale}</p>
              </div>
            )}

            <div className="border-t border-gray-800 pt-4 space-y-2">
              <p className="text-xs text-yellow-500/80 flex gap-2 items-start">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                {analysis.structured_output.caveats}
              </p>
              <p className="text-xs text-gray-600">{analysis.structured_output.disclaimer}</p>
            </div>
          </div>
        ) : !refreshing ? (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">No analysis yet.</p>
            <p className="text-gray-600 text-xs mt-1">Click "Refresh Insight" above to generate one.</p>
          </div>
        ) : (
          <div className="space-y-2 animate-pulse">
            <div className="h-3.5 bg-gray-800 rounded w-full" />
            <div className="h-3.5 bg-gray-800 rounded w-5/6" />
            <div className="h-3.5 bg-gray-800 rounded w-4/6" />
          </div>
        )}
      </div>
    </div>
  );
}
