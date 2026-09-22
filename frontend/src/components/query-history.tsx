"use client";

import { CheckCircle2, Clock3, Database, Search, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { type QueryRunHistoryItem, listQueryRuns } from "@/lib/api";

export function QueryHistory() {
  const [items, setItems] = useState<QueryRunHistoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    listQueryRuns().then((runs) => { setItems(runs); setStatus("ready"); }).catch(() => setStatus("error"));
  }, []);
  const visible = useMemo(() => items.filter((item) => `${item.user_question} ${item.dataset_name}`.toLowerCase().includes(query.toLowerCase())), [items, query]);

  return <>
    <div className="page-heading"><div><p className="eyebrow">Audit trail</p><h1>Query history</h1><p className="lede">Review questions, execution outcomes, and the datasets behind them.</p></div></div>
    <section className="history-panel">
      <div className="history-toolbar"><label><Search size={14} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search questions or datasets" /></label><span>{visible.length} runs</span></div>
      {status === "loading" && <div className="library-message">Loading query history…</div>}
      {status === "error" && <div className="library-message"><strong>History is unavailable</strong><span>Check the API and refresh this page.</span></div>}
      {status === "ready" && visible.length === 0 && <div className="library-message"><strong>No matching queries</strong><span>Completed analyses will be recorded here.</span></div>}
      <div className="history-list">{visible.map((item) => <article key={item.id} className="history-row">
        <span className={`run-status is-${item.execution_status}`}>{item.execution_status === "completed" ? <CheckCircle2 size={15} /> : <ShieldAlert size={15} />}</span>
        <div><h2>{item.user_question}</h2><p>{item.answer_summary ?? statusCopy(item.execution_status)}</p><div className="history-meta"><span><Database size={11} />{item.dataset_name}</span><span><Clock3 size={11} />{formatDate(item.created_at)}</span>{item.execution_time_ms !== null && <span>{item.execution_time_ms.toFixed(1)} ms</span>}</div></div>
        <Link href={`/analysis?dataset=${item.dataset_id}`}>Open analysis</Link>
      </article>)}</div>
    </section>
  </>;
}

function statusCopy(status: string) {
  if (status === "needs_clarification") return "Waiting for clarification.";
  if (status === "rejected") return "The generated query did not pass safety validation.";
  if (status === "failed") return "Execution did not complete.";
  return "Analysis plan prepared.";
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
