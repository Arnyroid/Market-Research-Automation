import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import WatchlistPage  from "./pages/Watchlist";
import PortfolioPage  from "./pages/Portfolio";
import AlertsPage     from "./pages/Alerts";
import StockDetailPage from "./pages/StockDetail";
import RiskProfilePage from "./pages/RiskProfile";
import clsx from "clsx";

const NAV = [
  { to: "/",           label: "Watchlist" },
  { to: "/portfolio",  label: "Portfolio" },
  { to: "/alerts",     label: "Alerts"    },
  { to: "/risk",       label: "Risk Profile" },
];

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 font-sans">
        {/* Top nav */}
        <nav className="bg-white border-b px-6 py-3 flex items-center gap-6">
          <span className="font-bold text-blue-600 mr-4">📈 StockAI</span>
          {NAV.map(({ to, label }) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => clsx(
                "text-sm font-medium transition-colors",
                isActive ? "text-blue-600" : "text-gray-500 hover:text-gray-900"
              )}>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Page content */}
        <main>
          <Routes>
            <Route path="/"              element={<WatchlistPage />} />
            <Route path="/portfolio"     element={<PortfolioPage />} />
            <Route path="/alerts"        element={<AlertsPage />} />
            <Route path="/stock/:symbol" element={<StockDetailPage />} />
            <Route path="/risk"          element={<RiskProfilePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
