import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AnalysisWorkspace } from "./analysis-workspace";
import * as api from "@/lib/api";

vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams("dataset=dataset-1") }));
vi.mock("@/lib/api", () => ({
  getDataset: vi.fn(),
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  addQuestion: vi.fn(),
  createAnalysisPlan: vi.fn(),
  executeAnalysis: vi.fn(),
  saveInsight: vi.fn(),
  exportResult: vi.fn(),
}));
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="chart">{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-kind="line">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-kind="bar">{children}</div>,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-kind="donut">{children}</div>,
  ScatterChart: ({ children }: { children: React.ReactNode }) => <div data-kind="scatter">{children}</div>,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Line: () => null,
  Bar: () => null,
  Pie: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Cell: () => null,
  Scatter: () => null,
}));

const dataset: api.DatasetDetail = {
  id: "dataset-1",
  name: "Ecommerce orders",
  description: null,
  original_filename: "orders.csv",
  media_type: "text/csv",
  size_bytes: 100,
  row_count: 20,
  column_count: 2,
  profile_status: "ready",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  columns: [],
  preview: [],
};

const plan: api.AnalysisPlan = {
  restated_question: "Monthly revenue",
  intent: "trend",
  selected_dataset: "dataset-1",
  metrics: [{ column: "revenue", aggregation: "sum", alias: "total_revenue" }],
  dimensions: ["period"],
  filters: [],
  time_column: "order_date",
  time_granularity: "month",
  required_joins: [],
  assumptions: ["Revenue uses the recorded order total."],
  clarification_needed: false,
  clarification_question: null,
  suggested_chart: "line",
  approach: "Group revenue by month.",
};

const answer: api.AnalysisAnswer = {
  direct_answer: "Revenue reached $42,000 in February.",
  evidence: ["February revenue was $42,000."],
  columns: ["period", "total_revenue"],
  rows: [{ period: "2026-02", total_revenue: 42000 }],
  chart: { type: "line", x_key: "period", y_keys: ["total_revenue"] },
  assumptions: plan.assumptions,
  limitations: [],
  generated_sql: 'SELECT DATE_TRUNC(\'month\', "order_date") AS period, SUM("revenue") AS total_revenue FROM dataset GROUP BY 1',
  row_count: 1,
  execution_time_ms: 12,
  suggested_follow_ups: ["Compare this with January"],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getDataset).mockResolvedValue(dataset);
  vi.mocked(api.listConversations).mockResolvedValue([]);
  vi.mocked(api.createConversation).mockResolvedValue({ id: "conversation-1", dataset_id: dataset.id, title: "Monthly revenue", business_context: null, created_at: "", updated_at: "" });
  vi.mocked(api.addQuestion).mockResolvedValue({ id: "message-1", conversation_id: "conversation-1", role: "user", content: "Show monthly revenue", payload: null, created_at: "" });
  vi.mocked(api.createAnalysisPlan).mockResolvedValue({ query_run_id: "run-1", assistant_message: { id: "message-2", conversation_id: "conversation-1", role: "assistant", content: "I will group revenue by month.", payload: null, created_at: "" }, plan, provider: "local", model: "deterministic", prompt_version: "v1", mode: "local_fallback" });
  vi.mocked(api.executeAnalysis).mockResolvedValue({ query_run_id: "run-1", status: "completed", answer, model: "deterministic", mode: "local_fallback" });
});

describe("AnalysisWorkspace", () => {
  it("shows a loading state while the dataset is being prepared", () => {
    vi.mocked(api.getDataset).mockReturnValue(new Promise(() => {}));
    render(<AnalysisWorkspace />);
    expect(screen.getByText(/preparing workspace/i)).toBeInTheDocument();
  });

  it("asks a question and presents the answer, assumptions, SQL, and chart", async () => {
    render(<AnalysisWorkspace />);
    const prompt = await screen.findByPlaceholderText(/ask about revenue/i);
    fireEvent.change(prompt, { target: { value: "Show monthly revenue" } });
    fireEvent.click(screen.getByRole("button", { name: /send question/i }));

    expect((await screen.findAllByText("Revenue reached $42,000 in February.")).length).toBe(2);
    expect(screen.getByText("Revenue uses the recorded order total.")).toBeInTheDocument();
    expect(screen.getByText(/SELECT DATE_TRUNC/)).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toBeInTheDocument();
    expect(api.executeAnalysis).toHaveBeenCalledWith("run-1");
  });

  it("turns API failures into a stable error state", async () => {
    vi.mocked(api.getDataset).mockRejectedValueOnce(new Error("Dataset could not be loaded."));
    render(<AnalysisWorkspace />);
    await waitFor(() => expect(screen.getByText("Dataset could not be loaded.")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: /choose dataset/i })).toBeInTheDocument();
  });
});
