import { NavLink, Route, Routes } from "react-router-dom";
import { LayoutDashboard, Bell, TrendingUp, ShieldCheck, Briefcase, BarChart2 } from "lucide-react";
import WatchlistPage   from "./pages/Watchlist";
import PortfolioPage   from "./pages/Portfolio";
import AlertsPage      from "./pages/Alerts";
import StockDetailPage from "./pages/StockDetail";
import RiskProfilePage from "./pages/RiskProfile";
import IndustryPage    from "./pages/Industry";

const NAV = [
  { to: "/",          label: "Watchlist",     icon: LayoutDashboard },
  { to: "/portfolio", label: "Portfolio",     icon: Briefcase },
  { to: "/industry",  label: "Industries",    icon: BarChart2 },
  { to: "/alerts",    label: "Alerts",        icon: Bell },
  { to: "/risk",      label: "Risk Profile",  icon: ShieldCheck },
];

// ── Market open/closed dot ─────────────────────────────────────────────────────

function MarketStatusDot() {
  const now = new Date();
  // Current time in IST (Asia/Kolkata = UTC+5:30)
  const istParts = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "numeric",
    minute: "numeric",
    hour12: false,
    weekday: "short",
  }).formatToParts(now);

  const get = (type: string) => istParts.find(p => p.type === type)?.value ?? "";
  const weekday = get("weekday"); // "Mon", "Tue", …
  const h = parseInt(get("hour"), 10);
  const m = parseInt(get("minute"), 10);
  const minutes = h * 60 + m;

  // NSE/BSE: Mon–Fri 9:15–15:30 IST; closed on weekends
  const isWeekday = weekday !== "Sun" && weekday !== "Sat";
  const open = isWeekday && minutes >= 9 * 60 + 15 && minutes < 15 * 60 + 30;

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`w-1.5 h-1.5 rounded-full ${open ? "bg-emerald-400" : "bg-gray-500"}`}
      />
      <span className="text-xs text-gray-600">
        Market {open ? "Open" : "Closed"}
      </span>
    </div>
  );
}

// ── 404 page ───────────────────────────────────────────────────────────────────

function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-32 text-center">
      <p className="text-6xl font-bold text-gray-700 mb-4">404</p>
      <p className="text-lg font-semibold text-white mb-2">Page not found</p>
      <p className="text-gray-400 text-sm mb-8">
        The page you're looking for doesn't exist.
      </p>
      <a href="/" className="btn-primary text-sm">Go to Watchlist</a>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────────

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

        {/* Footer — live market status dot */}
        <div className="px-5 py-4 border-t border-gray-800">
          <MarketStatusDot />
          <p className="text-xs text-gray-700 mt-0.5">NSE &amp; BSE · 9:15–15:30 IST</p>
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
          <Route path="/industry"      element={<IndustryPage />} />
          <Route path="*"              element={<NotFoundPage />} />
        </Routes>
      </main>

    </div>
  );
}
