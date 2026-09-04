import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { RefreshCw } from "lucide-react";
import { pricesApi, OHLCVBar } from "../api/prices";
import { analysisApi, Analysis } from "../api/analysis";

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-700",
  medium: "bg-yellow-100 text-yellow-700",
  high: "bg-red-100 text-red-700",
};

export default function StockDetailPage() {
  const { symbol }              = useParams<{ symbol: string }>();
  const [sp]                    = useSearchParams();
  const exchange                = sp.get("exchange") ?? "NSE";

  const [history, setHistory]   = useState<OHLCVBar[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [aiError, setAiError]   = useState<string | null>(null);

  useEffect(() => {
    if (!symbol) return;
    pricesApi.getHistory(symbol, exchange).then(setHistory).catch(console.error);
    analysisApi.getLatest(symbol, exchange).then(setAnalysis).catch(() => setAnalysis(null));
  }, [symbol, exchange]);

  async function handleRefresh() {
    if (!symbol) return;
    setRefreshing(true);
    setAiError(null);
    try {
      await analysisApi.refresh(symbol, exchange);
      // Poll for the new result after a short delay
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

  const chartData = history.map((b) => ({
    date: b.timestamp.slice(0, 10),
    close: b.close,
  }));

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">{symbol} <span className="text-gray-400 text-base font-normal">({exchange})</span></h1>

      {/* Price chart */}
      <div className="mt-4 mb-8 bg-white border rounded-lg p-4">
        <h2 className="text-sm font-semibold text-gray-500 mb-3">Price History (30 days)</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData}>
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `₹${v.toLocaleString("en-IN")}`} />
              <Line type="monotone" dataKey="close" stroke="#3b82f6" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">No price history yet — add to watchlist and wait for the price poller.</p>
        )}
      </div>

      {/* Indicators */}
      {analysis?.indicators_snapshot && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-gray-500 mb-3">Technical Indicators</h2>
          <div className="grid grid-cols-3 gap-3">
            {[
              ["RSI (14)", analysis.indicators_snapshot["rsi_14"]],
              ["SMA-20", analysis.indicators_snapshot["sma_20"]],
              ["SMA-50", analysis.indicators_snapshot["sma_50"]],
              ["EMA-20", analysis.indicators_snapshot["ema_20"]],
              ["1-day %", analysis.indicators_snapshot["pct_change_1d"]],
              ["Volatility (30d ann.)", analysis.indicators_snapshot["realized_volatility_30d"]],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-gray-50 rounded-lg p-3 border">
                <p className="text-xs text-gray-500">{label as string}</p>
                <p className="text-lg font-semibold mt-1">
                  {val != null ? (typeof val === "number" ? val.toFixed(2) : String(val)) : "—"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI Insight panel */}
      <div className="border rounded-lg p-5 bg-white">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">AI Insight</h2>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Generating…" : "Get AI Insight"}
          </button>
        </div>

        {aiError && <p className="text-red-500 text-sm mb-3">{aiError}</p>}

        {analysis?.structured_output ? (
          <>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${RISK_COLORS[analysis.risk_flag ?? "medium"] ?? ""}`}>
                {(analysis.risk_flag ?? "medium").toUpperCase()} RISK
              </span>
              <span className="text-xs text-gray-400">Generated {analysis.generated_at.slice(0, 10)}</span>
            </div>
            <p className="text-sm text-gray-700 mb-3 leading-relaxed">{analysis.structured_output.summary}</p>
            <p className="text-xs text-gray-500 italic mb-3">⚠ {analysis.structured_output.caveats}</p>
            <p className="text-xs text-gray-400 border-t pt-2">{analysis.structured_output.disclaimer}</p>
          </>
        ) : (
          <p className="text-gray-400 text-sm">No analysis yet. Click "Get AI Insight" to generate one.</p>
        )}
      </div>
    </div>
  );
}
