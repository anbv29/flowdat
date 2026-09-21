"use client";

import { Braces, Calendar, Hash, KeyRound, Search, Shapes, Table2 } from "lucide-react";
import { useMemo, useState } from "react";
import type { DatasetColumn, DatasetDetail } from "@/lib/api";

type ProfileTab = "schema" | "preview";

const semanticIcons = {
  identifier: KeyRound,
  measure: Hash,
  category: Shapes,
  date: Calendar,
};

export function DatasetProfile({ dataset }: { dataset: DatasetDetail }) {
  const [tab, setTab] = useState<ProfileTab>("schema");
  const [search, setSearch] = useState("");
  const visibleColumns = useMemo(
    () => dataset.columns.filter((column) => column.name.toLowerCase().includes(search.toLowerCase())),
    [dataset.columns, search],
  );

  return (
    <section className="profile-section" aria-labelledby="profile-heading">
      <div className="profile-toolbar">
        <div>
          <p className="eyebrow">Contents</p>
          <h2 id="profile-heading">Inspect this dataset</h2>
        </div>
        <div className="profile-tabs" role="tablist" aria-label="Dataset contents">
          <button
            className={tab === "schema" ? "is-active" : ""}
            type="button"
            role="tab"
            aria-selected={tab === "schema"}
            onClick={() => setTab("schema")}
          >
            <Braces size={14} /> Schema
          </button>
          <button
            className={tab === "preview" ? "is-active" : ""}
            type="button"
            role="tab"
            aria-selected={tab === "preview"}
            onClick={() => setTab("preview")}
          >
            <Table2 size={14} /> Data preview
          </button>
        </div>
      </div>

      {tab === "schema" ? (
        <div role="tabpanel">
          <label className="column-search">
            <Search size={14} />
            <span className="sr-only">Find a column</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Find a column"
            />
          </label>
          <div className="schema-table-wrap">
            <table className="schema-table">
              <thead>
                <tr><th>Column</th><th>Role</th><th>Type</th><th>Complete</th><th>Unique</th><th>Observed values</th></tr>
              </thead>
              <tbody>
                {visibleColumns.map((column) => <SchemaRow column={column} rowCount={dataset.row_count} key={column.name} />)}
              </tbody>
            </table>
            {visibleColumns.length === 0 && <div className="no-columns">No columns match “{search}”.</div>}
          </div>
        </div>
      ) : (
        <div className="preview-table-wrap" role="tabpanel">
          <table className="preview-table">
            <thead><tr>{dataset.columns.map((column) => <th key={column.name}>{column.name}<span>{column.data_type}</span></th>)}</tr></thead>
            <tbody>
              {dataset.preview.map((row, index) => (
                <tr key={index}>{dataset.columns.map((column) => <td key={column.name}>{formatCell(row[column.name])}</td>)}</tr>
              ))}
            </tbody>
          </table>
          <div className="preview-caption">Showing {dataset.preview.length} profile rows. Queries always run against the complete dataset.</div>
        </div>
      )}
    </section>
  );
}

function SchemaRow({ column, rowCount }: { column: DatasetColumn; rowCount: number }) {
  const Icon = semanticIcons[column.semantic_type];
  const complete = rowCount ? ((rowCount - column.null_count) / rowCount) * 100 : 100;
  const observed = describeObservedValues(column);
  return (
    <tr>
      <td><strong>{column.name}</strong></td>
      <td><span className={`semantic-label is-${column.semantic_type}`}><Icon size={12} />{column.semantic_type}</span></td>
      <td><code>{column.data_type}</code></td>
      <td>
        <div className="completeness-cell"><span>{complete.toFixed(1)}%</span><i><b style={{ width: `${complete}%` }} /></i></div>
      </td>
      <td>{column.distinct_count.toLocaleString()}</td>
      <td className="observed-cell">{observed}</td>
    </tr>
  );
}

function describeObservedValues(column: DatasetColumn) {
  const minimum = column.statistics.min;
  const maximum = column.statistics.max;
  if (minimum !== undefined && minimum !== null && maximum !== undefined && maximum !== null) {
    return `${formatCell(minimum)} — ${formatCell(maximum)}`;
  }
  return column.sample_values.slice(0, 3).map(formatCell).join(" · ") || "No non-null values";
}

export function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (typeof value === "boolean") return value ? "True" : "False";
  return String(value);
}
