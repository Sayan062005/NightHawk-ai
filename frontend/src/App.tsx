import { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import api from './services/api';
import FindingsPage from './pages/FindingsPage';
import ScansPage from './pages/ScansPage';
import BlueTeamPage from './pages/BlueTeamPage';
import SettingsPage from './pages/SettingsPage';

/* ═══════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════ */

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

interface DashboardStats {
  total_engagements: number;
  active_engagements: number;
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  medium_findings: number;
  low_findings: number;
  info_findings: number;
  confirmed_findings: number;
  candidate_findings: number;
  false_positives: number;
  active_scans: number;
  completed_scans: number;
  tools_available: number;
  tools_total: number;
  ai_available: boolean;
}

interface HealthData {
  status: string;
  version: string;
  ai_provider: string;
  ai_available: boolean;
  tools_available: number;
  tools_total: number;
  uptime_seconds: number;
}

interface Tool {
  name: string;
  binary: string;
  available: boolean;
  path: string;
  version: string;
  install_instructions: string;
  description: string;
}

type Page = 'dashboard' | 'engagements' | 'findings' | 'scans' | 'tools' | 'blueteam' | 'settings';

/* ═══════════════════════════════════════════════════════════════
   Icon Components (inline SVG for zero deps)
   ═══════════════════════════════════════════════════════════════ */

const icons = {
  dashboard: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
  target: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>,
  bug: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 2l1.88 1.88"/><path d="M14.12 3.88L16 2"/><path d="M9 7.13v-1a3.003 3.003 0 116 0v1"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 014-4h4a4 4 0 014 4v3c0 3.3-2.7 6-6 6"/><path d="M12 20v-9"/><path d="M6.53 9C4.6 8.8 3 7.1 3 5"/><path d="M6 13H2"/><path d="M3 21c0-2.1 1.7-3.9 3.8-4"/><path d="M20.97 5c0 2.1-1.6 3.8-3.5 4"/><path d="M22 13h-4"/><path d="M17.2 17c2.1.1 3.8 1.9 3.8 4"/></svg>,
  scan: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 7V5a2 2 0 012-2h2"/><path d="M17 3h2a2 2 0 012 2v2"/><path d="M21 17v2a2 2 0 01-2 2h-2"/><path d="M7 21H5a2 2 0 01-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/></svg>,
  tools: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
  shield: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  settings: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>,
  check: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>,
  x: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>,
  plus: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  ai: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2a4 4 0 014 4v1a2 2 0 012 2v3a8 8 0 01-16 0V9a2 2 0 012-2V6a4 4 0 014-4z"/><path d="M9 14l2 2 4-4"/></svg>,
  sun: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
  moon: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>,
  logout: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
};

/* ═══════════════════════════════════════════════════════════════
   Login Page
   ═══════════════════════════════════════════════════════════════ */

function LoginPage({ onLogin }: { onLogin: (user: User) => void }) {
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      let data;
      if (isRegister) {
        data = await api.register(username, email, password);
      } else {
        data = await api.login(username, password);
      }
      onLogin(data.user);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0a0e1a 0%, #1a1a3e 50%, #0a0e1a 100%)',
      padding: 20,
    }}>
      <div style={{
        width: '100%',
        maxWidth: 420,
        animation: 'fadeIn 0.4s ease-out',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 0 30px rgba(99, 102, 241, 0.4)',
          }}>
            <span style={{ width: 32, height: 32, color: 'white' }}>{icons.shield}</span>
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
            SentinelWeb AI
          </h1>
          <p style={{ color: '#94a3b8', marginTop: 4, fontSize: '0.875rem' }}>
            Security Assessment Platform
          </p>
        </div>

        <div className="card card-glass" style={{ padding: 28 }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 20, textAlign: 'center' }}>
            {isRegister ? 'Create Account' : 'Sign In'}
          </h2>

          {error && (
            <div style={{
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--severity-critical-bg)',
              color: 'var(--severity-critical)',
              fontSize: '0.85rem',
              marginBottom: 16,
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Username</label>
              <input
                className="form-input"
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                minLength={3}
              />
            </div>

            {isRegister && (
              <div className="form-group">
                <label className="form-label">Email</label>
                <input
                  className="form-input"
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Enter email"
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                minLength={8}
              />
            </div>

            <button className="btn btn-primary btn-lg w-full" type="submit" disabled={loading}
              style={{ justifyContent: 'center', marginTop: 4 }}>
              {loading ? <span className="spinner" /> : (isRegister ? 'Create Account' : 'Sign In')}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: 16, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account? ' : "Don't have an account? "}
            <a href="#" onClick={e => { e.preventDefault(); setIsRegister(!isRegister); setError(''); }}>
              {isRegister ? 'Sign In' : 'Create one'}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Dashboard Page
   ═══════════════════════════════════════════════════════════════ */

function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getDashboard(), api.getHealth()])
      .then(([s, h]) => { setStats(s); setHealth(h); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-4"><div className="spinner" /></div>;

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Security Dashboard</h1>
          <p className="text-muted text-sm" style={{ marginTop: 2 }}>Real-time security assessment overview</p>
        </div>
        <div className="flex gap-2">
          <span className={`badge ${health?.ai_available ? 'badge-confirmed' : 'badge-critical'}`}>
            AI: {health?.ai_available ? 'Connected' : 'Offline'}
          </span>
          <span className="badge badge-info" style={{ background: 'rgba(59,130,246,0.12)', color: '#3b82f6' }}>
            {health?.tools_available}/{health?.tools_total} Tools
          </span>
        </div>
      </div>

      {/* Severity Stats */}
      <div className="stat-grid">
        <div className="stat-card" style={{ '--stat-color': 'var(--severity-critical)' } as any}>
          <span className="stat-label">Critical</span>
          <span className="stat-value">{stats?.critical_findings ?? 0}</span>
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--severity-high)' } as any}>
          <span className="stat-label">High</span>
          <span className="stat-value">{stats?.high_findings ?? 0}</span>
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--severity-medium)' } as any}>
          <span className="stat-label">Medium</span>
          <span className="stat-value">{stats?.medium_findings ?? 0}</span>
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--severity-low)' } as any}>
          <span className="stat-label">Low</span>
          <span className="stat-value">{stats?.low_findings ?? 0}</span>
        </div>
        <div className="stat-card" style={{ '--stat-color': 'var(--severity-info)' } as any}>
          <span className="stat-label">Info</span>
          <span className="stat-value">{stats?.info_findings ?? 0}</span>
        </div>
      </div>

      {/* Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Engagements</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
                {stats?.total_engagements ?? 0}
              </div>
              <div className="text-muted text-sm">Total</div>
            </div>
            <div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-success)' }}>
                {stats?.active_engagements ?? 0}
              </div>
              <div className="text-muted text-sm">Active</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Findings Overview</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--status-confirmed)' }}>
                {stats?.confirmed_findings ?? 0}
              </div>
              <div className="text-muted text-sm">Confirmed</div>
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--status-candidate)' }}>
                {stats?.candidate_findings ?? 0}
              </div>
              <div className="text-muted text-sm">Candidates</div>
            </div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                {stats?.false_positives ?? 0}
              </div>
              <div className="text-muted text-sm">False Pos.</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Scan Activity</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-info)' }}>
                {stats?.active_scans ?? 0}
              </div>
              <div className="text-muted text-sm">Running</div>
            </div>
            <div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-success)' }}>
                {stats?.completed_scans ?? 0}
              </div>
              <div className="text-muted text-sm">Completed</div>
            </div>
          </div>
        </div>
      </div>

      {/* System Health */}
      {health && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">System Health</span>
            <span className="badge badge-confirmed">● {health.status}</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            <div><span className="text-muted text-sm">Version</span><br/><span className="text-mono">{health.version}</span></div>
            <div><span className="text-muted text-sm">AI Provider</span><br/><span className="text-mono">{health.ai_provider}</span></div>
            <div><span className="text-muted text-sm">Uptime</span><br/><span className="text-mono">{Math.floor(health.uptime_seconds / 60)}m {Math.floor(health.uptime_seconds % 60)}s</span></div>
            <div><span className="text-muted text-sm">Database</span><br/><span className="text-mono">Connected</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Engagements Page
   ═══════════════════════════════════════════════════════════════ */

function EngagementsPage() {
  const [engagements, setEngagements] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadEngagements = useCallback(() => {
    api.getEngagements().then(setEngagements).catch(() => {}).finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadEngagements(); }, [loadEngagements]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    try {
      await api.createEngagement({
        name: formData.get('name'),
        description: formData.get('description'),
        operating_profile: formData.get('profile'),
        scopes: formData.get('scope_origin') ? [{
          scope_type: 'include',
          origin: formData.get('scope_origin'),
        }] : [],
      });
      setShowCreate(false);
      loadEngagements();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const statusColors: Record<string, string> = {
    draft: 'var(--text-muted)',
    active: 'var(--accent-success)',
    paused: 'var(--accent-warning)',
    completed: 'var(--accent-primary)',
    cancelled: 'var(--accent-danger)',
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="flex items-center justify-between">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Engagements</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <span style={{ width: 16, height: 16 }}>{icons.plus}</span> New Engagement
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ borderColor: 'var(--accent-primary)', borderWidth: 2 }}>
          <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Create Engagement</h3>
          <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Name</label>
              <input className="form-input" name="name" placeholder="e.g. Q4 Security Assessment" required />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <input className="form-input" name="description" placeholder="Describe the scope and objectives" />
            </div>
            <div className="form-group">
              <label className="form-label">Operating Profile</label>
              <select className="form-input" name="profile" defaultValue="passive">
                <option value="passive">Passive — Read-only discovery</option>
                <option value="active">Active — Authorized testing</option>
                <option value="lab">Lab — Isolated environment</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Target Origin (include scope)</label>
              <input className="form-input" name="scope_origin" placeholder="https://example.com" />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary">Create</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center p-4"><div className="spinner" /></div>
      ) : engagements.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <span style={{ width: 48, height: 48, color: 'var(--text-muted)', display: 'inline-block' }}>{icons.target}</span>
          <h3 style={{ marginTop: 16, color: 'var(--text-secondary)' }}>No engagements yet</h3>
          <p className="text-muted text-sm" style={{ marginTop: 4 }}>Create your first engagement to start assessing targets.</p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Profile</th>
                <th>Created</th>
                <th>Scopes</th>
              </tr>
            </thead>
            <tbody>
              {engagements.map(eng => (
                <tr key={eng.id}>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{eng.name}</td>
                  <td>
                    <span className="badge" style={{
                      background: `${statusColors[eng.status] || 'var(--text-muted)'}22`,
                      color: statusColors[eng.status] || 'var(--text-muted)',
                    }}>
                      {eng.status}
                    </span>
                  </td>
                  <td><span className="text-mono text-sm">{eng.operating_profile}</span></td>
                  <td className="text-sm">{new Date(eng.created_at).toLocaleDateString()}</td>
                  <td className="text-sm text-muted">{eng.scopes?.length || 0} rules</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Tools Page
   ═══════════════════════════════════════════════════════════════ */

function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTools()
      .then(data => setTools(data.tools || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-4"><div className="spinner" /></div>;

  const available = tools.filter(t => t.available);
  const missing = tools.filter(t => !t.available);

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Tool Inventory</h1>
          <p className="text-muted text-sm" style={{ marginTop: 2 }}>
            {available.length} of {tools.length} tools available
          </p>
        </div>
      </div>

      {available.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title" style={{ color: 'var(--accent-success)' }}>✓ Available Tools</span>
          </div>
          <div className="table-container" style={{ border: 'none' }}>
            <table>
              <thead>
                <tr><th>Tool</th><th>Version</th><th>Path</th><th>Description</th></tr>
              </thead>
              <tbody>
                {available.map(t => (
                  <tr key={t.name}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{t.name}</td>
                    <td className="text-mono text-sm">{t.version.substring(0, 60)}</td>
                    <td className="text-mono text-sm text-muted">{t.path}</td>
                    <td className="text-sm">{t.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {missing.length > 0 && (
        <div className="card">
          <div className="card-header">
            <span className="card-title" style={{ color: 'var(--accent-warning)' }}>⚠ Missing Tools</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 8 }}>
            {missing.map(t => (
              <div key={t.name} style={{
                padding: '12px 16px',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <div>
                  <span style={{ fontWeight: 600 }}>{t.name}</span>
                  <span className="text-muted text-sm" style={{ marginLeft: 8 }}>({t.description})</span>
                </div>
                <code className="text-mono text-sm" style={{
                  padding: '4px 8px',
                  background: 'var(--bg-card)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--accent-secondary)',
                }}>
                  {t.install_instructions}
                </code>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Placeholder Pages
   ═══════════════════════════════════════════════════════════════ */

function PlaceholderPage({ title, icon }: { title: string; icon: React.ReactNode }) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center" style={{ minHeight: 400, textAlign: 'center' }}>
      <span style={{ width: 64, height: 64, color: 'var(--text-muted)', display: 'inline-block' }}>{icon}</span>
      <h2 style={{ marginTop: 16, fontWeight: 600 }}>{title}</h2>
      <p className="text-muted text-sm" style={{ marginTop: 4, maxWidth: 400 }}>
        This module is part of the SentinelWeb AI platform and will be fully operational when connected to the backend assessment engine.
      </p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   Main App
   ═══════════════════════════════════════════════════════════════ */

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<Page>('dashboard');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [checking, setChecking] = useState(true);

  // Check existing session
  useEffect(() => {
    const token = localStorage.getItem('sentinel_token');
    if (token) {
      api.getMe()
        .then(u => setUser(u))
        .catch(() => api.clearToken())
        .finally(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  // Theme
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const handleLogout = () => {
    api.clearToken();
    setUser(null);
  };

  if (checking) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
      }}>
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  const navItems: { id: Page; label: string; icon: React.ReactNode; section?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: icons.dashboard, section: 'OVERVIEW' },
    { id: 'engagements', label: 'Engagements', icon: icons.target },
    { id: 'findings', label: 'Findings', icon: icons.bug, section: 'ASSESSMENT' },
    { id: 'scans', label: 'Scans', icon: icons.scan },
    { id: 'tools', label: 'Tools', icon: icons.tools },
    { id: 'blueteam', label: 'Blue Team', icon: icons.shield, section: 'DEFENSE' },
    { id: 'settings', label: 'Settings', icon: icons.settings, section: 'SYSTEM' },
  ];

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <DashboardPage />;
      case 'engagements': return <EngagementsPage />;
      case 'tools': return <ToolsPage />;
      case 'findings': return <FindingsPage />;
      case 'scans': return <ScansPage />;
      case 'blueteam': return <BlueTeamPage />;
      case 'settings': return <SettingsPage />;
      default: return <DashboardPage />;
    }
  };

  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="flex items-center gap-3" style={{ flex: 1 }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}>
            <span style={{ width: 16, height: 16, color: 'white' }}>{icons.shield}</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: '1rem', letterSpacing: '-0.01em' }}>
            SentinelWeb <span style={{ color: 'var(--accent-primary)' }}>AI</span>
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            title="Toggle theme"
          >
            <span style={{ width: 14, height: 14 }}>{theme === 'dark' ? icons.sun : icons.moon}</span>
          </button>

          <div className="flex items-center gap-2">
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: 'var(--accent-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'white',
            }}>
              {user.username[0].toUpperCase()}
            </div>
            <span className="text-sm" style={{ fontWeight: 500 }}>{user.username}</span>
            <span className="badge" style={{
              background: 'var(--accent-primary-glow)',
              color: 'var(--accent-primary)',
              fontSize: '0.65rem',
            }}>
              {user.role}
            </span>
          </div>

          <button className="btn btn-secondary btn-sm" onClick={handleLogout} title="Sign out">
            <span style={{ width: 14, height: 14 }}>{icons.logout}</span>
          </button>
        </div>
      </header>

      {/* Sidebar */}
      <nav className="app-sidebar">
        {navItems.map(item => (
          <div key={item.id}>
            {item.section && <div className="nav-section">{item.section}</div>}
            <div
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </div>
          </div>
        ))}
      </nav>

      {/* Main Content */}
      <main className="app-main">
        {renderPage()}
      </main>
    </div>
  );
}
