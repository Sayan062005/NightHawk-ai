import { useState, useEffect, useRef } from 'react';
import api from '../services/api';

export default function ScansPage() {
  const [engagements, setEngagements] = useState<any[]>([]);
  const [selectedEngId, setSelectedEngId] = useState<string>('');
  const [scans, setScans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [uploadingHar, setUploadingHar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form inputs
  const [scanTarget, setScanTarget] = useState('');
  const [scanType, setScanType] = useState('full_scan');
  const [scanTool, setScanTool] = useState('native');

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

  const loadScans = (engId: string) => {
    if (!engId) return;
    api.getScans(engId)
      .then(s => setScans(s))
      .catch(() => setScans([]));
  };

  useEffect(() => {
    if (selectedEngId) {
      loadScans(selectedEngId);
      const interval = setInterval(() => {
        loadScans(selectedEngId);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [selectedEngId]);

  const handleLaunchScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEngId || !scanTarget) return;
    try {
      await api.createScan(selectedEngId, {
        scan_type: scanType,
        target: scanTarget,
        tool_name: scanTool,
      });
      setShowCreateModal(false);
      setScanTarget('');
      loadScans(selectedEngId);
    } catch (err: any) {
      alert(err.message || 'Failed to start scan');
    }
  };

  const handleHarFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedEngId) return;
    setUploadingHar(true);
    try {
      const res = await api.uploadHar(selectedEngId, file);
      alert(`Success! Analyzed ${res.total_requests} requests and imported ${res.findings_imported} vulnerabilities from ${file.name}.`);
      loadScans(selectedEngId);
    } catch (err: any) {
      alert(err.message || 'HAR upload failed');
    } finally {
      setUploadingHar(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="flex items-center justify-between" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Scan Manager</h1>
          <p className="text-muted text-sm">Automated reconnaissance, vulnerability scans, and traffic ingestion</p>
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

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleHarFileChange}
            accept=".har,application/json"
            style={{ display: 'none' }}
          />

          <button
            className="btn btn-secondary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingHar}
          >
            {uploadingHar ? 'Analyzing HAR...' : 'Import .HAR File'}
          </button>

          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            + Launch Scan
          </button>
        </div>
      </div>

      {/* Launch Scan Modal */}
      {showCreateModal && (
        <div className="card" style={{ borderColor: 'var(--accent-primary)', borderWidth: 2 }}>
          <h3 style={{ marginBottom: 16, fontWeight: 600 }}>Configure Security Scan</h3>
          <form onSubmit={handleLaunchScan} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="form-group">
              <label className="form-label">Target URL / Host</label>
              <input
                className="form-input"
                value={scanTarget}
                onChange={e => setScanTarget(e.target.value)}
                placeholder="https://example.com"
                required
              />
              <span className="text-muted text-xs" style={{ marginTop: 4 }}>
                Target must be included in the engagement scope rules.
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Scan Type</label>
                <select
                  className="form-input"
                  value={scanType}
                  onChange={e => setScanType(e.target.value)}
                >
                  <option value="full_scan">Full Scan (Ports + TLS + HTTP Headers)</option>
                  <option value="web_audit">Web Header & Cookie Security Audit</option>
                  <option value="port_scan">TCP Port Discovery</option>
                  <option value="tls_inspection">TLS/SSL Cipher & Certificate Audit</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Tool Preference</label>
                <select
                  className="form-input"
                  value={scanTool}
                  onChange={e => setScanTool(e.target.value)}
                >
                  <option value="native">Native Engine (Zero Dependencies)</option>
                  <option value="nmap">Nmap Network Scanner (if available)</option>
                  <option value="testssl">testssl.sh TLS Inspector (if available)</option>
                </select>
              </div>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn btn-primary">Start Scan</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Scans Table */}
      {scans.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <h3 style={{ color: 'var(--text-secondary)' }}>No scans executed yet</h3>
          <p className="text-muted text-sm" style={{ marginTop: 4 }}>
            Click "Launch Scan" or "Import .HAR File" to begin security assessments on approved targets.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Target</th>
                <th>Type</th>
                <th>Progress</th>
                <th>Summary</th>
                <th>Started</th>
              </tr>
            </thead>
            <tbody>
              {scans.map(scan => (
                <tr key={scan.id}>
                  <td>
                    <span
                      className="badge"
                      style={{
                        background: scan.status === 'completed'
                          ? 'rgba(16,185,129,0.15)'
                          : scan.status === 'running'
                          ? 'rgba(59,130,246,0.15)'
                          : scan.status === 'failed'
                          ? 'rgba(239,68,68,0.15)'
                          : 'var(--bg-tertiary)',
                        color: scan.status === 'completed'
                          ? '#10b981'
                          : scan.status === 'running'
                          ? '#3b82f6'
                          : scan.status === 'failed'
                          ? '#ef4444'
                          : 'var(--text-secondary)',
                        textTransform: 'uppercase',
                        fontWeight: 600,
                      }}
                    >
                      {scan.status}
                    </span>
                  </td>
                  <td className="text-mono" style={{ fontWeight: 600 }}>{scan.target}</td>
                  <td>
                    <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                      {scan.scan_type}
                    </span>
                  </td>
                  <td style={{ minWidth: 140 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 6, background: 'var(--bg-tertiary)', borderRadius: 3, overflow: 'hidden' }}>
                        <div style={{
                          width: `${scan.progress_percent}%`,
                          height: '100%',
                          background: scan.status === 'failed' ? '#ef4444' : 'var(--accent-primary)',
                          transition: 'width 0.3s ease',
                        }} />
                      </div>
                      <span className="text-xs text-muted">{scan.progress_percent}%</span>
                    </div>
                  </td>
                  <td className="text-sm text-muted" style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {scan.error_message ? (
                      <span style={{ color: '#ef4444' }}>{scan.error_message}</span>
                    ) : (
                      scan.result_summary || 'Running...'
                    )}
                  </td>
                  <td className="text-sm text-muted">
                    {scan.started_at ? new Date(scan.started_at).toLocaleTimeString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
