import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { UploadDialog } from "./upload-dialog";
import { uploadDataset } from "@/lib/api";

vi.mock("@/lib/api", () => ({ uploadDataset: vi.fn() }));

const uploaded = {
  id: "dataset-1",
  name: "Orders",
  description: null,
  original_filename: "orders.csv",
  media_type: "text/csv",
  size_bytes: 32,
  row_count: 2,
  column_count: 2,
  profile_status: "ready" as const,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("UploadDialog", () => {
  it("uploads the selected file and returns the profiled dataset", async () => {
    const onUploaded = vi.fn();
    vi.mocked(uploadDataset).mockImplementation(async (_file, onProgress) => {
      onProgress("uploading", 60);
      onProgress("profiling");
      return uploaded;
    });

    render(<UploadDialog onUploaded={onUploaded} />);
    fireEvent.click(screen.getByRole("button", { name: /upload dataset/i }));
    const input = document.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).not.toBeNull();
    fireEvent.change(input!, { target: { files: [new File(["a,b\n1,2"], "orders.csv", { type: "text/csv" })] } });
    expect(screen.getByText("orders.csv")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /profile dataset/i }));

    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(uploaded));
    expect(uploadDataset).toHaveBeenCalledOnce();
  });

  it("shows a useful upload error", async () => {
    vi.mocked(uploadDataset).mockRejectedValueOnce(new Error("Only CSV and Parquet files are supported."));
    render(<UploadDialog onUploaded={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /upload dataset/i }));
    const input = document.querySelector<HTMLInputElement>('input[type="file"]');
    fireEvent.change(input!, { target: { files: [new File(["bad"], "notes.txt")] } });
    fireEvent.click(screen.getByRole("button", { name: /profile dataset/i }));
    expect(await screen.findByRole("status")).toHaveTextContent("Only CSV and Parquet files are supported.");
  });
});
