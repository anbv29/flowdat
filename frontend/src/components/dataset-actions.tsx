"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { deleteDataset } from "@/lib/api";

export function DatasetActions({ datasetId, datasetName }: { datasetId: string; datasetName: string }) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "deleting" | "error">("idle");

  async function remove() {
    setState("deleting");
    try {
      await deleteDataset(datasetId);
      router.push("/");
      router.refresh();
    } catch {
      setState("error");
    }
  }

  return <Dialog.Root><Dialog.Trigger asChild><Button variant="ghost" className="danger-button"><Trash2 size={14} /> Delete</Button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content delete-dialog"><div className="dialog-heading"><div><Dialog.Title>Delete {datasetName}?</Dialog.Title><Dialog.Description>The source file, profile, conversations, and query history will be removed. This cannot be undone.</Dialog.Description></div><Dialog.Close asChild><Button variant="ghost" size="small" aria-label="Close"><X size={16} /></Button></Dialog.Close></div>{state === "error" && <p className="delete-error">The dataset could not be deleted. Please try again.</p>}<div className="dialog-actions"><Dialog.Close asChild><Button variant="ghost" disabled={state === "deleting"}>Cancel</Button></Dialog.Close><Button className="delete-confirm" onClick={remove} disabled={state === "deleting"}>{state === "deleting" ? "Deleting…" : "Delete dataset"}</Button></div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
