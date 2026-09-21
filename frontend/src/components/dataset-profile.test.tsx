import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DatasetProfile } from "./dataset-profile";
import type { DatasetDetail } from "@/lib/api";

const dataset: DatasetDetail = {
  id: "dataset-1",
  name: "Orders",
  description: null,
  original_filename: "orders.csv",
  media_type: "text/csv",
  size_bytes: 128,
  row_count: 2,
  column_count: 2,
  profile_status: "ready",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  columns: [
    { name: "order_id", position: 0, data_type: "VARCHAR", semantic_type: "identifier", nullable: false, null_count: 0, distinct_count: 2, statistics: { null_percentage: 0 }, sample_values: ["A-1", "A-2"] },
    { name: "revenue", position: 1, data_type: "DOUBLE", semantic_type: "measure", nullable: false, null_count: 0, distinct_count: 2, statistics: { min: 10, max: 20 }, sample_values: [10, 20] },
  ],
  preview: [{ order_id: "A-1", revenue: 10 }, { order_id: "A-2", revenue: 20 }],
};

describe("DatasetProfile", () => {
  it("moves from schema details to the data preview", () => {
    render(<DatasetProfile dataset={dataset} />);
    expect(screen.getByText("order_id")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /data preview/i }));
    expect(screen.getByText("A-1")).toBeInTheDocument();
    expect(screen.getByText(/complete dataset/i)).toBeInTheDocument();
  });
});
