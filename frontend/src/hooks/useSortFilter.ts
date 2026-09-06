/**
 * useSortFilter — generic sort + filter hook for table data.
 *
 * Usage:
 *   const { filtered, sortKey, sortDir, setSort, filterText, setFilterText }
 *     = useSortFilter(rows, { textKeys: ["symbol","company_name"], getValue })
 */
import { useMemo, useState } from "react";

export type SortDir = "asc" | "desc";

export interface SortFilterOptions<T> {
  /** Keys to search when the user types in the filter box */
  textKeys: (keyof T)[];
  /** Extra filter predicates beyond text search */
  extraFilter?: (row: T) => boolean;
  /** Map a sort key name to a numeric/string value for comparison */
  getValue: (row: T, key: string) => string | number | null | undefined;
  /** Initial sort key */
  defaultSortKey?: string;
  /** Initial sort direction */
  defaultSortDir?: SortDir;
}

export function useSortFilter<T>(
  data: T[],
  opts: SortFilterOptions<T>
) {
  const [filterText, setFilterText] = useState("");
  const [extraFilters, setExtraFilters] = useState<Record<string, string>>({});
  const [sortKey, setSortKey]       = useState(opts.defaultSortKey ?? "");
  const [sortDir, setSortDir]       = useState<SortDir>(opts.defaultSortDir ?? "asc");

  function setSort(key: string) {
    setSortKey(prev => {
      if (prev === key) {
        setSortDir(d => d === "asc" ? "desc" : "asc");
        return key;
      }
      setSortDir("asc");
      return key;
    });
  }

  function setExtraFilter(key: string, value: string) {
    setExtraFilters(prev => ({ ...prev, [key]: value }));
  }

  const filtered = useMemo(() => {
    let rows = data;

    // Text filter
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase();
      rows = rows.filter(row =>
        opts.textKeys.some(k => {
          const v = row[k];
          return v != null && String(v).toLowerCase().includes(q);
        })
      );
    }

    // Extra predicate
    if (opts.extraFilter) {
      rows = rows.filter(opts.extraFilter);
    }

    // Extra key=value filters
    Object.entries(extraFilters).forEach(([k, v]) => {
      if (v && v !== "all") {
        rows = rows.filter(row => {
          const val = opts.getValue(row, k);
          return val != null && String(val).toLowerCase() === v.toLowerCase();
        });
      }
    });

    // Sort
    if (sortKey) {
      rows = [...rows].sort((a, b) => {
        const av = opts.getValue(a, sortKey) ?? "";
        const bv = opts.getValue(b, sortKey) ?? "";
        let cmp = 0;
        if (typeof av === "number" && typeof bv === "number") {
          cmp = av - bv;
        } else {
          cmp = String(av).localeCompare(String(bv), "en-IN", { numeric: true });
        }
        return sortDir === "asc" ? cmp : -cmp;
      });
    }

    return rows;
  }, [data, filterText, extraFilters, sortKey, sortDir]);

  return { filtered, filterText, setFilterText, extraFilters, setExtraFilter, sortKey, sortDir, setSort };
}
