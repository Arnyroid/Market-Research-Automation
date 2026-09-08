import { memo, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { LayoutDashboard, Bell, TrendingUp, ShieldCheck, Briefcase, BarChart2, Menu, X, Coins, Home } from "lucide-react";
import HomePage        from "./pages/Home";
import WatchlistPage   from "./pages/Watchlist";
import PortfolioPage   from "./pages/Portfolio";
import AlertsPage      from "./pages/Alerts";
import StockDetailPage from "./pages/StockDetail";
import RiskProfilePage from "./pages/RiskProfile";
import IndustryPage    from "./pages/Industry";
import PennyStocksPage from "./pages/PennyStocks";

const NAV = [
  { to: "/home",      label: "Home",          icon: Home },
  { to: "/watchlist", label: "Watchlist",     icon: LayoutDashboard },
  { to: "/portfolio", label: "Portfolio",     icon: Briefcase },
  { to: "/industry",  label: "Industries",    icon: BarChart2 },
  { to: "/penny",     label: "Penny Stocks",  icon: Coins },
  { to: "/alerts",    label: "Alerts",        icon: Bell },
  { to: "/risk",      label: "Risk Profile",  icon: ShieldCheck },
];

// ── Market open/closed dot ─────────────────────────────────────────────────────

/** Derive IST market-open state and the ms until it next flips. */
function _getMarketState(): { open: boolean; msUntilFlip: number } {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "numeric", minute: "numeric", hour12: false, weekday: "short",
  });
  const parts  = fmt.formatToParts(now);
  const get    = (t: string) => parts.find(p => p.type === t)?.value ?? "";
  const weekday = get("weekday");
  const h      = parseInt(get("hour"),   10);
  const m      = parseInt(get("minute"), 10);
  const minutes = h * 60 + m;

  const isWeekday = weekday !== "Sun" && weekday !== "Sat";
  const OPEN_MIN  = 9 * 60 + 15;   // 09:15
  const CLOSE_MIN = 15 * 60 + 30;  // 15:30
  const open = isWeekday && minutes >= OPEN_MIN && minutes < CLOSE_MIN;

  // ms until the state flips next (open→close or close→open on next weekday)
  let minsUntilFlip: number;
  if (open) {
    minsUntilFlip = CLOSE_MIN - minutes;
  } else if (isWeekday && minutes < OPEN_MIN) {
    minsUntilFlip = OPEN_MIN - minutes;
  } else {
    // After close or weekend — next open is Monday (or next day) at 09:15
    const daysUntilMon = weekday === "Sat" ? 2 : weekday === "Sun" ? 1 : 1;
    minsUntilFlip = daysUntilMon * 24 * 60 - minutes + OPEN_MIN;
  }

  // Add 1 min buffer so the flip fires after the boundary, not right on it
  return { open, msUntilFlip: (minsUntilFlip + 1) * 60 * 1000 };
}

// memo: re-renders only when the parent forces it — never on drawerOpen toggles
const MarketStatusDot = memo(function MarketStatusDot() {
  const [open, setOpen] = useState(() => _getMarketState().open);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;

    function schedule() {
      const { open: isOpen, msUntilFlip } = _getMarketState();
      setOpen(isOpen);
      timer = setTimeout(() => { schedule(); }, msUntilFlip);
    }

    schedule();
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-1.5 h-1.5 rounded-full ${open ? "bg-emerald-400" : "bg-gray-500"}`} />
      <span className="text-xs text-gray-600">Market {open ? "Open" : "Closed"}</span>
    </div>
  );
});

// ── 404 page ───────────────────────────────────────────────────────────────────

function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full py-32 text-center">
      <p className="text-6xl font-bold text-gray-700 mb-4">404</p>
      <p className="text-lg font-semibold text-white mb-2">Page not found</p>
      <p className="text-gray-400 text-sm mb-8">
        The page you're looking for doesn't exist.
      </p>
      <a href="/home" className="btn-primary text-sm">Go to Home</a>
    </div>
  );
}

// ── Sidebar nav content (shared between desktop + mobile drawer) ───────────────

function SidebarContent({ onNavClick }: { onNavClick?: () => void }) {
  return (
    <>
      {/* Logo — click navigates to /home */}
      <div className="px-5 py-5 border-b border-gray-800">
        <Link to="/home" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <TrendingUp size={20} className="text-blue-400" />
          <span className="font-bold text-white text-base tracking-tight">StockAI</span>
        </Link>
        <p className="text-xs text-gray-500 mt-0.5">Indian Equities Tracker</p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            onClick={onNavClick}
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
    </>
  );
}

// ── App ────────────────────────────────────────────────────────────────────────

export default function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">

      {/* ── Desktop sidebar (hidden on mobile) ────────────────── */}
      <aside className="w-56 shrink-0 bg-gray-900 border-r border-gray-800 flex-col hidden md:flex">
        <SidebarContent />
      </aside>

      {/* ── Mobile drawer overlay ──────────────────────────────── */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={() => setDrawerOpen(false)}
          aria-label="Close menu"
        />
      )}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-56 bg-gray-900 border-r border-gray-800 flex flex-col
          transform transition-transform duration-200 ease-in-out md:hidden
          ${drawerOpen ? "translate-x-0" : "-translate-x-full"}`}
        aria-hidden={!drawerOpen}
      >
        {/* Close button inside drawer */}
        <button
          onClick={() => setDrawerOpen(false)}
          className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors"
          aria-label="Close menu"
        >
          <X size={18} />
        </button>
        <SidebarContent onNavClick={() => setDrawerOpen(false)} />
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        {/* Mobile top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 md:hidden bg-gray-900">
          <button
            onClick={() => setDrawerOpen(true)}
            className="text-gray-400 hover:text-white transition-colors"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <Link to="/home" className="flex items-center gap-1.5 hover:opacity-80 transition-opacity">
            <TrendingUp size={16} className="text-blue-400" />
            <span className="font-bold text-white text-sm tracking-tight">StockAI</span>
          </Link>
        </div>

        <Routes>
          <Route path="/"              element={<HomePage />} />
          <Route path="/home"          element={<HomePage />} />
          <Route path="/watchlist"     element={<WatchlistPage />} />
          <Route path="/portfolio"     element={<PortfolioPage />} />
          <Route path="/alerts"        element={<AlertsPage />} />
          <Route path="/stock/:symbol" element={<StockDetailPage />} />
          <Route path="/risk"          element={<RiskProfilePage />} />
          <Route path="/industry"      element={<IndustryPage />} />
          <Route path="/penny"         element={<PennyStocksPage />} />
          <Route path="*"              element={<NotFoundPage />} />
        </Routes>
      </main>

    </div>
  );
}
