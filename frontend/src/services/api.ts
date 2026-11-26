/* API Service — cookie-based authentication and typed API access */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

interface AuthResponse {
  user: any;
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const entry = document.cookie.split('; ').find(part => part.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

class ApiService {
  private async refreshSession(): Promise<boolean> {
    const csrf = readCookie('nighthawk_csrf');
    if (!csrf) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': csrf },
      });
      if (response.ok) return true;

      // Expired or revoked sessions should not leave stale HttpOnly cookies behind.
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRF-Token': csrf },
      }).catch(() => undefined);
      return false;
    } catch {
      return false;
    }
  }

  private async fetchAuthenticated(
    endpoint: string,
    options: RequestOptions = {},
    retryAfterRefresh = true,
  ): Promise<Response> {
    const method = (options.method || 'GET').toUpperCase();
    const headers: Record<string, string> = { ...options.headers };
    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    if (options.body !== undefined && !isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const csrf = readCookie('nighthawk_csrf');
      if (csrf) headers['X-CSRF-Token'] = csrf;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      credentials: 'include',
      headers,
      body: options.body === undefined
        ? undefined
        : isFormData ? options.body as FormData : JSON.stringify(options.body),
    });

    const isAuthEndpoint = endpoint.startsWith('/auth/');
    if (response.status === 401 && retryAfterRefresh && !isAuthEndpoint) {
      if (await this.refreshSession()) {
        return this.fetchAuthenticated(endpoint, options, false);
      }
    }
    return response;
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const response = await this.fetchAuthenticated(endpoint, options);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    if (response.status === 204) return undefined as T;
    return response.json();
  }

  private async requestText(endpoint: string): Promise<string> {
    const response = await this.fetchAuthenticated(endpoint);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    return response.text();
  }

  // Authentication — credentials are sent once; the server sets HttpOnly cookies.
  async register(username: string, email: string, password: string, bootstrapToken?: string) {
    return this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: { username, email, password, ...(bootstrapToken ? { bootstrap_token: bootstrapToken } : {}) },
    });
  }

  async login(username: string, password: string) {
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
    });
  }

  async getMe() {
    return this.request<any>('/auth/me');
  }

  async logout() {
    try {
      await this.fetchAuthenticated('/auth/logout', { method: 'POST' }, false);
    } finally {
      // No authentication token is exposed to or retained by JavaScript.
    }
  }

  // System
  async getHealth() {
    return this.request<any>('/health');
  }

  async getTools() {
    return this.request<any>('/tools');
  }

  async getDashboard() {
    return this.request<any>('/dashboard');
  }

  // Engagements
  async getEngagements() {
    return this.request<any[]>('/engagements/');
  }

  async createEngagement(data: any) {
    return this.request<any>('/engagements/', { method: 'POST', body: data });
  }

  async getEngagement(id: string) {
    return this.request<any>(`/engagements/${id}`);
  }

  async updateEngagement(id: string, data: any) {
    return this.request<any>(`/engagements/${id}`, { method: 'PATCH', body: data });
  }

  async getEngagementStats(id: string) {
    return this.request<any>(`/engagements/${id}/stats`);
  }

  // Scans
  async createScan(engagementId: string, data: any) {
    return this.request<any>(`/engagements/${engagementId}/scans`, { method: 'POST', body: data });
  }

  async getScans(engagementId: string) {
    return this.request<any[]>(`/engagements/${engagementId}/scans`);
  }

  // Findings
  async getFindings(engagementId: string, filters?: Record<string, string>) {
    const params = new URLSearchParams(filters || {}).toString();
    const qs = params ? `?${params}` : '';
    return this.request<any[]>(`/engagements/${engagementId}/findings/${qs}`);
  }

  async updateFinding(engagementId: string, findingId: string, data: any) {
    return this.request<any>(`/engagements/${engagementId}/findings/${findingId}`, {
      method: 'PATCH',
      body: data,
    });
  }

  async remediateFinding(engagementId: string, findingId: string) {
    return this.request<any>(`/engagements/${engagementId}/findings/${findingId}/remediate`, {
      method: 'POST',
    });
  }

  // Reports
  async getMarkdownReport(engagementId: string) {
    return this.requestText(`/engagements/${engagementId}/reports/markdown`);
  }

  async getHtmlReport(engagementId: string) {
    return this.requestText(`/engagements/${engagementId}/reports/html`);
  }

  // Blue Team
  async getDefensivePosture(engagementId: string) {
    return this.request<any>(`/engagements/${engagementId}/blueteam/posture`);
  }

  async getWafRules(engagementId: string) {
    return this.request<{ rules: any[]; count: number }>(`/engagements/${engagementId}/blueteam/waf-rules`);
  }

  async getSigmaRules(engagementId: string) {
    return this.request<{ rules: any[]; count: number }>(`/engagements/${engagementId}/blueteam/sigma-rules`);
  }

  async getNginxConfig(engagementId: string) {
    return this.requestText(`/engagements/${engagementId}/blueteam/nginx-config`);
  }

  // HAR Analysis
  async uploadHar(engagementId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request<any>(`/engagements/${engagementId}/har/upload`, {
      method: 'POST',
      body: formData,
    });
  }
}

export const api = new ApiService();
export default api;
