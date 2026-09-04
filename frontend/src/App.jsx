import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { WatchlistPage } from './pages/WatchlistPage';
import { AlertsPage } from './pages/AlertsPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-8">
                <h1 className="text-2xl font-bold text-blue-600">📈 Stock Watchlist</h1>
                <div className="flex gap-4">
                  <Link to="/" className="text-gray-700 hover:text-blue-600">
                    Watchlist
                  </Link>
                  <Link to="/alerts" className="text-gray-700 hover:text-blue-600">
                    Alerts
                  </Link>
                </div>
              </div>
              <div className="text-sm text-gray-500">
                v1.0.0 - Personal Stock Watchlist & AI Trading Assistant
              </div>
            </div>
          </div>
        </nav>

        {/* Routes */}
        <Routes>
          <Route path="/" element={<WatchlistPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
        </Routes>

        {/* Footer */}
        <footer className="bg-white border-t mt-12">
          <div className="max-w-7xl mx-auto px-6 py-4 text-center text-sm text-gray-600">
            <p>⚠️ Educational purposes only. Not financial advice.</p>
            <p>Always do your own research before making investment decisions.</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
