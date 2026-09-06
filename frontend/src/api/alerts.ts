import { apiFetch } from "./client";

export interface Alert {
  id: number;
  symbol: string;
  exchange: string;
  condition_type: string;
  threshold: number;
  active: boolean;
  repeating: boolean;
  notes: string | null;
  created_at: string;
}

export interface AlertLog {
  id: number;
  alert_id: number;
  triggered_at: string;
  price_at_trigger: number;
  notified: boolean;
}

export interface CreateAlertPayload {
  symbol: string;
  exchange: string;
  condition_type: "price_above" | "price_below" | "pct_change_up" | "pct_change_down" | "portfolio_pnl_below";
  threshold: number;
  notes?: string;
}

export const alertsApi = {
  list:    (activeOnly = false) => apiFetch<Alert[]>(`/alerts?active_only=${activeOnly}`),
  create:  (p: CreateAlertPayload) => apiFetch<Alert>("/alerts", { method: "POST", body: JSON.stringify(p) }),
  update:  (id: number, p: Partial<Pick<Alert, "threshold" | "active" | "notes">>) =>
    apiFetch<Alert>(`/alerts/${id}`, { method: "PUT", body: JSON.stringify(p) }),
  remove:  (id: number) => apiFetch<void>(`/alerts/${id}`, { method: "DELETE" }),
  getLogs: (id: number) => apiFetch<AlertLog[]>(`/alerts/${id}/log`),
};
