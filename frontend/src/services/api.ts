/* API Service — All backend communication */

const API_BASE = 'http://localhost:8000/api/v1';

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

class ApiService {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('nighthawk_token', token);
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('nighthawk_token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('nighthawk_token');
  }

  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async register(username: string, email: string, password: string) {
    const data = await this.request<{ access_token: string; user: any }>('/auth/register', {
      method: 'POST',
      body: { username, email, password },
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(username: string, password: string) {
    const data = await this.request<{ access_token: string; user: any }>('/auth/login', {
      method: 'POST',
      body: { username, password },
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.request<any>('/auth/me');
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
    const token = this.getToken();
    const res = await fetch(`${API_BASE}/engagements/${engagementId}/reports/markdown`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.text();
  }

  async getHtmlReport(engagementId: string) {
    const token = this.getToken();
    const res = await fetch(`${API_BASE}/engagements/${engagementId}/reports/html`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.text();
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
    const token = this.getToken();
    const res = await fetch(`${API_BASE}/engagements/${engagementId}/blueteam/nginx-config`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    return res.text();
  }

  // HAR Analysis
  async uploadHar(engagementId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const token = this.getToken();
    const res = await fetch(`${API_BASE}/engagements/${engagementId}/har/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'HAR analysis failed');
    }
    return res.json();
  }
}

export const api = new ApiService();
export default api;
