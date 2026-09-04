import React, { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { Save, CheckCircle } from "lucide-react";

interface RiskProfile {
  time_horizon: string;
  loss_tolerance: string;
  experience_level: string;
  updated_at: string;
}

const HORIZONS    = [{ v:"short",        l:"Short-term  (< 1 year)" }, { v:"medium", l:"Medium-term  (1–5 years)" }, { v:"long", l:"Long-term  (5+ years)" }];
const TOLERANCES  = [{ v:"low",          l:"Low — uncomfortable with losses" }, { v:"medium", l:"Medium — can tolerate drawdowns" }, { v:"high", l:"High — long-term focus, absorb volatility" }];
const EXPERIENCE  = [{ v:"beginner",     l:"Beginner" }, { v:"intermediate", l:"Intermediate" }, { v:"experienced", l:"Experienced" }];

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
        time_horizon:     profile.time_horizon,
        loss_tolerance:   profile.loss_tolerance,
        experience_level: profile.experience_level,
      }),
    });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  if (!profile) return (
    <div className="p-8 flex items-center justify-center h-full">
      <p className="text-gray-500 text-sm">Loading…</p>
    </div>
  );

  function Field({ label, value, options, onChange }: {
    label: string; value: string;
    options: { v: string; l: string }[];
    onChange: (v: string) => void;
  }) {
    return (
      <div className="card">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{label}</p>
        <div className="space-y-2">
          {options.map(o => (
            <label key={o.v} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${value === o.v ? "border-blue-500 bg-blue-600/10" : "border-gray-700 hover:border-gray-600"}`}>
              <input type="radio" className="accent-blue-500" name={label} value={o.v} checked={value === o.v} onChange={() => onChange(o.v)} />
              <span className={`text-sm ${value === o.v ? "text-white" : "text-gray-300"}`}>{o.l}</span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Risk Profile</h1>
        <p className="text-gray-400 text-sm mt-1">
          Shapes how the AI frames analysis. Review quarterly as your circumstances change.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        <Field label="Investment Time Horizon" value={profile.time_horizon}
          options={HORIZONS} onChange={v => setProfile({ ...profile, time_horizon: v })} />
        <Field label="Loss Tolerance" value={profile.loss_tolerance}
          options={TOLERANCES} onChange={v => setProfile({ ...profile, loss_tolerance: v })} />
        <Field label="Experience Level" value={profile.experience_level}
          options={EXPERIENCE} onChange={v => setProfile({ ...profile, experience_level: v })} />

        <button type="submit" className={`btn-primary w-full justify-center py-3 ${saved ? "bg-emerald-600 hover:bg-emerald-600" : ""}`}>
          {saved ? <><CheckCircle size={16} /> Saved</> : <><Save size={16} /> Save Profile</>}
        </button>
      </form>

      <p className="text-xs text-gray-600 mt-4 text-center">
        Last updated: {new Date(profile.updated_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
      </p>
    </div>
  );
}
