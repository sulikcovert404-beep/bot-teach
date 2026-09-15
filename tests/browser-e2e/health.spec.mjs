import { test, expect } from '@playwright/test';

test('disposable application exposes health and dashboard routes', async ({ page, baseURL }) => {
  const health = await page.request.get(`${baseURL}/health`);
  expect(health.status()).toBe(200);
  const ready = await page.request.get(`${baseURL}/health/ready`);
  expect(ready.status()).toBe(200);
  for (const route of ['/mini-app/', '/student-dashboard/', '/teacher-dashboard/', '/admin-dashboard/', '/platform/']) {
    const response = await page.request.get(`${baseURL}${route}`);
    expect(response.status(), route).toBe(200);
  }
});
