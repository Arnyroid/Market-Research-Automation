import React, { useState, useEffect } from 'react';
import { watchlistAPI, pricesAPI, analysisAPI } from '../api/client';

export function WatchlistPage() {
  const [watchlist, setWatchlist] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [newExchange, setNewExchange] = useState('NSE');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      const response = await watchlistAPI.getAll();
      setWatchlist(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load watchlist');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newSymbol.trim()) return;

    try {
      setLoading(true);
      await watchlistAPI.add(newSymbol.toUpperCase(), newExchange);
      setNewSymbol('');
      fetchWatchlist();
    } catch (err) {
      setError('Failed to add symbol');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (id) => {
    try {
      await watchlistAPI.remove(id);
      fetchWatchlist();
    } catch (err) {
      setError('Failed to remove symbol');
      console.error(err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">📊 Watchlist</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleAdd} className="mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Stock Symbol (e.g., RELIANCE)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            className="flex-1 px-4 py-2 border rounded-lg"
            disabled={loading}
          />
          <select
            value={newExchange}
            onChange={(e) => setNewExchange(e.target.value)}
            className="px-4 py-2 border rounded-lg"
            disabled={loading}
          >
            <option value="NSE">NSE</option>
            <option value="BSE">BSE</option>
          </select>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </form>

      {loading && <div className="text-center text-gray-500">Loading...</div>}

      <div className="grid gap-4">
        {watchlist.map((item) => (
          <WatchlistCard
            key={item.id}
            item={item}
            onRemove={handleRemove}
          />
        ))}
      </div>

      {watchlist.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-8">
          No stocks in watchlist yet. Add one to get started!
        </div>
      )}
    </div>
  );
}

function WatchlistCard({ item, onRemove }) {
  const [price, setPrice] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, [item.symbol]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [priceRes, analysisRes] = await Promise.all([
        pricesAPI.getCurrent(item.symbol),
        analysisAPI.getLatest(item.symbol).catch(() => null),
      ]);
      setPrice(priceRes.data);
      setAnalysis(analysisRes?.data || null);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (flag) => {
    switch (flag) {
      case 'low':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'high':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="text-lg font-semibold">{item.symbol}</h3>
          <p className="text-sm text-gray-600">{item.exchange}</p>
          
          {price && (
            <div className="mt-2">
              <p className="text-2xl font-bold">₹{price.current_price?.toFixed(2)}</p>
              <p className={price.pct_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                {price.pct_change >= 0 ? '+' : ''}{price.pct_change?.toFixed(2)}%
              </p>
            </div>
          )}

          {analysis && (
            <div className="mt-3 pt-3 border-t">
              <p className="text-sm">
                <span className={`font-semibold ${getRiskColor(analysis.risk_flag)}`}>
                  Risk: {analysis.risk_flag?.toUpperCase()}
                </span>
              </p>
              <p className="text-sm text-gray-600 mt-1">{analysis.llm_output}</p>
            </div>
          )}
        </div>

        <button
          onClick={() => onRemove(item.id)}
          className="text-red-500 hover:text-red-700 text-sm"
        >
          Remove
        </button>
      </div>
    </div>
  );
}
