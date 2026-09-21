"use client";

import { ArrowRight, Clock3, Database, Rows3 } from "lucide-react";
import { useEffect, useState } from "react";
import { UploadDialog } from "@/components/upload-dialog";
import { Button } from "@/components/ui/button";
import { type Dataset, listDatasets } from "@/lib/api";

export function DatasetLibrary() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    listDatasets(controller.signal)
      .then((items) => { setDatasets(items); setStatus("ready"); })
      .catch((error: Error) => {
        if (error.name !== "AbortError") setStatus("error");
      });
    return () => controller.abort();
  }, []);

  function addDataset(dataset: Dataset) {
    setDatasets((current) => [dataset, ...current.filter((item) => item.id !== dataset.id)]);
    setStatus("ready");
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>Your datasets</h1>
          <p className="lede">Upload a source, check its shape and quality, then begin an analysis.</p>
        </div>
        <UploadDialog onUploaded={addDataset} />
      </div>

      <section className="library-panel" aria-labelledby="recent-heading">
        <div className="section-heading">
          <div>
            <h2 id="recent-heading">Recent datasets</h2>
            <p>Sources available for analysis in this workspace.</p>
          </div>
          <span className="count-label">{datasets.length} {datasets.length === 1 ? "dataset" : "datasets"}</span>
        </div>

        <div className="dataset-list">
          {status === "loading" && <LibrarySkeleton />}
          {status === "error" && (
            <div className="library-message"><strong>Couldn&apos;t reach the data service</strong><span>Start the backend, then refresh this page.</span></div>
          )}
          {status === "ready" && datasets.length === 0 && (
            <div className="library-message"><strong>No datasets yet</strong><span>Upload a source or begin with the ecommerce sample below.</span></div>
          )}
          {datasets.map((dataset) => (
            <article className="dataset-row" key={dataset.name}>
              <span className="dataset-glyph"><Database size={19} /></span>
              <div className="dataset-copy">
                <h3>{dataset.name}</h3>
                <p>{dataset.description ?? dataset.original_filename}</p>
              </div>
              <dl className="dataset-meta">
                <div><Rows3 size={13} /><dt className="sr-only">Rows</dt><dd>{dataset.row_count.toLocaleString()} rows</dd></div>
                <div><Database size={13} /><dt className="sr-only">Columns</dt><dd>{dataset.column_count} columns</dd></div>
                <div><Clock3 size={13} /><dt className="sr-only">Updated</dt><dd>{relativeDate(dataset.updated_at)}</dd></div>
              </dl>
              <Button variant="ghost" size="small" aria-label={`Open ${dataset.name}`}><ArrowRight size={16} /></Button>
            </article>
          ))}
        </div>
      </section>

      <aside className="sample-callout">
        <div>
          <strong>New to SignalDesk?</strong>
          <p>Open the ecommerce sample to see how profiles and analysis fit together.</p>
        </div>
        <Button variant="secondary" size="small">Explore sample data</Button>
      </aside>
    </>
  );
}

function LibrarySkeleton() {
  return <div className="dataset-row skeleton-row" aria-label="Loading datasets"><span /><span /><span /></div>;
}

function relativeDate(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(elapsed / 60_000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
