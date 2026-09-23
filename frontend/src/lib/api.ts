export type Dataset = {
  id: string;
  name: string;
  description: string | null;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  row_count: number;
  column_count: number;
  profile_status: "processing" | "ready" | "failed";
  created_at: string;
  updated_at: string;
};

export type DatasetColumn = {
  name: string;
  position: number;
  data_type: string;
  semantic_type: "identifier" | "measure" | "category" | "date";
  nullable: boolean;
  null_count: number;
  distinct_count: number;
  statistics: Record<string, string | number | null>;
  sample_values: Array<string | number | boolean | null>;
};

export type DatasetDetail = Dataset & {
  columns: DatasetColumn[];
  preview: Array<Record<string, string | number | boolean | null>>;
};

export type Conversation = {
  id: string;
  dataset_id: string;
  title: string;
  business_context: string | null;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  payload: Record<string, unknown> | null;
  created_at: string;
};

export type AnalysisPlan = {
  restated_question: string;
  intent: string;
  selected_dataset: string;
  metrics: Array<{ column: string | null; aggregation: string; alias: string }>;
  dimensions: string[];
  filters: Array<{ column: string; operator: string; value: unknown }>;
  time_column: string | null;
  time_granularity: string | null;
  required_joins: string[];
  assumptions: string[];
  clarification_needed: boolean;
  clarification_question: string | null;
  suggested_chart: "none" | "kpi" | "line" | "bar" | "donut" | "histogram" | "scatter" | "table";
  approach: string;
};

export type CreatedPlan = {
  query_run_id: string;
  assistant_message: Message;
  plan: AnalysisPlan;
  provider: string;
  model: string;
  prompt_version: string;
  mode: "openai" | "local_fallback";
};

export type AnalysisAnswer = {
  direct_answer: string;
  evidence: string[];
  columns: string[];
  rows: Array<Record<string, string | number | boolean | null>>;
  chart: { type: AnalysisPlan["suggested_chart"]; x_key: string | null; y_keys: string[] };
  assumptions: string[];
  limitations: string[];
  generated_sql: string;
  row_count: number;
  execution_time_ms: number;
  suggested_follow_ups: string[];
};

export type ExecutedRun = {
  query_run_id: string;
  status: string;
  answer: AnalysisAnswer;
  model: string;
  mode: "openai" | "local_fallback";
};

export type QueryRunHistoryItem = {
  id: string;
  dataset_id: string;
  dataset_name: string;
  conversation_id: string | null;
  user_question: string;
  execution_status: string;
  execution_time_ms: number | null;
  row_count: number | null;
  answer_summary: string | null;
  created_at: string;
};

export type SavedInsight = {
  id: string;
  dataset_id: string;
  query_run_id: string;
  title: string;
  note: string | null;
  created_at: string;
  updated_at: string;
};

export type EvaluationSummary = {
  total_cases: number;
  passed_cases: number;
  sql_validity_rate: number;
  execution_success_rate: number;
  result_correctness_rate: number;
  clarification_quality_rate: number;
  unsafe_rejection_rate: number;
  average_latency_ms: number;
  estimated_model_cost_usd: number;
};

export type EvaluationFailure = {
  id: string;
  case_name: string;
  question: string;
  category: string;
  actual_outcome: string;
  expected: Record<string, unknown>;
  failure_reason: string | null;
};

export type EvaluationReport = {
  summary: EvaluationSummary;
  failures: EvaluationFailure[];
};

type DatasetListResponse = { items: Dataset[]; total: number };
type ApiError = { error?: { message?: string } };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function listDatasets(signal?: AbortSignal): Promise<Dataset[]> {
  const response = await fetch(`${API_URL}/datasets`, { signal, cache: "no-store" });
  if (!response.ok) throw new Error(await responseMessage(response));
  const payload = (await response.json()) as DatasetListResponse;
  return payload.items;
}

export async function getDataset(datasetId: string, signal?: AbortSignal): Promise<DatasetDetail> {
  const response = await fetch(`${API_URL}/datasets/${datasetId}`, { signal, cache: "no-store" });
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.json() as Promise<DatasetDetail>;
}

export function uploadDataset(
  file: File,
  onProgress: (phase: "uploading" | "profiling", percent?: number) => void,
): Promise<Dataset> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    const form = new FormData();
    form.append("file", file);
    request.open("POST", `${API_URL}/datasets`);
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress("uploading", Math.round((event.loaded / event.total) * 100));
    };
    request.upload.onload = () => onProgress("profiling");
    request.onerror = () => reject(new Error("The API could not be reached. Check that the backend is running."));
    request.onload = () => {
      let payload: Dataset | ApiError;
      try {
        payload = JSON.parse(request.responseText) as Dataset | ApiError;
      } catch {
        reject(new Error("The server returned an unreadable response."));
        return;
      }
      if (request.status >= 200 && request.status < 300) resolve(payload as Dataset);
      else reject(new Error((payload as ApiError).error?.message ?? "The dataset could not be uploaded."));
    };
    request.send(form);
  });
}

export async function exploreSample(): Promise<Dataset> {
  const response = await fetch(`${API_URL}/datasets/sample`, { method: "POST" });
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.json() as Promise<Dataset>;
}

export async function listConversations(datasetId: string): Promise<Conversation[]> {
  return apiRequest<Conversation[]>(`/conversations?dataset_id=${encodeURIComponent(datasetId)}`);
}

export async function createConversation(datasetId: string): Promise<Conversation> {
  return apiRequest<Conversation>("/conversations", {
    method: "POST",
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}

export async function addQuestion(conversationId: string, content: string): Promise<Message> {
  return apiRequest<Message>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function createAnalysisPlan(conversationId: string, messageId: string): Promise<CreatedPlan> {
  return apiRequest<CreatedPlan>(`/conversations/${conversationId}/plans`, {
    method: "POST",
    body: JSON.stringify({ message_id: messageId }),
  });
}

export async function executeAnalysis(queryRunId: string): Promise<ExecutedRun> {
  return apiRequest<ExecutedRun>(`/query-runs/${queryRunId}/execute`, { method: "POST" });
}

export async function listQueryRuns(): Promise<QueryRunHistoryItem[]> {
  return apiRequest<QueryRunHistoryItem[]>("/query-runs");
}

export async function saveInsight(queryRunId: string, title: string): Promise<SavedInsight> {
  return apiRequest<SavedInsight>("/insights", {
    method: "POST",
    body: JSON.stringify({ query_run_id: queryRunId, title }),
  });
}

export async function deleteDataset(datasetId: string): Promise<void> {
  const response = await fetch(`${API_URL}/datasets/${datasetId}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await responseMessage(response));
}

export async function exportResult(queryRunId: string): Promise<Blob> {
  const response = await fetch(`${API_URL}/query-runs/${queryRunId}/export`);
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.blob();
}

export async function getEvaluationSummary(signal?: AbortSignal): Promise<EvaluationReport> {
  return apiRequest<EvaluationReport>("/evaluations/summary", { signal, cache: "no-store" });
}

export async function runEvaluations(datasetId: string): Promise<EvaluationReport> {
  return apiRequest<EvaluationReport>(`/evaluations/run?dataset_id=${encodeURIComponent(datasetId)}`, {
    method: "POST",
  });
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(await responseMessage(response));
  return response.json() as Promise<T>;
}

async function responseMessage(response: Response) {
  try {
    const payload = (await response.json()) as ApiError;
    return payload.error?.message ?? "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}
