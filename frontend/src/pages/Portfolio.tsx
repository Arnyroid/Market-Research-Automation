import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface PortfolioRow {
  id: number; symbol: string; exchange: string; company_name: string | null;
  total_quantity: number; avg_buy_price: number; total_invested: number;
  current_price: number | null; current_value: number | null;
  unrealized_pnl: number | null; unrealized_pnl_pct: number | null;
}

function inr(n: number | null) {
  if (n == null) return <span className="text-gray-600">—</span>;
  return `₹${Math.abs(n).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}

export default function PortfolioPage() {
  const [rows, setRows] = useState<PortfolioRow[]>([]);

  useEffect(() => {
    apiFetch<PortfolioRow[]>("/trades/portfolio").then(setRows).catch(console.error);
  }, []);

  const totalInvested = rows.reduce((s, r) => s + r.total_invested, 0);
  const totalValue    = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
  const totalPnl      = totalValue - totalInvested;
  const totalPct      = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;
  const gainers       = rows.filter(r => (r.unrealized_pnl ?? 0) > 0).length;
  const losers        = rows.filter(r => (r.unrealized_pnl ?? 0) < 0).length;

  const summaryCards = [
    { label: "Invested",     value: `₹${totalInvested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, sub: `${rows.length} holdings`, color: "text-white" },
    { label: "Current Value",value: `₹${totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,    sub: "Mark to market",          color: "text-white" },
    { label: "Unrealized P&L",value: `${totalPnl >= 0 ? "+" : ""}₹${Math.abs(totalPnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`, sub: `${totalPct >= 0 ? "+" : ""}${totalPct.toFixed(2)}%`, color: totalPnl >= 0 ? "gain" : "loss" },
    { label: "Gainers / Losers", value: `${gainers} / ${losers}`, sub: `${rows.length - gainers - losers} neutral`, color: "text-white" },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Portfolio</h1>
        <p className="text-gray-400 text-sm mt-1">Current holdings and unrealized P&amp;L</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {summaryCards.map(c => (
          <div key={c.label} className="card">
            <p className="text-xs text-gray-500 uppercase tracking-wide">{c.label}</p>
            <p className={`text-xl font-bold mt-2 ${c.color}`}>{c.value}</p>
            <p className="text-xs text-gray-500 mt-1">{c.sub}</p>
          </div>
        ))}
      </div>

      {/* Holdings table */}
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-800/50">
            <tr>
              {["Symbol", "Exchange", "Qty", "Avg Price", "Invested", "LTP", "Current Value", "P&L", "P&L %"].map(h => (
                <th key={h} className="th last:text-right">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={9} className="td text-center text-gray-500 py-16">No holdings. Add trades via the API or import a file.</td></tr>
            )}
            {rows.map(r => {
              const pnl  = r.unrealized_pnl;
              const pct  = r.unrealized_pnl_pct;
              const up   = (pnl ?? 0) >= 0;
              const Icon = pnl == null ? Minus : up ? TrendingUp : TrendingDown;
              return (
                <tr key={r.id} className="hover:bg-gray-800/30 transition-colors">
                  <td className="td font-mono font-semibold text-white">{r.symbol}</td>
                  <td className="td"><span className="text-xs bg-gray-800 text-gray-300 px-2 py-0.5 rounded">{r.exchange}</span></td>
                  <td className="td text-gray-300">{r.total_quantity}</td>
                  <td className="td font-mono text-gray-300">₹{r.avg_buy_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  <td className="td font-mono text-gray-300">₹{r.total_invested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td>
                  <td className="td font-mono text-white">{r.current_price != null ? `₹${r.current_price.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : <span className="text-gray-600">—</span>}</td>
                  <td className="td font-mono text-white">{r.current_value != null ? `₹${r.current_value.toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : <span className="text-gray-600">—</span>}</td>
                  <td className={`td font-mono ${pnl == null ? "text-gray-600" : up ? "gain" : "loss"}`}>
                    <span className="flex items-center gap-1">
                      <Icon size={13} />
                      {pnl != null ? `${up ? "+" : "-"}₹${Math.abs(pnl).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "—"}
                    </span>
                  </td>
                  <td className={`td font-mono text-right ${pct == null ? "text-gray-600" : up ? "gain" : "loss"}`}>
                    {pct != null ? `${up ? "+" : ""}${pct.toFixed(2)}%` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
