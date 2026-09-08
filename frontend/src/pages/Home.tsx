import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, TrendingDown, Briefcase, LayoutDashboard,
  Bell, BarChart2, Coins, ShieldCheck, ArrowRight, Activity,
} from "lucide-react";
import { apiFetch } from "../api/client";
import { watchlistApi, WatchlistItem } from "../api/watchlist";
import { alertsApi, Alert } from "../api/alerts";
import { tradesApi, TradeOut } from "../api/trades";

// ── types ─────────────────────────────────────────────────────────────────────

interface PortfolioRow {
  symbol: string;
  exchange: string;
  company_name: string | null;
  total_quantity: number;
  avg_buy_price: number;
  total_invested: number;
  current_price: number | null;
  current_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  cap_tier: string | null;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function fmtInr(v: number) {
  return "₹" + Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = "text-white", tint }: {
  label: string; value: string; sub?: string; color?: string; tint?: string;
}) {
  return (
    <div className={`rounded-xl px-4 py-4 border ${tint ?? "bg-gray-800/60 border-gray-700/40"}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function NavCard({ icon: Icon, label, desc, to, color }: {
  icon: React.ElementType; label: string; desc: string; to: string; color: string;
}) {
  const nav = useNavigate();
  return (
    <button
      onClick={() => nav(to)}
      className="flex items-start gap-3 rounded-xl px-4 py-3 bg-gray-800/50 border border-gray-700/40
        hover:bg-gray-800 hover:border-gray-600 transition-colors text-left w-full group"
    >
      <div className={`mt-0.5 p-1.5 rounded-lg ${color}`}>
        <Icon size={14} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="text-xs text-gray-500 mt-0.5 leading-snug">{desc}</p>
      </div>
      <ArrowRight size={13} className="text-gray-600 group-hover:text-gray-400 mt-0.5 shrink-0 transition-colors" />
    </button>
  );
}

/** One row in a Top Gainers / Top Losers mini-table */
function MoverRow({ r, navigate }: { r: PortfolioRow; navigate: ReturnType<typeof useNavigate> }) {
  const up  = (r.unrealized_pnl_pct ?? 0) >= 0;
  const pct = r.unrealized_pnl_pct ?? 0;
  return (
    <button
      onClick={() => navigate(`/stock/${r.symbol}?exchange=${r.exchange}`)}
      className="w-full flex items-center justify-between px-4 py-3 text-left
        hover:bg-gray-800/60 transition-colors border-t border-gray-800/60 first:border-t-0"
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-white leading-tight truncate">
          {r.company_name ?? r.symbol}
        </p>
        <p className="text-xs text-gray-500 font-mono mt-0.5">{r.symbol}</p>
      </div>
      <div className="text-right shrink-0 ml-4">
        <p className={`text-sm font-mono font-semibold ${up ? "text-emerald-400" : "text-red-400"}`}>
          {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
        </p>
        {r.unrealized_pnl != null && (
          <p className={`text-xs font-mono ${up ? "text-emerald-500" : "text-red-500"}`}>
            {up ? "+" : "−"}{fmtInr(r.unrealized_pnl)}
          </p>
        )}
      </div>
    </button>
  );
}

// ── page ──────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const navigate = useNavigate();

  const [rows,      setRows]      = useState<PortfolioRow[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [alerts,    setAlerts]    = useState<Alert[]>([]);
  const [trades,    setTrades]    = useState<TradeOut[]>([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiFetch<PortfolioRow[]>("/trades/portfolio").catch(() => [] as PortfolioRow[]),
      watchlistApi.list().catch(() => [] as WatchlistItem[]),
      alertsApi.list().catch(() => [] as Alert[]),
      tradesApi.list().catch(() => [] as TradeOut[]),
    ]).then(([r, w, a, t]) => {
      if (cancelled) return;
      setRows(r); setWatchlist(w); setAlerts(a); setTrades(t);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, []);

  const stats = useMemo(() => {
    const totalInvested = rows.reduce((s, r) => s + r.total_invested, 0);
    const totalValue    = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
    const totalPnl      = totalValue - totalInvested;
    const totalPct      = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;
    const gainers       = rows.filter(r => (r.unrealized_pnl ?? 0) > 0).length;
    const losers        = rows.filter(r => (r.unrealized_pnl ?? 0) < 0).length;
    const realizedPnl   = trades
      .filter(t => t.trade_type === "SELL" && t.realized_pnl != null)
      .reduce((s, t) => s + (t.realized_pnl ?? 0), 0);
    const activeAlerts  = alerts.filter(a => a.active).length;
    return { totalInvested, totalValue, totalPnl, totalPct, gainers, losers, realizedPnl, activeAlerts };
  }, [rows, trades, alerts]);

  const { gainers: topGainers, losers: topLosers } = useMemo(() => {
    const eligible = rows.filter(r => r.unrealized_pnl_pct != null);
    const gainers  = [...eligible]
      .filter(r => (r.unrealized_pnl_pct ?? 0) > 0)
      .sort((a, b) => (b.unrealized_pnl_pct ?? 0) - (a.unrealized_pnl_pct ?? 0))
      .slice(0, 5);
    const losers   = [...eligible]
      .filter(r => (r.unrealized_pnl_pct ?? 0) < 0)
      .sort((a, b) => (a.unrealized_pnl_pct ?? 0) - (b.unrealized_pnl_pct ?? 0))
      .slice(0, 5);
    return { gainers, losers };
  }, [rows]);

  const pnlUp = stats.totalPnl >= 0;
  const hasMovers = topGainers.length > 0 || topLosers.length > 0;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <TrendingUp size={22} className="text-blue-400" />
          <h1 className="text-2xl font-bold text-white tracking-tight">StockAI</h1>
        </div>
        <p className="text-sm text-gray-400">Your personal Indian equities dashboard — NSE &amp; BSE.</p>
      </div>

      {/* ── Summary cards ────────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded-xl bg-gray-800/40 animate-pulse border border-gray-700/40" />
          ))}
        </div>
      ) : rows.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard
            label="Invested"
            value={fmtInr(stats.totalInvested)}
            sub={`${rows.length} holding${rows.length !== 1 ? "s" : ""}`}
          />
          <StatCard
            label="Current Value"
            value={fmtInr(stats.totalValue)}
            color={pnlUp ? "text-emerald-400" : "text-red-400"}
          />
          <StatCard
            label="Unrealized P&L"
            value={`${pnlUp ? "+" : ""}${fmtInr(stats.totalPnl)}`}
            sub={`${stats.totalPct >= 0 ? "+" : ""}${stats.totalPct.toFixed(2)}%`}
            color={pnlUp ? "text-emerald-400" : "text-red-400"}
            tint={pnlUp ? "bg-emerald-900/20 border-emerald-800/40" : "bg-red-900/20 border-red-800/40"}
          />
          <StatCard
            label="Gainers / Losers"
            value={`${stats.gainers}↑  ${stats.losers}↓`}
            sub={stats.realizedPnl !== 0
              ? `Realized: ${stats.realizedPnl >= 0 ? "+" : ""}${fmtInr(stats.realizedPnl)}`
              : `${stats.activeAlerts} active alert${stats.activeAlerts !== 1 ? "s" : ""}`}
          />
        </div>
      )}

      {/* ── Top Gainers ──────────────────────────────────────────────────── */}
      {!loading && topGainers.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <TrendingUp size={14} className="text-emerald-400" />
            Top Gainers
          </h2>
          <div className="rounded-xl border border-gray-700/40 overflow-hidden">
            {topGainers.map(r => <MoverRow key={r.symbol} r={r} navigate={navigate} />)}
          </div>
        </div>
      )}

      {/* ── Top Losers ───────────────────────────────────────────────────── */}
      {!loading && topLosers.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <TrendingDown size={14} className="text-red-400" />
            Top Losers
          </h2>
          <div className="rounded-xl border border-gray-700/40 overflow-hidden">
            {topLosers.map(r => <MoverRow key={r.symbol} r={r} navigate={navigate} />)}
          </div>
        </div>
      )}

      {/* ── Watchlist quick glance ───────────────────────────────────────── */}
      {!loading && watchlist.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3 flex items-center gap-2">
            <LayoutDashboard size={14} />
            Watchlist
            <span className="ml-auto text-xs text-gray-600 font-normal">{watchlist.length} symbol{watchlist.length !== 1 ? "s" : ""}</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {watchlist.slice(0, 12).map(w => (
              <button
                key={w.id}
                onClick={() => navigate(`/stock/${w.symbol}?exchange=${w.exchange}`)}
                className="px-3 py-2 rounded-lg bg-gray-800/60 border border-gray-700/40
                  hover:bg-gray-700/60 hover:border-gray-600 transition-colors text-left"
              >
                {w.company_name && (
                  <p className="text-xs font-semibold text-white leading-tight">{w.company_name}</p>
                )}
                <p className="text-[10px] text-gray-500 font-mono mt-0.5">
                  {w.symbol} <span className="text-gray-600">{w.exchange}</span>
                </p>
              </button>
            ))}
            {watchlist.length > 12 && (
              <button
                onClick={() => navigate("/watchlist")}
                className="px-3 py-1.5 rounded-lg bg-gray-800/30 border border-gray-700/30
                  text-xs text-gray-500 hover:text-gray-300 transition-colors self-center"
              >
                +{watchlist.length - 12} more
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Quick navigation ─────────────────────────────────────────────── */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Navigate</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <NavCard icon={LayoutDashboard} label="Watchlist"    to="/watchlist" color="bg-blue-900/40 text-blue-400"    desc="Live quotes, alerts and search for NSE/BSE symbols." />
          <NavCard icon={Briefcase}       label="Portfolio"    to="/portfolio" color="bg-purple-900/40 text-purple-400" desc="Holdings, P&L breakdown and trade history." />
          <NavCard icon={BarChart2}       label="Industries"   to="/industry"  color="bg-teal-900/40 text-teal-400"     desc="Sector pulse, industry trends and AI summaries." />
          <NavCard icon={Coins}           label="Penny Stocks" to="/penny"     color="bg-amber-900/40 text-amber-400"   desc="Screener-powered low-price stock discovery." />
          <NavCard icon={Bell}            label="Alerts"       to="/alerts"    color="bg-rose-900/40 text-rose-400"     desc={`${stats.activeAlerts} active price alert${stats.activeAlerts !== 1 ? "s" : ""} across your watchlist.`} />
          <NavCard icon={ShieldCheck}     label="Risk Profile" to="/risk"      color="bg-green-900/40 text-green-400"   desc="Set your risk appetite to personalise AI insights." />
        </div>
      </div>

    </div>
  );
}
