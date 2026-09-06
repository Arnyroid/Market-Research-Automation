import { apiFetch } from "./client";

export interface CorporateActionOut {
  id: number;
  action_date: string;
  symbol: string;
  exchange: string;
  company_name: string | null;
  action_type: "DIVIDEND" | "BONUS" | "SPLIT" | "RIGHTS";
  quantity: number | null;
  amount: number | null;
  ratio: string | null;
  notes: string | null;
}

export const corporateActionsApi = {
  list: (symbol?: string) =>
    apiFetch<CorporateActionOut[]>(
      `/corporate-actions${symbol ? `?symbol=${symbol}` : ""}`
    ),
};
