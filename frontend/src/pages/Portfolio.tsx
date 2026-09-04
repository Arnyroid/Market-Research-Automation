import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

interface PortfolioRow {
  id: number;
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
}

function fmt(n: number | null, prefix = "₹") {
  if (n == null) return "—";
  return `${prefix}${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function PortfolioPage() {
  const [rows, setRows] = useState<PortfolioRow[]>([]);

  useEffect(() => {
    apiFetch<PortfolioRow[]>("/trades/portfolio").then(setRows).catch(console.error);
  }, []);

  const totalInvested = rows.reduce((s, r) => s + r.total_invested, 0);
  const totalValue    = rows.reduce((s, r) => s + (r.current_value ?? r.total_invested), 0);
  const totalPnl      = totalValue - totalInvested;
  const totalPnlPct   = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Portfolio</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          ["Total Invested",  fmt(totalInvested)],
          ["Current Value",   fmt(totalValue)],
          ["Unrealized P&L",  fmt(totalPnl)],
          ["P&L %",           `${totalPnlPct >= 0 ? "+" : ""}${totalPnlPct.toFixed(2)}%`],
        ].map(([label, val]) => (
          <div key={label} className="bg-white border rounded-lg p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-lg font-bold mt-1 ${label === "P&L %" || label === "Unrealized P&L" ? (totalPnl >= 0 ? "text-green-600" : "text-red-600") : ""}`}>{val}</p>
          </div>
        ))}
      </div>

      {/* Holdings table */}
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-gray-50 text-left">
            {["Symbol", "Exchange", "Qty", "Avg Price", "Invested", "LTP", "Value", "P&L", "P&L %"].map((h) => (
              <th key={h} className="px-3 py-2 border-b text-xs font-semibold text-gray-500">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const pnl    = r.unrealized_pnl;
            const pnlPct = r.unrealized_pnl_pct;
            const green  = (pnl ?? 0) >= 0;
            return (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-3 py-2 border-b font-mono font-semibold">{r.symbol}</td>
                <td className="px-3 py-2 border-b text-gray-400">{r.exchange}</td>
                <td className="px-3 py-2 border-b">{r.total_quantity}</td>
                <td className="px-3 py-2 border-b font-mono">{fmt(r.avg_buy_price)}</td>
                <td className="px-3 py-2 border-b font-mono">{fmt(r.total_invested)}</td>
                <td className="px-3 py-2 border-b font-mono">{fmt(r.current_price)}</td>
                <td className="px-3 py-2 border-b font-mono">{fmt(r.current_value)}</td>
                <td className={`px-3 py-2 border-b font-mono ${pnl == null ? "text-gray-400" : green ? "text-green-600" : "text-red-600"}`}>{fmt(pnl)}</td>
                <td className={`px-3 py-2 border-b font-mono ${pnlPct == null ? "text-gray-400" : green ? "text-green-600" : "text-red-600"}`}>
                  {pnlPct != null ? `${green ? "+" : ""}${pnlPct.toFixed(2)}%` : "—"}
                </td>
              </tr>
            );
          })}
          {rows.length === 0 && (
            <tr><td colSpan={9} className="px-3 py-8 text-center text-gray-400">No holdings. Add trades via the Trades page.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
