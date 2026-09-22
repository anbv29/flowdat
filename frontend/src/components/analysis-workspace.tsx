"use client";

import {
  BarChart3,
  Check,
  ChevronRight,
  Code2,
  Database,
  Filter,
  History,
  Lightbulb,
  LoaderCircle,
  MessageSquareText,
  PanelRight,
  Send,
  Bookmark,
  Download,
  Sparkles,
  Table2,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Button } from "@/components/ui/button";
import {
  type AnalysisAnswer,
  type AnalysisPlan,
  type Conversation,
  type DatasetDetail,
  type Message,
  addQuestion,
  createAnalysisPlan,
  createConversation,
  executeAnalysis,
  getDataset,
  listConversations,
  saveInsight,
  exportResult,
} from "@/lib/api";

type WorkspaceMessage = Message | { id: string; role: "assistant"; content: string; created_at: string };
type WorkState = "idle" | "saving" | "planning" | "executing" | "error";
type MobilePanel = "sources" | "conversation" | "context";

const suggestions = [
  "What is total revenue by region?",
  "Show the monthly revenue trend",
  "Which category has the highest revenue?",
];

export function AnalysisWorkspace() {
  const datasetId = useSearchParams().get("dataset");
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<WorkspaceMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [plan, setPlan] = useState<AnalysisPlan | null>(null);
  const [answer, setAnswer] = useState<AnalysisAnswer | null>(null);
  const [mode, setMode] = useState<"openai" | "local_fallback" | null>(null);
  const [queryRunId, setQueryRunId] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">("idle");
  const [state, setState] = useState<WorkState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("conversation");

  useEffect(() => {
    if (!datasetId) return;
    const controller = new AbortController();
    Promise.all([getDataset(datasetId, controller.signal), listConversations(datasetId)])
      .then(([selected, threads]) => {
        setDataset(selected);
        setConversations(threads);
      })
      .catch((reason: Error) => {
        if (reason.name !== "AbortError") setError(reason.message);
      });
    return () => controller.abort();
  }, [datasetId]);

  async function ask(content: string) {
    const trimmed = content.trim();
    if (!dataset || !trimmed || state !== "idle") return;
    setQuestion("");
    setError(null);
    setAnswer(null);
    setPlan(null);
    try {
      setState("saving");
      let activeConversationId = conversationId;
      if (!activeConversationId) {
        const created = await createConversation(dataset.id);
        activeConversationId = created.id;
        setConversationId(created.id);
        setConversations((current) => [created, ...current]);
      }
      const userMessage = await addQuestion(activeConversationId, trimmed);
      setMessages((current) => [...current, userMessage]);
      setState("planning");
      const createdPlan = await createAnalysisPlan(activeConversationId, userMessage.id);
      setQueryRunId(createdPlan.query_run_id);
      setPlan(createdPlan.plan);
      setMode(createdPlan.mode);
      setMessages((current) => [...current, createdPlan.assistant_message]);
      if (!createdPlan.plan.clarification_needed) {
        setState("executing");
        const executed = await executeAnalysis(createdPlan.query_run_id);
        setAnswer(executed.answer);
        setMode(executed.mode);
        setMessages((current) => [
          ...current,
          {
            id: `${createdPlan.query_run_id}-answer`,
            role: "assistant",
            content: executed.answer.direct_answer,
            created_at: new Date().toISOString(),
          },
        ]);
      }
      setState("idle");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The analysis could not be completed.");
      setState("error");
      window.setTimeout(() => setState("idle"), 300);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(question);
  }

  async function bookmarkAnswer() {
    if (!queryRunId || !answer) return;
    setSaveState("saving");
    try {
      await saveInsight(queryRunId, plan?.restated_question ?? answer.direct_answer);
      setSaveState("saved");
    } catch (reason) {
      setSaveState("idle");
      setError(reason instanceof Error ? reason.message : "The insight could not be saved.");
    }
  }

  async function downloadResult() {
    if (!queryRunId) return;
    try {
      const blob = await exportResult(queryRunId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `signaldesk-${queryRunId.slice(0, 8)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The result could not be exported.");
    }
  }

  if (!datasetId) return <WorkspaceNotice text="Choose a dataset before starting an analysis." />;
  if (!dataset && !error) return <div className="analysis-loading"><LoaderCircle className="spinner-icon" /> Preparing workspace…</div>;
  if (!dataset) return <WorkspaceNotice text={error ?? "This dataset is unavailable."} />;

  return (
    <main className="analysis-page">
      <div className="mobile-workspace-tabs" role="tablist" aria-label="Workspace panels">
        <button className={mobilePanel === "sources" ? "is-active" : ""} onClick={() => setMobilePanel("sources")}><Database size={14} /> Data</button>
        <button className={mobilePanel === "conversation" ? "is-active" : ""} onClick={() => setMobilePanel("conversation")}><MessageSquareText size={14} /> Answer</button>
        <button className={mobilePanel === "context" ? "is-active" : ""} onClick={() => setMobilePanel("context")}><PanelRight size={14} /> Context</button>
      </div>

      <aside className={`analysis-panel source-rail ${mobilePanel === "sources" ? "is-mobile-active" : ""}`}>
        <PanelTitle icon={Database} label="Dataset" />
        <div className="active-dataset">
          <span><Table2 size={16} /></span>
          <div><strong>{dataset.name}</strong><p>{dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns</p></div>
          <Check size={14} />
        </div>
        <PanelTitle icon={History} label="Conversations" />
        <div className="thread-list">
          {conversations.length === 0 && <p className="rail-empty">Your analysis history will appear here.</p>}
          {conversations.map((conversation) => (
            <button key={conversation.id} className={conversation.id === conversationId ? "is-active" : ""} type="button">
              <MessageSquareText size={13} /><span>{conversation.title}</span><ChevronRight size={12} />
            </button>
          ))}
        </div>
      </aside>

      <section className={`analysis-panel conversation-panel ${mobilePanel === "conversation" ? "is-mobile-active" : ""}`}>
        <header className="conversation-header">
          <div><p className="eyebrow">Analysis</p><h1>{dataset.name}</h1></div>
          {mode && <span className="mode-label">{mode === "local_fallback" ? "Local fallback" : "OpenAI"}</span>}
        </header>

        <div className="conversation-scroll">
          {messages.length === 0 && !answer ? (
            <div className="analysis-empty">
              <span><Sparkles size={21} /></span>
              <h2>What would you like to understand?</h2>
              <p>Ask a concrete question about this dataset. SignalDesk will show its assumptions and SQL.</p>
              <div className="suggestion-list">
                {suggestions.map((item) => <button type="button" key={item} onClick={() => void ask(item)}>{item}<ChevronRight size={13} /></button>)}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message) => message.role === "user" ? (
                <div className="user-message" key={message.id}>{message.content}</div>
              ) : (
                <div className="assistant-message" key={message.id}><Sparkles size={13} /><p>{message.content}</p></div>
              ))}
              {state !== "idle" && <AnalysisProgress state={state} />}
              {plan?.clarification_needed && <div className="assistant-note"><Sparkles size={15} /><p>{plan.clarification_question}</p></div>}
              {answer && <AnswerView answer={answer} onSave={bookmarkAnswer} onExport={downloadResult} onFollowUp={(prompt) => void ask(prompt)} saveState={saveState} />}
              {error && <div className="analysis-error">{error}</div>}
            </div>
          )}
        </div>

        <form className="question-composer" onSubmit={submit}>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about revenue, customers, products…" rows={2} />
          <Button disabled={!question.trim() || state !== "idle"} aria-label="Send question"><Send size={15} /></Button>
        </form>
      </section>

      <aside className={`analysis-panel context-rail ${mobilePanel === "context" ? "is-mobile-active" : ""}`}>
        <PanelTitle icon={Lightbulb} label="Analysis context" />
        {!plan ? <p className="rail-empty">Metrics, filters, assumptions, and generated SQL will appear after you ask a question.</p> : (
          <div className="context-stack">
            <ContextBlock icon={BarChart3} title="Plan">
              <p>{plan.approach}</p>
            </ContextBlock>
            <ContextBlock icon={Filter} title="Filters">
              <p>{plan.filters.length ? plan.filters.map((item) => `${item.column} ${item.operator} ${String(item.value)}`).join(", ") : "No filters applied"}</p>
            </ContextBlock>
            <ContextBlock icon={Lightbulb} title="Assumptions">
              {plan.assumptions.length ? <ul>{plan.assumptions.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No additional assumptions.</p>}
            </ContextBlock>
            {answer && <ContextBlock icon={Code2} title="Generated SQL"><pre>{answer.generated_sql}</pre></ContextBlock>}
          </div>
        )}
      </aside>
    </main>
  );
}

function PanelTitle({ icon: Icon, label }: { icon: typeof Database; label: string }) {
  return <div className="rail-title"><Icon size={14} /><span>{label}</span></div>;
}

function ContextBlock({ icon: Icon, title, children }: { icon: typeof Database; title: string; children: React.ReactNode }) {
  return <section className="context-block"><h3><Icon size={13} />{title}</h3>{children}</section>;
}

function AnalysisProgress({ state }: { state: WorkState }) {
  const copy = state === "saving" ? "Saving your question" : state === "planning" ? "Preparing a grounded plan" : "Validating and running SQL";
  return <div className="analysis-progress"><LoaderCircle className="spinner-icon" size={15} /><span>{copy}</span></div>;
}

function AnswerView({ answer, onSave, onExport, onFollowUp, saveState }: { answer: AnalysisAnswer; onSave: () => void; onExport: () => void; onFollowUp: (prompt: string) => void; saveState: "idle" | "saving" | "saved" }) {
  return (
    <article className="answer-view">
      <div className="answer-heading"><span><Sparkles size={16} /></span><div><p className="eyebrow">Verified answer</p><h2>{answer.direct_answer}</h2></div><div className="answer-actions"><Button variant="ghost" size="small" onClick={onExport}><Download size={13} /> CSV</Button><Button variant="secondary" size="small" onClick={onSave} disabled={saveState !== "idle"}><Bookmark size={13} />{saveState === "saved" ? "Saved" : saveState === "saving" ? "Saving…" : "Save"}</Button></div></div>
      <ResultChart answer={answer} />
      <div className="result-table-wrap"><table><thead><tr>{answer.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{answer.rows.slice(0, 20).map((row, index) => <tr key={index}>{answer.columns.map((column) => <td key={column}>{formatValue(row[column])}</td>)}</tr>)}</tbody></table></div>
      <ul className="evidence-list">{answer.evidence.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="execution-note">{answer.row_count} result rows · {answer.execution_time_ms.toFixed(1)} ms</p>
      <div className="follow-up-list"><span>Continue exploring</span>{answer.suggested_follow_ups.map((item) => <button type="button" onClick={() => onFollowUp(item)} key={item}>{item}<ChevronRight size={12} /></button>)}</div>
    </article>
  );
}

function ResultChart({ answer }: { answer: AnalysisAnswer }) {
  const { chart, rows } = answer;
  if (!chart.x_key || !chart.y_keys.length || !["bar", "line"].includes(chart.type)) return null;
  const common = <><CartesianGrid stroke="rgba(42,51,72,.08)" vertical={false} /><XAxis dataKey={chart.x_key} tick={{ fontSize: 9, fill: "#777e8d" }} /><YAxis tick={{ fontSize: 9, fill: "#777e8d" }} /><Tooltip /></>;
  return <div className="answer-chart"><ResponsiveContainer width="100%" height="100%">{chart.type === "line" ? <LineChart data={rows}>{common}{chart.y_keys.map((key) => <Line key={key} dataKey={key} stroke="#5a5f9f" strokeWidth={2} dot={false} />)}</LineChart> : <BarChart data={rows}>{common}{chart.y_keys.map((key) => <Bar key={key} dataKey={key} fill="#666ba6" radius={[4, 4, 0, 0]} />)}</BarChart>}</ResponsiveContainer></div>;
}

function WorkspaceNotice({ text }: { text: string }) {
  return <div className="workspace-notice"><Database size={22} /><p>{text}</p><Button variant="secondary" asChild><Link href="/">Choose dataset</Link></Button></div>;
}

function formatValue(value: unknown) {
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (value === null || value === undefined) return "—";
  return String(value);
}
