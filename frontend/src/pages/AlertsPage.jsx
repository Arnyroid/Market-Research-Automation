import React, { useState, useEffect } from 'react';
import { alertsAPI, watchlistAPI } from '../api/client';

export function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    symbol: '',
    exchange: 'NSE',
    condition_type: 'price_above',
    threshold: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [alertsRes, watchlistRes] = await Promise.all([
        alertsAPI.getAll(),
        watchlistAPI.getAll(),
      ]);
      setAlerts(alertsRes.data);
      setWatchlist(watchlistRes.data);
      setError(null);
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAlert = async (e) => {
    e.preventDefault();
    if (!formData.symbol || !formData.threshold) {
      setError('Please fill all fields');
      return;
    }

    try {
      setLoading(true);
      await alertsAPI.create({
        symbol: formData.symbol,
        exchange: formData.exchange,
        condition_type: formData.condition_type,
        threshold: parseFloat(formData.threshold),
      });
      setFormData({
        symbol: '',
        exchange: 'NSE',
        condition_type: 'price_above',
        threshold: '',
      });
      fetchData();
    } catch (err) {
      setError('Failed to create alert');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAlert = async (id, active) => {
    try {
      await alertsAPI.update(id, { active: !active });
      fetchData();
    } catch (err) {
      setError('Failed to update alert');
      console.error(err);
    }
  };

  const handleDeleteAlert = async (id) => {
    try {
      await alertsAPI.delete(id);
      fetchData();
    } catch (err) {
      setError('Failed to delete alert');
      console.error(err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">🔔 Price Alerts</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg p-6 shadow-sm mb-6">
        <h2 className="text-lg font-semibold mb-4">Create New Alert</h2>
        <form onSubmit={handleAddAlert} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Symbol</label>
              <select
                value={formData.symbol}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    symbol: e.target.value,
                    exchange: watchlist.find((w) => w.symbol === e.target.value)?.exchange || 'NSE',
                  })
                }
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="">Select symbol</option>
                {watchlist.map((item) => (
                  <option key={item.id} value={item.symbol}>
                    {item.symbol}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Condition</label>
              <select
                value={formData.condition_type}
                onChange={(e) =>
                  setFormData({ ...formData, condition_type: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="price_above">Price Above</option>
                <option value="price_below">Price Below</option>
                <option value="pct_change">% Change</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Threshold</label>
              <input
                type="number"
                step="0.01"
                value={formData.threshold}
                onChange={(e) =>
                  setFormData({ ...formData, threshold: e.target.value })
                }
                placeholder="Enter threshold value"
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
              >
                Create Alert
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="space-y-2">
        {alerts.map((alert) => (
          <div key={alert.id} className="bg-white border rounded-lg p-4 flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-semibold">{alert.symbol}</h3>
              <p className="text-sm text-gray-600">
                {alert.condition_type === 'price_above' && `Price above ₹${alert.threshold}`}
                {alert.condition_type === 'price_below' && `Price below ₹${alert.threshold}`}
                {alert.condition_type === 'pct_change' && `Change {alert.threshold}%`}
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleToggleAlert(alert.id, alert.active)}
                className={`px-3 py-1 rounded text-sm ${
                  alert.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                }`}
              >
                {alert.active ? 'Active' : 'Inactive'}
              </button>
              <button
                onClick={() => handleDeleteAlert(alert.id)}
                className="px-3 py-1 text-red-600 hover:text-red-700 text-sm"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {alerts.length === 0 && !loading && (
        <div className="text-center text-gray-500 py-8">
          No alerts yet. Create one to get started!
        </div>
      )}
    </div>
  );
}
