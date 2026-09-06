/**
 * usePriceSocket — connects to the backend WebSocket and keeps a live
 * map of symbol → { ltp, pct_change, lastUpdated } updated every ~60 seconds.
 * Also exposes a `connected` boolean so the UI can show a stale indicator.
 */
import { useEffect, useRef, useState } from "react";
import { WS_URL } from "../api/client";

export interface LivePrice {
  symbol: string;
  exchange: string;
  ltp: number;
  pct_change: number | null;
  /** epoch ms of the last received update for this symbol */
  lastUpdated: number;
}

export interface PriceSocketResult {
  prices: Map<string, LivePrice>;
  /** true while the WebSocket is in OPEN state */
  connected: boolean;
}

export function usePriceSocket(): PriceSocketResult {
  const [prices, setPrices]       = useState<Map<string, LivePrice>>(new Map());
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      if (cancelled) return;
      const ws = new WebSocket(`${WS_URL}/prices/ws/prices`);
      wsRef.current = ws;

      ws.onopen = () => { if (!cancelled) setConnected(true); };

      ws.onmessage = (evt) => {
        try {
          const now  = Date.now();
          const items: Omit<LivePrice, "lastUpdated">[] = JSON.parse(evt.data);
          setPrices((prev) => {
            const next = new Map(prev);
            items.forEach((p) => next.set(`${p.symbol}:${p.exchange}`, { ...p, lastUpdated: now }));
            return next;
          });
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          // Auto-reconnect after 5 s, but only if this effect is still mounted
          reconnectTimer = setTimeout(connect, 5_000);
        }
      };
    }

    connect();

    return () => {
      // Mark as cancelled so the reconnect timer never opens a new socket
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  return { prices, connected };
}
