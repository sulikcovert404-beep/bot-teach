/** Provider-neutral Core API client for Web/Android/Bale clients. */
export class CoreApiClient {
  constructor({ baseUrl = "/api/v1", fetchImpl = window.fetch.bind(window) } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetchImpl = fetchImpl;
    this.session = null;
  }

  setSession(session) { this.session = session; }

  async request(path, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (this.session?.token) headers.Authorization = `Bearer ${this.session.token}`;
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, { ...options, headers });
    let body = null;
    try { body = await response.json(); } catch (_) { body = null; }
    if (!response.ok) {
      const error = new Error(body?.detail || "درخواست ناموفق بود.");
      error.status = response.status;
      error.code = body?.code || "API_ERROR";
      throw error;
    }
    return body;
  }
}

export function renderApiError(element, error) {
  if (!element) return;
  element.textContent = error?.message || "خطای ارتباط با سرویس.";
  element.hidden = false;
}
