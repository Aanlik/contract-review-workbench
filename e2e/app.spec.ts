import { test, expect } from "@playwright/test";

test.describe("Contract Review Workbench", () => {
  test("cases page loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("审核记录");
  });

  test("can create a new case", async ({ page }) => {
    await page.goto("/");
    await page.click('button:has-text("新建审核")');
    await expect(page.locator("h1")).toContainText("新建审核");
    await page.fill('input[placeholder*="合同名称"]', "E2E 测试合同");
    await page.click('button:has-text("创建")');
    // Should navigate to workspace
    await expect(page.locator("h1, .workspace")).toBeVisible({ timeout: 5000 });
  });

  test("settings page loads and has AI config form", async ({ page }) => {
    await page.goto("/");
    await page.click('button:has-text("设置")');
    await expect(page.locator("h1")).toContainText("系统设置");
    await expect(page.locator('input[placeholder*="api"]')).toBeVisible();
  });

  test("audit log page loads", async ({ page }) => {
    await page.goto("/");
    await page.click('button:has-text("审计日志")');
    await expect(page.locator("h1")).toContainText("审计日志");
  });

  test("dark mode toggle works", async ({ page }) => {
    await page.goto("/");
    const themeToggle = page.locator('button:has-text("🌙")');
    await themeToggle.click();
    const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
    expect(theme).toBe("dark");
  });

  test("sidebar collapse works", async ({ page }) => {
    await page.goto("/");
    const toggle = page.locator(".sidebar-toggle");
    await toggle.click();
    await expect(page.locator(".app-shell")).toHaveClass(/sidebar-collapsed/);
  });
});
