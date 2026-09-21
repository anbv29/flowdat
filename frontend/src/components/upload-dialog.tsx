"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { FileSpreadsheet, Upload, X } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { type Dataset, uploadDataset } from "@/lib/api";

type UploadState =
  | { phase: "idle" }
  | { phase: "uploading"; percent: number }
  | { phase: "profiling" }
  | { phase: "error"; message: string };

export function UploadDialog({ onUploaded }: { onUploaded: (dataset: Dataset) => void }) {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<UploadState>({ phase: "idle" });

  async function submit() {
    if (!file) return;
    setState({ phase: "uploading", percent: 0 });
    try {
      const dataset = await uploadDataset(file, (phase, percent) => {
        setState(phase === "uploading" ? { phase, percent: percent ?? 0 } : { phase });
      });
      onUploaded(dataset);
      setOpen(false);
      setFile(null);
      setState({ phase: "idle" });
    } catch (error) {
      setState({ phase: "error", message: error instanceof Error ? error.message : "Upload failed." });
    }
  }

  const busy = state.phase === "uploading" || state.phase === "profiling";

  return (
    <Dialog.Root open={open} onOpenChange={(nextOpen) => {
      if (busy) return;
      setOpen(nextOpen);
      if (!nextOpen) { setFile(null); setState({ phase: "idle" }); }
    }}>
      <Dialog.Trigger asChild>
        <Button><Upload size={15} /> Upload dataset</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-heading">
            <div>
              <Dialog.Title>Add a dataset</Dialog.Title>
              <Dialog.Description>Choose a CSV or Parquet file to profile in this workspace.</Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="small" aria-label="Close"><X size={16} /></Button>
            </Dialog.Close>
          </div>

          <label className="drop-zone" htmlFor={inputId}>
            <input
              id={inputId}
              type="file"
              accept=".csv,.parquet,text/csv,application/vnd.apache.parquet"
              disabled={busy}
              onChange={(event) => { setFile(event.target.files?.[0] ?? null); setState({ phase: "idle" }); }}
            />
            <span className="file-icon"><FileSpreadsheet size={21} /></span>
            {file ? (
              <>
                <strong>{file.name}</strong>
                <span>{formatBytes(file.size)} · ready to upload</span>
              </>
            ) : (
              <>
                <strong>Drop a file here, or browse</strong>
                <span>CSV or Parquet, up to 100 MB</span>
              </>
            )}
          </label>

          {state.phase !== "idle" && (
            <div className={state.phase === "error" ? "upload-status is-error" : "upload-status"} role="status">
              {state.phase === "uploading" && <><span>Uploading securely</span><strong>{state.percent}%</strong></>}
              {state.phase === "profiling" && <><span>Reading columns and statistics</span><span className="spinner" /></>}
              {state.phase === "error" && <span>{state.message}</span>}
            </div>
          )}

          <div className="dialog-actions">
            <Dialog.Close asChild><Button variant="ghost" disabled={busy}>Cancel</Button></Dialog.Close>
            <Button disabled={!file || busy} onClick={submit}>{busy ? "Working…" : "Profile dataset"}</Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
