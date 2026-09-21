"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { FileSpreadsheet, Upload, X } from "lucide-react";
import { useId, useState } from "react";
import { Button } from "@/components/ui/button";

export function UploadDialog() {
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);

  return (
    <Dialog.Root onOpenChange={(open) => !open && setFile(null)}>
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
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
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

          <div className="dialog-actions">
            <Dialog.Close asChild><Button variant="ghost">Cancel</Button></Dialog.Close>
            <Button disabled={!file}>Profile dataset</Button>
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
