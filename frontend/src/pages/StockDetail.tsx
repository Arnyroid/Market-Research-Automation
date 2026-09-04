import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { RefreshCw, AlertTriangle, TrendingUp } from "lucide-react";
import { pricesApi, OHLCVBar } from "../api/prices";
import { analysisApi, Analysis } from "../api/analysis";

const RISK_BADGE: Record<string, string> = {
  low:    "badge-low",
  medium: "badge-medium",
  high:   "badge-high",
};

function IndicatorTile({ label, value, sub }: { label: string; value: string | null; sub?: string }) {
  return (
    <div className="card py-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-lg font-semibold text-white">{value ?? <span className="text-gray-600 text-sm">—</span>}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

export default function StockDetailPage() {
  const { symbol }              = useParams<{ symbol: string }>();
  const [sp]                    = useSearchParams();
  const exchange                = (sp.get("exchange") ?? "NSE").toUpperCase();

  const [history, setHistory]       = useState<OHLCVBar[]>([]);
  const [analysis, setAnalysis]     = useState<Analysis | null>(null);
  const [quote, setQuote]           = useState<import("../api/prices").Quote | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [aiError, setAiError]       = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    pricesApi.getHistory(symbol, exchange).then(setHistory).catch(console.error);
    analysisApi.getLatest(symbol, exchange).then(setAnalysis).catch(() => setAnalysis(null));
    pricesApi.getQuote(symbol, exchange).then(setQuote).catch(() => null);
  }, [symbol, exchange]);

  async function handleRefresh() {
    if (!symbol) return;
    setRefreshing(true); setAiError(null);
    try {
      await analysisApi.refresh(symbol, exchange);
      setTimeout(async () => {
        const a = await analysisApi.getLatest(symbol, exchange).catch(() => null);
        if (a) setAnalysis(a);
        setRefreshing(false);
      }, 4_000);
    } catch (err: any) {
      setAiError(err.message);
      setRefreshing(false);
    }
  }

  const chartData = history.map(b => ({
    date:  b.timestamp.slice(0, 10),
    close: b.close,
  }));

  const snap = analysis?.indicators_snapshot as Record<string, number | null> | null;
  const ltp  = snap?.current_price;
  const pct1 = snap?.pct_change_1d;

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
          {/* Ticker symbol shown below company name */}
          <p className="font-mono text-sm text-gray-500 mt-0.5">{symbol}</p>
          {/* Live price — prefer quote over analysis snapshot */}
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
        <button onClick={handleRefresh} disabled={refreshing} className="btn-primary">
          <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} />
          {refreshing ? "Generating…" : "Get AI Insight"}
        </button>
      </div>

      {/* Price chart */}
      <div className="card mb-6">
        <h2 className="text-sm font-semibold text-gray-400 mb-4">Price History — 30 days</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "#6b7280", fontSize: 11 }} tickLine={false} axisLine={false}
                tickFormatter={v => `₹${v.toLocaleString("en-IN")}`} width={72} />
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
                labelStyle={{ color: "#9ca3af", fontSize: 11 }}
                formatter={(v: number) => [`₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, "Close"]}
              />
              <Line type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} />
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
        <div className="grid grid-cols-3 gap-3 mb-6">
          <IndicatorTile label="RSI (14)" value={snap.rsi_14?.toFixed(1) ?? null}
            sub={snap.rsi_14 != null ? (snap.rsi_14 > 70 ? "Overbought" : snap.rsi_14 < 30 ? "Oversold" : "Neutral") : undefined} />
          <IndicatorTile label="SMA-20" value={snap.sma_20 != null ? `₹${snap.sma_20.toLocaleString("en-IN")}` : null}
            sub={snap.price_vs_sma20_pct != null ? `${snap.price_vs_sma20_pct > 0 ? "+" : ""}${snap.price_vs_sma20_pct.toFixed(1)}% vs price` : undefined} />
          <IndicatorTile label="SMA-50" value={snap.sma_50 != null ? `₹${snap.sma_50.toLocaleString("en-IN")}` : null} />
          <IndicatorTile label="EMA-20" value={snap.ema_20 != null ? `₹${snap.ema_20.toLocaleString("en-IN")}` : null} />
          <IndicatorTile label="5-day Change" value={snap.pct_change_5d != null ? `${snap.pct_change_5d > 0 ? "+" : ""}${snap.pct_change_5d.toFixed(2)}%` : null} />
          <IndicatorTile label="Volatility (30d ann.)" value={snap.realized_volatility_30d != null ? `${snap.realized_volatility_30d.toFixed(1)}%` : null} />
        </div>
      )}

      {/* AI Insight panel */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-white">AI Insight</h2>
          {analysis?.generated_at && (
            <span className="text-xs text-gray-500">
              {new Date(analysis.generated_at).toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" })}
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
            <p className="text-gray-200 text-sm leading-relaxed mb-4">{analysis.structured_output.summary}</p>
            <div className="border-t border-gray-800 pt-4 space-y-2">
              <p className="text-xs text-yellow-500/80 flex gap-2 items-start">
                <AlertTriangle size={12} className="mt-0.5 shrink-0" />
                {analysis.structured_output.caveats}
              </p>
              <p className="text-xs text-gray-600">{analysis.structured_output.disclaimer}</p>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">No analysis yet.</p>
            <p className="text-gray-600 text-xs mt-1">Click "Get AI Insight" above to generate one.</p>
          </div>
        )}
      </div>
    </div>
  );
}
