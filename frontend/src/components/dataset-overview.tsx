"use client";

import {
  AlertCircle,
  ArrowLeft,
  CalendarDays,
  Database,
  FileSpreadsheet,
  Hash,
  MessageSquareText,
  Rows3,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { DatasetProfile } from "@/components/dataset-profile";
import { DatasetActions } from "@/components/dataset-actions";
import { type DatasetDetail, getDataset } from "@/lib/api";

export function DatasetOverview() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();
    getDataset(datasetId, controller.signal)
      .then((result) => {
        setDataset(result);
        setStatus("ready");
      })
      .catch((error: Error) => {
        if (error.name !== "AbortError") setStatus("error");
      });
    return () => controller.abort();
  }, [datasetId]);

  const missingCells = useMemo(
    () => dataset?.columns.reduce((total, column) => total + column.null_count, 0) ?? 0,
    [dataset],
  );

  if (status === "loading") return <OverviewSkeleton />;
  if (status === "error" || !dataset) return <OverviewError />;

  const totalCells = dataset.row_count * dataset.column_count;
  const completeness = totalCells ? 100 - (missingCells / totalCells) * 100 : 100;

  return (
    <>
      <Link className="back-link" href="/"><ArrowLeft size={14} /> All datasets</Link>

      <div className="dataset-titlebar">
        <div>
          <div className="dataset-kicker"><span className="status-dot" /> Profile ready</div>
          <h1>{dataset.name}</h1>
          <p className="lede">{dataset.description ?? `Profile for ${dataset.original_filename}`}</p>
        </div>
        <div className="dataset-actions"><DatasetActions datasetId={dataset.id} datasetName={dataset.name} /><Button asChild><Link href={`/analysis?dataset=${dataset.id}`}><MessageSquareText size={16} /> Ask a question</Link></Button></div>
      </div>

      <section className="metric-grid" aria-label="Dataset summary">
        <Metric icon={Rows3} label="Rows" value={dataset.row_count.toLocaleString()} />
        <Metric icon={Database} label="Columns" value={dataset.column_count.toLocaleString()} />
        <Metric icon={Hash} label="Completeness" value={`${completeness.toFixed(1)}%`} />
        <Metric icon={CalendarDays} label="Added" value={formatDate(dataset.created_at)} />
      </section>

      <section className="overview-grid">
        <div className="glass-section">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Profile</p>
              <h2>At a glance</h2>
            </div>
          </div>
          <dl className="profile-facts">
            <Fact label="Missing cells" value={missingCells.toLocaleString()} />
            <Fact label="Measures" value={countSemantic(dataset, "measure").toString()} />
            <Fact label="Categories" value={countSemantic(dataset, "category").toString()} />
            <Fact label="Date fields" value={countSemantic(dataset, "date").toString()} />
          </dl>
        </div>

        <div className="glass-section source-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Source</p>
              <h2>File details</h2>
            </div>
            <FileSpreadsheet size={18} />
          </div>
          <dl className="source-facts">
            <Fact label="Filename" value={dataset.original_filename} />
            <Fact label="Format" value={dataset.original_filename.split(".").at(-1)?.toUpperCase() ?? "Data"} />
            <Fact label="Size" value={formatBytes(dataset.size_bytes)} />
            <Fact label="Updated" value={formatDate(dataset.updated_at)} />
          </dl>
        </div>
      </section>

      <DatasetProfile dataset={dataset} />
    </>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Rows3; label: string; value: string }) {
  return (
    <div className="metric-card">
      <span><Icon size={16} /></span>
      <div><p>{label}</p><strong>{value}</strong></div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div><dt>{label}</dt><dd>{value}</dd></div>;
}

function countSemantic(dataset: DatasetDetail, semanticType: string) {
  return dataset.columns.filter((column) => column.semantic_type === semanticType).length;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function OverviewSkeleton() {
  return <div className="overview-loading" aria-label="Loading dataset"><span /><span /><span /><span /></div>;
}

function OverviewError() {
  return (
    <div className="overview-error">
      <AlertCircle size={22} />
      <h1>Dataset unavailable</h1>
      <p>SignalDesk could not load this profile. Check the data service and try again.</p>
      <Button variant="secondary" asChild><Link href="/">Return to datasets</Link></Button>
    </div>
  );
}
