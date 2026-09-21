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

type DatasetListResponse = { items: Dataset[]; total: number };
type ApiError = { error?: { message?: string } };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export async function listDatasets(signal?: AbortSignal): Promise<Dataset[]> {
  const response = await fetch(`${API_URL}/datasets`, { signal, cache: "no-store" });
  if (!response.ok) throw new Error(await responseMessage(response));
  const payload = (await response.json()) as DatasetListResponse;
  return payload.items;
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

async function responseMessage(response: Response) {
  try {
    const payload = (await response.json()) as ApiError;
    return payload.error?.message ?? "The request could not be completed.";
  } catch {
    return "The request could not be completed.";
  }
}
