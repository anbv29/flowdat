import path from "node:path";
import { expect, test } from "@playwright/test";

test("uploads ecommerce data and answers a revenue question", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Upload dataset" }).click();
  await page.locator('input[type="file"]').setInputFiles(
    path.resolve(process.cwd(), "../backend/data/ecommerce_orders.csv"),
  );
  await page.getByRole("button", { name: "Profile dataset" }).click();

  await expect(page).toHaveURL(/\/datasets\//);
  await expect(page.getByText("Profile ready")).toBeVisible();
  await page.getByRole("link", { name: "Ask a question" }).click();

  await page.getByPlaceholder(/Ask about revenue/).fill("What is total revenue by region?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Verified answer")).toBeVisible();
  await expect(page.locator(".result-table-wrap tbody tr").first()).toBeVisible();

  await page.getByRole("button", { name: "Context" }).click();
  await expect(page.getByText("Generated SQL")).toBeVisible();
  await expect(page.locator(".context-block pre")).toContainText("SELECT");
});
