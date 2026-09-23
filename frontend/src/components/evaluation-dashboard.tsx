"use client";

import { AlertCircle, Check, FlaskConical, Gauge, Play, ShieldCheck, Timer } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  getEvaluationSummary,
  listDatasets,
  runEvaluations,
  type Dataset,
  type EvaluationReport,
} from "@/lib/api";

const EMPTY_REPORT: EvaluationReport = {
  summary: {
    total_cases: 0,
    passed_cases: 0,
    sql_validity_rate: 0,
    execution_success_rate: 0,
    result_correctness_rate: 0,
    clarification_quality_rate: 0,
    unsafe_rejection_rate: 0,
    average_latency_ms: 0,
    estimated_model_cost_usd: 0,
  },
  failures: [],
};

export function EvaluationDashboard() {
  const [report, setReport] = useState<EvaluationReport>(EMPTY_REPORT);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([getEvaluationSummary(controller.signal), listDatasets(controller.signal)])
      .then(([summary, availableDatasets]) => {
        const readyDatasets = availableDatasets.filter((dataset) => dataset.profile_status === "ready");
        setReport(summary);
        setDatasets(readyDatasets);
        setDatasetId(readyDatasets[0]?.id || "");
        setLoading(false);
      })
      .catch((caught: Error) => {
        if (caught.name !== "AbortError") {
          setError(caught.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  async function runBenchmark() {
    if (!datasetId) return;
    setRunning(true);
    setError(null);
    try {
      setReport(await runEvaluations(datasetId));
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setRunning(false);
    }
  }

  const passRate = useMemo(() => {
    if (!report.summary.total_cases) return 0;
    return Math.round((report.summary.passed_cases / report.summary.total_cases) * 100);
  }, [report.summary]);

  if (loading) {
    return <div className="evaluation-loading"><span className="spinner" /> Loading benchmark results…</div>;
  }

  const summary = report.summary;
  const metrics = [
    { label: "Overall pass rate", value: `${passRate}%`, detail: `${summary.passed_cases} of ${summary.total_cases} cases`, icon: Check },
    { label: "Result correctness", value: `${summary.result_correctness_rate}%`, detail: "Expected shape and fields", icon: Gauge },
    { label: "Safe rejection", value: `${summary.unsafe_rejection_rate}%`, detail: "Unsafe requests stopped", icon: ShieldCheck },
    { label: "Average latency", value: `${Math.round(summary.average_latency_ms)} ms`, detail: "Across the latest run", icon: Timer },
  ];

  return (
    <>
      <section className="page-heading evaluation-heading">
        <div>
          <p className="eyebrow">Quality checks</p>
          <h1>Evaluation suite</h1>
          <p className="lede">Run the standard question set against a profiled dataset and inspect the cases that need work.</p>
        </div>
        <div className="evaluation-runner">
          <label>
            <span>Evaluation dataset</span>
            <select value={datasetId} onChange={(event) => setDatasetId(event.target.value)} disabled={running}>
              {datasets.map((dataset) => <option value={dataset.id} key={dataset.id}>{dataset.name}</option>)}
            </select>
          </label>
          <Button onClick={runBenchmark} disabled={!datasetId || running}>
            {running ? <span className="spinner evaluation-spinner" /> : <Play size={14} />}
            {running ? "Running cases" : "Run evaluation"}
          </Button>
        </div>
      </section>

      {error && <div className="evaluation-error"><AlertCircle size={15} /> {error}</div>}
      {!datasets.length && <div className="evaluation-note">Profile a dataset before running the benchmark.</div>}

      <section className="evaluation-metrics" aria-label="Evaluation summary">
        {metrics.map(({ label, value, detail, icon: Icon }) => (
          <article className="evaluation-metric" key={label}>
            <span><Icon size={15} /></span>
            <p>{label}</p>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </section>

      <section className="evaluation-detail-grid">
        <article className="evaluation-panel">
          <div className="evaluation-panel-heading">
            <div><p className="eyebrow">Latest run</p><h2>Capability breakdown</h2></div>
            <FlaskConical size={17} />
          </div>
          <div className="score-list">
            <Score label="SQL validity" value={summary.sql_validity_rate} />
            <Score label="Execution success" value={summary.execution_success_rate} />
            <Score label="Clarification quality" value={summary.clarification_quality_rate} />
            <Score label="Unsafe query rejection" value={summary.unsafe_rejection_rate} />
          </div>
          <div className="cost-note">
            <span>Estimated model cost</span>
            <strong>${summary.estimated_model_cost_usd.toFixed(4)}</strong>
          </div>
        </article>

        <article className="evaluation-panel failure-panel">
          <div className="evaluation-panel-heading">
            <div><p className="eyebrow">Review queue</p><h2>Failed cases</h2></div>
            <span className="failure-count">{report.failures.length}</span>
          </div>
          {!summary.total_cases ? (
            <div className="evaluation-empty">Run the suite to establish a baseline.</div>
          ) : !report.failures.length ? (
            <div className="evaluation-empty is-success"><Check size={17} /> All cases passed in the latest run.</div>
          ) : (
            <div className="failure-list">
              {report.failures.map((failure) => (
                <div className="failure-row" key={failure.id}>
                  <span>{failure.category.replaceAll("_", " ")}</span>
                  <strong>{failure.case_name}</strong>
                  <p>{failure.failure_reason || `Returned ${failure.actual_outcome}.`}</p>
                  <small>{failure.question}</small>
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </>
  );
}

function Score({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-row">
      <div><span>{label}</span><strong>{value}%</strong></div>
      <i><b style={{ width: `${Math.min(100, Math.max(0, value))}%` }} /></i>
    </div>
  );
}
