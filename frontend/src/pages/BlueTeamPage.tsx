import { useState, useEffect } from 'react';
import api from '../services/api';

export default function BlueTeamPage() {
  const [engagements, setEngagements] = useState<any[]>([]);
  const [selectedEngId, setSelectedEngId] = useState<string>('');
  const [tab, setTab] = useState<'posture' | 'waf' | 'sigma' | 'nginx' | 'reports'>('posture');
  const [posture, setPosture] = useState<any | null>(null);
  const [wafRules, setWafRules] = useState<any[]>([]);
  const [sigmaRules, setSigmaRules] = useState<any[]>([]);
  const [nginxConfig, setNginxConfig] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    api.getEngagements()
      .then(engs => {
        setEngagements(engs);
        if (engs.length > 0) {
          setSelectedEngId(engs[0].id);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const loadDefensiveData = (engId: string) => {
    if (!engId) return;
    setLoading(true);
    Promise.all([
      api.getDefensivePosture(engId).catch(() => null),
      api.getWafRules(engId).catch(() => ({ rules: [] })),
      api.getSigmaRules(engId).catch(() => ({ rules: [] })),
      api.getNginxConfig(engId).catch(() => ''),
    ])
      .then(([pos, waf, sig, ngx]) => {
        setPosture(pos);
        setWafRules(waf.rules || []);
        setSigmaRules(sig.rules || []);
        setNginxConfig(ngx || '');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (selectedEngId) {
      loadDefensiveData(selectedEngId);
    }
  }, [selectedEngId]);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDownloadReport = async () => {
    if (!selectedEngId) return;
    try {
      const md = await api.getMarkdownReport(selectedEngId);
      const blob = new Blob([md], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nighthawk-report-${selectedEngId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || 'Report download failed');
    }
  };

  const handleOpenHtmlReport = async () => {
    if (!selectedEngId) return;
    try {
      const html = await api.getHtmlReport(selectedEngId);
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (err: any) {
      alert(err.message || 'Opening HTML report failed');
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="flex items-center justify-between" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Blue Team & Defensive Engineering</h1>
          <p className="text-muted text-sm">Security telemetry correlation, virtual patching, and detection rule synthesis</p>
        </div>

        <div className="flex items-center gap-3">
          <select
            className="form-input"
            value={selectedEngId}
            onChange={e => setSelectedEngId(e.target.value)}
            style={{ minWidth: 220 }}
          >
            {engagements.map(e => (
              <option key={e.id} value={e.id}>{e.name}</option>
            ))}
          </select>
          <button className="btn btn-secondary btn-sm" onClick={() => loadDefensiveData(selectedEngId)}>
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 10 }}>
        {(['posture', 'waf', 'sigma', 'nginx', 'reports'] as const).map(t => (
          <button
            key={t}
            className={`btn btn-sm ${tab === t ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setTab(t)}
            style={{ textTransform: 'capitalize' }}
          >
            {t === 'waf' ? 'WAF Rules' : t === 'sigma' ? 'Sigma Rules' : t === 'nginx' ? 'Nginx Config' : t === 'reports' ? 'Reports' : 'Defense Posture'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-4"><div className="spinner" /></div>
      ) : (
        <div>
          {/* Posture Overview Tab */}
          {tab === 'posture' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                  <div style={{
                    width: 80,
                    height: 80,
                    borderRadius: '50%',
                    background: (posture?.posture_score || 0) > 75
                      ? 'rgba(16,185,129,0.15)'
                      : (posture?.posture_score || 0) > 50
                      ? 'rgba(245,158,11,0.15)'
                      : 'rgba(239,68,68,0.15)',
                    border: `3px solid ${(posture?.posture_score || 0) > 75 ? '#10b981' : (posture?.posture_score || 0) > 50 ? '#f59e0b' : '#ef4444'}`,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '1.4rem',
                    color: (posture?.posture_score || 0) > 75 ? '#10b981' : (posture?.posture_score || 0) > 50 ? '#f59e0b' : '#ef4444',
                  }}>
                    {posture?.posture_score ?? 100}%
                  </div>
                  <div>
                    <h3 style={{ fontWeight: 700 }}>Posture Score</h3>
                    <p className="text-muted text-sm">Rating: <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{posture?.risk_level || 'Normal'}</span></p>
                    <span className="text-xs text-muted">Total Flaws: {posture?.total_flaws || 0}</span>
                  </div>
                </div>

                <div className="card">
                  <span className="text-muted text-xs font-semibold">Risk Breakdown</span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 12 }}>
                    <div>
                      <span className="text-sm font-semibold" style={{ color: '#ef4444' }}>Critical: {posture?.critical_count || 0}</span>
                    </div>
                    <div>
                      <span className="text-sm font-semibold" style={{ color: '#f59e0b' }}>High: {posture?.high_count || 0}</span>
                    </div>
                    <div>
                      <span className="text-sm font-semibold" style={{ color: '#3b82f6' }}>Medium: {posture?.medium_count || 0}</span>
                    </div>
                    <div>
                      <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Low: {posture?.low_count || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* WAF Rules Tab */}
          {tab === 'waf' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {wafRules.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                  <p className="text-muted">No WAF rules required for current findings.</p>
                </div>
              ) : (
                wafRules.map(r => (
                  <div key={r.finding_id} className="card">
                    <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
                      <span style={{ fontWeight: 600 }}>{r.title}</span>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => copyToClipboard(r.rule, `waf-${r.finding_id}`)}
                      >
                        {copied === `waf-${r.finding_id}` ? 'Copied!' : 'Copy Rule'}
                      </button>
                    </div>
                    <pre style={{
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 4,
                      fontSize: '0.8rem',
                      fontFamily: 'var(--font-mono)',
                      overflowX: 'auto',
                    }}>
                      {r.rule}
                    </pre>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Sigma Rules Tab */}
          {tab === 'sigma' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {sigmaRules.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                  <p className="text-muted">No Sigma rules generated.</p>
                </div>
              ) : (
                sigmaRules.map(r => (
                  <div key={r.finding_id} className="card">
                    <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
                      <span style={{ fontWeight: 600 }}>{r.title}</span>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => copyToClipboard(r.rule, `sig-${r.finding_id}`)}
                      >
                        {copied === `sig-${r.finding_id}` ? 'Copied!' : 'Copy Rule'}
                      </button>
                    </div>
                    <pre style={{
                      padding: 12,
                      background: 'var(--bg-tertiary)',
                      borderRadius: 4,
                      fontSize: '0.8rem',
                      fontFamily: 'var(--font-mono)',
                      overflowX: 'auto',
                    }}>
                      {r.rule}
                    </pre>
                  </div>
                ))
              )}
            </div>
          )}

          {/* Nginx Config Tab */}
          {tab === 'nginx' && (
            <div className="card">
              <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                <span style={{ fontWeight: 600 }}>Recommended Nginx Security Directives</span>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => copyToClipboard(nginxConfig, 'nginx')}
                >
                  {copied === 'nginx' ? 'Copied!' : 'Copy Configuration'}
                </button>
              </div>
              <pre style={{
                padding: 16,
                background: 'var(--bg-tertiary)',
                borderRadius: 6,
                fontSize: '0.85rem',
                fontFamily: 'var(--font-mono)',
                overflowX: 'auto',
                lineHeight: 1.5,
              }}>
                {nginxConfig || '# Loading configuration...'}
              </pre>
            </div>
          )}

          {/* Reports Tab */}
          {tab === 'reports' && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 600 }}>
              <h3 style={{ fontWeight: 600 }}>Executive & Technical Security Reports</h3>
              <p className="text-muted text-sm">
                Generate formal penetration testing deliverables summarizing discovered vulnerabilities, CVSS score vectors, technical proof of concepts, and remediation roadmap.
              </p>
              <div className="flex gap-3" style={{ marginTop: 8 }}>
                <button className="btn btn-primary" onClick={handleDownloadReport}>
                  Download Markdown Report (.md)
                </button>
                <button className="btn btn-secondary" onClick={handleOpenHtmlReport}>
                  View / Print HTML Report
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
