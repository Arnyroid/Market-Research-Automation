import { NavLink, Route, Routes } from "react-router-dom";
import { LayoutDashboard, Bell, TrendingUp, ShieldCheck, Briefcase } from "lucide-react";
import WatchlistPage   from "./pages/Watchlist";
import PortfolioPage   from "./pages/Portfolio";
import AlertsPage      from "./pages/Alerts";
import StockDetailPage from "./pages/StockDetail";
import RiskProfilePage from "./pages/RiskProfile";

const NAV = [
  { to: "/",          label: "Watchlist",     icon: LayoutDashboard },
  { to: "/portfolio", label: "Portfolio",     icon: Briefcase },
  { to: "/alerts",    label: "Alerts",        icon: Bell },
  { to: "/risk",      label: "Risk Profile",  icon: ShieldCheck },
];

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">

      {/* ── Sidebar ───────────────────────────────────────────── */}
      <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <TrendingUp size={20} className="text-blue-400" />
            <span className="font-bold text-white text-base tracking-tight">StockAI</span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">Indian Equities Tracker</p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-800">
          <p className="text-xs text-gray-600">NSE &amp; BSE · IST 9:15–15:30</p>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/"              element={<WatchlistPage />} />
          <Route path="/portfolio"     element={<PortfolioPage />} />
          <Route path="/alerts"        element={<AlertsPage />} />
          <Route path="/stock/:symbol" element={<StockDetailPage />} />
          <Route path="/risk"          element={<RiskProfilePage />} />
        </Routes>
      </main>

    </div>
  );
}
