/**
 * usePriceSocket — connects to the backend WebSocket and keeps a live
 * map of symbol → { ltp, pct_change } updated every ~60 seconds.
 */
import { useEffect, useRef, useState } from "react";
import { WS_URL } from "../api/client";

export interface LivePrice {
  symbol: string;
  exchange: string;
  ltp: number;
  pct_change: number | null;
}

export function usePriceSocket(): Map<string, LivePrice> {
  const [prices, setPrices] = useState<Map<string, LivePrice>>(new Map());
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`${WS_URL}/prices/ws/prices`);
      wsRef.current = ws;

      ws.onmessage = (evt) => {
        try {
          const items: LivePrice[] = JSON.parse(evt.data);
          setPrices((prev) => {
            const next = new Map(prev);
            items.forEach((p) => next.set(`${p.symbol}:${p.exchange}`, p));
            return next;
          });
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        // Auto-reconnect after 5 s
        setTimeout(connect, 5_000);
      };
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  return prices;
}
