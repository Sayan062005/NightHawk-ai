import { useState, useEffect } from 'react';
import api from '../services/api';

export default function SettingsPage() {
  const [health, setHealth] = useState<any | null>(null);
  const [user, setUser] = useState<any | null>(null);
  const [tools, setTools] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getHealth().catch(() => null),
      api.getMe().catch(() => null),
      api.getTools().catch(() => null),
    ])
      .then(([h, u, t]) => {
        setHealth(h);
        setUser(u);
        setTools(t);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-4"><div className="spinner" /></div>;

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 800 }}>
      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>System Settings & Status</h1>
        <p className="text-muted text-sm">Platform configuration, orchestration status, and active user credentials</p>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Active User Profile</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <span className="text-muted text-xs">Username:</span>
            <div style={{ fontWeight: 600 }}>{user?.username || '—'}</div>
          </div>
          <div>
            <span className="text-muted text-xs">Email:</span>
            <div style={{ fontWeight: 600 }}>{user?.email || '—'}</div>
          </div>
          <div>
            <span className="text-muted text-xs">Role:</span>
            <span className="badge badge-info" style={{ textTransform: 'capitalize' }}>{user?.role || 'operator'}</span>
          </div>
          <div>
            <span className="text-muted text-xs">Account Status:</span>
            <span className="badge badge-success">{user?.is_active ? 'Active' : 'Disabled'}</span>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16, fontWeight: 600 }}>AI Orchestration & Infrastructure</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <span className="text-muted text-xs">AI Provider:</span>
            <div style={{ fontWeight: 600 }}>{health?.ai_provider || 'Deterministic Rule Engine'}</div>
          </div>
          <div>
            <span className="text-muted text-xs">AI Status:</span>
            <span className={`badge ${health?.ai_available ? 'badge-success' : 'badge-warning'}`}>
              {health?.ai_available ? 'Online (NVIDIA NIM / AI Core)' : 'Rule-Based Fallback'}
            </span>
          </div>
          <div>
            <span className="text-muted text-xs">Backend Engine:</span>
            <div style={{ fontWeight: 600 }}>SentinelWeb Core v{health?.version || '0.1.0'}</div>
          </div>
          <div>
            <span className="text-muted text-xs">Security Tools Available:</span>
            <div style={{ fontWeight: 600 }}>{tools?.available || 0} / {tools?.total || 0} tools detected</div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12, fontWeight: 600 }}>Safety & Scope Guardrails</h3>
        <ul style={{ paddingLeft: 20, lineHeight: 1.8, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
          <li>Strict hostname and IP validation enforcing inclusion/exclusion rules before any packet or socket is opened.</li>
          <li>Cloud metadata endpoints (AWS, GCP, Azure, Oracle, Alibaba) unconditionally blocked from testing.</li>
          <li>Automated SSRF, private subnet (RFC 1918), and DNS-rebinding guard enabled on non-lab profiles.</li>
          <li>Execution Broker argument validation prevents shell injection and restricts binaries to approved list.</li>
        </ul>
      </div>
    </div>
  );
}
