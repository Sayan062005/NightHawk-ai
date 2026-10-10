import { useState, useEffect } from 'react';
import api from '../services/api';

export default function FindingsPage() {
  const [engagements, setEngagements] = useState<any[]>([]);
  const [selectedEngId, setSelectedEngId] = useState<string>('');
  const [findings, setFindings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [selectedFinding, setSelectedFinding] = useState<any | null>(null);
  const [remediating, setRemediating] = useState(false);

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

  const loadFindings = (engId: string) => {
    if (!engId) return;
    setLoading(true);
    api.getFindings(engId)
      .then(f => {
        setFindings(f);
        if (selectedFinding) {
          const updated = f.find((item: any) => item.id === selectedFinding.id);
          if (updated) setSelectedFinding(updated);
        }
      })
      .catch(() => setFindings([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (selectedEngId) {
      loadFindings(selectedEngId);
    }
  }, [selectedEngId]);

  const handleRemediate = async (findingId: string) => {
    if (!selectedEngId) return;
    setRemediating(true);
    try {
      const updated = await api.remediateFinding(selectedEngId, findingId);
      setSelectedFinding(updated);
      setFindings(prev => prev.map(f => f.id === updated.id ? updated : f));
    } catch (err: any) {
      alert(err.message || 'Remediation failed');
    } finally {
      setRemediating(false);
    }
  };

  const handleStatusChange = async (findingId: string, newStatus: string) => {
    if (!selectedEngId) return;
    try {
      const updated = await api.updateFinding(selectedEngId, findingId, { status: newStatus });
      setSelectedFinding(updated);
      setFindings(prev => prev.map(f => f.id === updated.id ? updated : f));
    } catch (err: any) {
      alert(err.message || 'Status update failed');
    }
  };

  const filteredFindings = findings.filter(f => {
    if (filterSeverity === 'all') return true;
    return f.severity?.toLowerCase() === filterSeverity.toLowerCase();
  });

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev?.toLowerCase()) {
      case 'critical': return 'badge-danger';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-info';
      case 'low': return 'badge-secondary';
      default: return 'badge-muted';
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="flex items-center justify-between" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Vulnerability Findings</h1>
          <p className="text-muted text-sm">Review, verify, and remediate security weaknesses</p>
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
          <button className="btn btn-secondary btn-sm" onClick={() => loadFindings(selectedEngId)}>
            Refresh
          </button>
        </div>
      </div>

      {/* Severity Filter Pills */}
      <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
        {['all', 'critical', 'high', 'medium', 'low', 'info'].map(sev => {
          const count = sev === 'all'
            ? findings.length
            : findings.filter(f => f.severity?.toLowerCase() === sev).length;
          return (
            <button
              key={sev}
              className={`btn btn-sm ${filterSeverity === sev ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilterSeverity(sev)}
              style={{ textTransform: 'capitalize' }}
            >
              {sev} ({count})
            </button>
          );
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-4"><div className="spinner" /></div>
      ) : filteredFindings.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <h3 style={{ color: 'var(--text-secondary)' }}>No findings in this category</h3>
          <p className="text-muted text-sm" style={{ marginTop: 4 }}>
            Run a vulnerability scan or import a HAR file to discover issues.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: selectedFinding ? '1fr 1fr' : '1fr', gap: 16 }}>
          {/* Findings List */}
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>CVSS</th>
                  <th>Affected Route</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredFindings.map(f => (
                  <tr
                    key={f.id}
                    onClick={() => setSelectedFinding(f)}
                    style={{
                      cursor: 'pointer',
                      background: selectedFinding?.id === f.id ? 'var(--bg-card-hover)' : undefined,
                    }}
                  >
                    <td>
                      <span className={`badge ${getSeverityBadgeClass(f.severity)}`} style={{ textTransform: 'uppercase' }}>
                        {f.severity}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{f.title}</td>
                    <td>
                      {f.cvss_score ? (
                        <span className="badge" style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444' }}>
                          {f.cvss_score}
                        </span>
                      ) : (
                        <span className="text-muted text-sm">—</span>
                      )}
                    </td>
                    <td className="text-mono text-sm" style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.affected_route || f.affected_asset || '—'}
                    </td>
                    <td>
                      <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                        {f.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Detailed Drawer */}
          {selectedFinding && (
            <div className="card animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="flex items-center justify-between">
                <span className={`badge ${getSeverityBadgeClass(selectedFinding.severity)}`} style={{ textTransform: 'uppercase', fontSize: '0.8rem' }}>
                  {selectedFinding.severity}
                </span>
                <div className="flex items-center gap-2">
                  <select
                    className="form-input"
                    value={selectedFinding.status}
                    onChange={e => handleStatusChange(selectedFinding.id, e.target.value)}
                    style={{ padding: '4px 8px', fontSize: '0.8rem' }}
                  >
                    <option value="candidate">Candidate</option>
                    <option value="needs_verification">Needs Verification</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="mitigated">Mitigated</option>
                    <option value="false_positive">False Positive</option>
                  </select>
                  <button className="btn btn-secondary btn-sm" onClick={() => setSelectedFinding(null)}>✕</button>
                </div>
              </div>

              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{selectedFinding.title}</h2>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {selectedFinding.cwe_id && (
                  <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--accent-info)' }}>
                    {selectedFinding.cwe_id}
                  </span>
                )}
                {selectedFinding.owasp_category && (
                  <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                    {selectedFinding.owasp_category}
                  </span>
                )}
                {selectedFinding.cvss_score && (
                  <span className="badge" style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}>
                    CVSS {selectedFinding.cvss_score}
                  </span>
                )}
              </div>

              <div>
                <span className="text-muted text-sm font-semibold">Affected Route / Asset:</span>
                <div className="text-mono text-sm" style={{ marginTop: 4, padding: 8, background: 'var(--bg-tertiary)', borderRadius: 4 }}>
                  {selectedFinding.affected_route || selectedFinding.affected_asset}
                </div>
              </div>

              <div>
                <span className="text-muted text-sm font-semibold">Description:</span>
                <p style={{ marginTop: 4, lineHeight: 1.5, fontSize: '0.9rem' }}>{selectedFinding.description}</p>
              </div>

              {selectedFinding.reproduction_steps && (
                <div>
                  <span className="text-muted text-sm font-semibold">Reproduction Steps:</span>
                  <pre style={{
                    marginTop: 4,
                    padding: 10,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 4,
                    fontSize: '0.8rem',
                    overflowX: 'auto',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {selectedFinding.reproduction_steps}
                  </pre>
                </div>
              )}

              {/* Remediation Section */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
                  <span className="font-semibold text-sm">Remediation & Fix:</span>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleRemediate(selectedFinding.id)}
                    disabled={remediating}
                  >
                    {remediating ? 'AI Analyzing...' : 'Generate AI Fix'}
                  </button>
                </div>

                {selectedFinding.remediation_guidance ? (
                  <pre style={{
                    padding: 12,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 6,
                    fontSize: '0.85rem',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--accent-success)',
                    lineHeight: 1.5,
                  }}>
                    {selectedFinding.remediation_guidance}
                  </pre>
                ) : (
                  <p className="text-muted text-sm">
                    No remediation generated yet. Click "Generate AI Fix" to produce code patches and regression tests.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
