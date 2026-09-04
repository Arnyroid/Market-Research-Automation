import React, { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

interface RiskProfile {
  time_horizon: string;
  loss_tolerance: string;
  experience_level: string;
  updated_at: string;
}

export default function RiskProfilePage() {
  const [profile, setProfile] = useState<RiskProfile | null>(null);
  const [saved, setSaved]     = useState(false);

  useEffect(() => {
    apiFetch<RiskProfile>("/risk-profile").then(setProfile).catch(console.error);
  }, []);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!profile) return;
    const updated = await apiFetch<RiskProfile>("/risk-profile", {
      method: "PUT",
      body: JSON.stringify({
        time_horizon: profile.time_horizon,
        loss_tolerance: profile.loss_tolerance,
        experience_level: profile.experience_level,
      }),
    });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!profile) return <div className="p-6 text-gray-400">Loading…</div>;

  return (
    <div className="p-6 max-w-md mx-auto">
      <h1 className="text-2xl font-bold mb-2">Risk Profile</h1>
      <p className="text-sm text-gray-500 mb-6">
        Your risk profile shapes AI analysis. Review it quarterly as your circumstances change.
      </p>

      <form onSubmit={handleSave} className="space-y-5">
        <div>
          <label className="block text-sm font-medium mb-1">Investment Time Horizon</label>
          <select className="w-full border rounded px-3 py-2 text-sm" value={profile.time_horizon}
            onChange={(e) => setProfile({ ...profile, time_horizon: e.target.value })}>
            <option value="short">Short (&lt; 1 year)</option>
            <option value="medium">Medium (1–5 years)</option>
            <option value="long">Long (5+ years)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Loss Tolerance</label>
          <select className="w-full border rounded px-3 py-2 text-sm" value={profile.loss_tolerance}
            onChange={(e) => setProfile({ ...profile, loss_tolerance: e.target.value })}>
            <option value="low">Low — I'm uncomfortable with losses</option>
            <option value="medium">Medium — I can tolerate moderate drawdowns</option>
            <option value="high">High — Long-term focus, can absorb volatility</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Experience Level</label>
          <select className="w-full border rounded px-3 py-2 text-sm" value={profile.experience_level}
            onChange={(e) => setProfile({ ...profile, experience_level: e.target.value })}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="experienced">Experienced</option>
          </select>
        </div>

        <button type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded text-sm hover:bg-blue-700">
          {saved ? "✓ Saved" : "Save Profile"}
        </button>
      </form>

      <p className="text-xs text-gray-400 mt-4">Last updated: {profile.updated_at.slice(0, 10)}</p>
    </div>
  );
}
