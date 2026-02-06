import React, { useState, useEffect } from 'react';

/**
 * GovernanceDashboard - Agent Governance & Quality Monitoring
 * 
 * NYC 2026-2027 Compliance Dashboard featuring:
 * - Agent Flow Accuracy tracking
 * - Human-on-the-loop monitoring  
 * - Token Cost Attribution per agent
 * - Time-to-First-Token (TTFT) performance
 * - AI Safety & Bias Audit (NYC Local Law 144)
 * - Legal Sandbox review queue
 * - Immutable audit log verification
 */
const GovernanceDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [biasAudit, setBiasAudit] = useState(null);
  const [legalReviews, setLegalReviews] = useState(null);
  const [logVerification, setLogVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState('ALL');

  // Fetch all governance data
  useEffect(() => {
    fetchGovernanceData();
    const interval = setInterval(fetchGovernanceData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchGovernanceData = async () => {
    try {
      // Fetch dashboard summary
      const dashRes = await fetch('http://localhost:8000/api/governance/dashboard');
      const dashData = await dashRes.json();
      setDashboardData(dashData);

      // Fetch latest bias audit
      const biasRes = await fetch('http://localhost:8000/api/governance/bias-audit/latest');
      const biasData = await biasRes.json();
      setBiasAudit(biasData);

      // Fetch pending legal reviews
      const legalRes = await fetch('http://localhost:8000/api/governance/legal-sandbox/pending');
      const legalData = await legalRes.json();
      setLegalReviews(legalData);

      // Verify immutable log
      const logRes = await fetch('http://localhost:8000/api/governance/immutable-log/verify');
      const logData = await logRes.json();
      setLogVerification(logData);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching governance data:', error);
      setLoading(false);
    }
  };

  const approveProof = async (proofId) => {
    try {
      await fetch(`http://localhost:8000/api/governance/legal-sandbox/approve/${proofId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: 'dashboard_user',
          notes: 'Approved from governance dashboard'
        })
      });
      fetchGovernanceData(); // Refresh
    } catch (error) {
      console.error('Error approving proof:', error);
    }
  };

  const rejectProof = async (proofId) => {
    try {
      await fetch(`http://localhost:8000/api/governance/legal-sandbox/reject/${proofId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: 'dashboard_user',
          reason: 'Rejected from governance dashboard - requires revision'
        })
      });
      fetchGovernanceData(); // Refresh
    } catch (error) {
      console.error('Error rejecting proof:', error);
    }
  };

  const getAgentColor = (agentType) => {
    const colors = {
      'Scout': '#3b82f6',
      'Guard': '#22c55e',
      'Watchman': '#f59e0b',
      'Fixer': '#ef4444',
      'Feasibility': '#8b5cf6',
      'ALL': '#6b7280'
    };
    return colors[agentType] || '#6b7280';
  };

  const styles = {
    dashboard: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: '#f8fafc',
      minHeight: '100vh',
      padding: '24px'
    },
    header: {
      marginBottom: '32px'
    },
    title: {
      fontSize: '32px',
      fontWeight: '700',
      color: '#1e293b',
      marginBottom: '8px'
    },
    subtitle: {
      fontSize: '16px',
      color: '#64748b',
      marginBottom: '16px'
    },
    agentSelector: {
      display: 'flex',
      gap: '8px',
      marginBottom: '24px',
      flexWrap: 'wrap'
    },
    agentButton: {
      padding: '8px 16px',
      borderRadius: '6px',
      border: '2px solid #e2e8f0',
      backgroundColor: 'white',
      cursor: 'pointer',
      fontSize: '14px',
      fontWeight: '600',
      transition: 'all 0.2s'
    },
    agentButtonActive: {
      borderColor: '#3b82f6',
      backgroundColor: '#3b82f6',
      color: 'white'
    },
    metricsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '20px',
      marginBottom: '32px'
    },
    metricCard: {
      backgroundColor: 'white',
      padding: '20px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0'
    },
    metricLabel: {
      fontSize: '12px',
      color: '#64748b',
      marginBottom: '8px',
      fontWeight: '600',
      textTransform: 'uppercase'
    },
    metricValue: {
      fontSize: '32px',
      fontWeight: '700',
      color: '#1e293b',
      marginBottom: '4px'
    },
    metricSubtext: {
      fontSize: '12px',
      color: '#64748b'
    },
    sectionCard: {
      backgroundColor: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0',
      marginBottom: '24px'
    },
    sectionTitle: {
      fontSize: '20px',
      fontWeight: '600',
      color: '#1e293b',
      marginBottom: '16px'
    },
    table: {
      width: '100%',
      borderCollapse: 'collapse'
    },
    th: {
      textAlign: 'left',
      padding: '12px',
      borderBottom: '2px solid #e2e8f0',
      fontSize: '12px',
      fontWeight: '600',
      color: '#64748b',
      textTransform: 'uppercase'
    },
    td: {
      padding: '12px',
      borderBottom: '1px solid #e2e8f0',
      fontSize: '14px',
      color: '#1e293b'
    },
    badge: {
      display: 'inline-block',
      padding: '4px 12px',
      borderRadius: '12px',
      fontSize: '11px',
      fontWeight: '600',
      textTransform: 'uppercase'
    },
    successBadge: {
      backgroundColor: '#dcfce7',
      color: '#16a34a'
    },
    warningBadge: {
      backgroundColor: '#fef3c7',
      color: '#ca8a04'
    },
    dangerBadge: {
      backgroundColor: '#fee2e2',
      color: '#dc2626'
    },
    button: {
      padding: '6px 12px',
      borderRadius: '6px',
      border: 'none',
      fontSize: '12px',
      fontWeight: '600',
      cursor: 'pointer',
      marginRight: '8px'
    },
    approveButton: {
      backgroundColor: '#22c55e',
      color: 'white'
    },
    rejectButton: {
      backgroundColor: '#ef4444',
      color: 'white'
    }
  };

  if (loading) {
    return (
      <div style={styles.dashboard}>
        <div style={{textAlign: 'center', paddingTop: '100px'}}>
          <div style={{fontSize: '48px'}}>⏳</div>
          <div style={{fontSize: '18px', color: '#64748b', marginTop: '16px'}}>
            Loading Governance Dashboard...
          </div>
        </div>
      </div>
    );
  }

  const agents = ['ALL', 'Scout', 'Guard', 'Watchman', 'Fixer', 'Feasibility'];
  const currentData = selectedAgent === 'ALL' 
    ? dashboardData?.overall_accuracy 
    : dashboardData?.agent_flow_accuracy?.[selectedAgent];

  return (
    <div style={styles.dashboard}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🛡️ Agent Governance & Quality Dashboard</h1>
        <p style={styles.subtitle}>
          NYC 2026-2027 Compliance | Multi-Agent System Observability
        </p>
      </div>

      {/* Agent Selector */}
      <div style={styles.agentSelector}>
        {agents.map(agent => (
          <button
            key={agent}
            style={{
              ...styles.agentButton,
              ...(selectedAgent === agent ? styles.agentButtonActive : {}),
              borderColor: getAgentColor(agent)
            }}
            onClick={() => setSelectedAgent(agent)}
          >
            {agent}
          </button>
        ))}
      </div>

      {/* Key Metrics */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Agent Flow Accuracy</div>
          <div style={styles.metricValue}>
            {currentData?.accuracy_percent?.toFixed(1) || '0'}%
          </div>
          <div style={styles.metricSubtext}>
            {currentData?.success_auto || 0} auto / {currentData?.total_flows || 0} total
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Human Override Rate</div>
          <div style={styles.metricValue}>
            {dashboardData?.overall_override_rate?.override_rate_percent?.toFixed(1) || '0'}%
          </div>
          <div style={styles.metricSubtext}>
            {dashboardData?.overall_override_rate?.total_overrides || 0} overrides
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Cost Per Operation</div>
          <div style={styles.metricValue}>
            ${dashboardData?.overall_cost?.avg_cost_per_operation?.toFixed(4) || '0.0000'}
          </div>
          <div style={styles.metricSubtext}>
            Target: $0.007 | {dashboardData?.overall_cost?.operations_meeting_target || 0} meeting
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>TTFT Performance</div>
          <div style={styles.metricValue}>
            {dashboardData?.overall_ttft?.avg_ttft_ms?.toFixed(0) || '0'}ms
          </div>
          <div style={styles.metricSubtext}>
            Target: &lt;500ms | P95: {dashboardData?.overall_ttft?.p95_ttft_ms?.toFixed(0) || '0'}ms
          </div>
        </div>
      </div>

      {/* Bias Audit Status */}
      {biasAudit && biasAudit.status !== 'no_audits_yet' && (
        <div style={styles.sectionCard}>
          <div style={styles.sectionTitle}>
            🔍 AI Safety & Bias Audit (NYC Local Law 144)
          </div>
          
          <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px'}}>
            <div>
              <div style={{fontSize: '12px', color: '#64748b', marginBottom: '4px'}}>Audit ID</div>
              <div style={{fontSize: '14px', fontWeight: '600'}}>{biasAudit.audit_id}</div>
            </div>
            <div>
              <div style={{fontSize: '12px', color: '#64748b', marginBottom: '4px'}}>Documents Processed</div>
              <div style={{fontSize: '14px', fontWeight: '600'}}>{biasAudit.documents_processed}</div>
            </div>
            <div>
              <div style={{fontSize: '12px', color: '#64748b', marginBottom: '4px'}}>Overall Status</div>
              <span style={{
                ...styles.badge,
                ...(biasAudit.overall_bias_detected ? styles.warningBadge : styles.successBadge)
              }}>
                {biasAudit.overall_bias_detected ? 'Bias Detected' : 'No Bias'}
              </span>
            </div>
          </div>

          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Test Type</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Confidence</th>
                <th style={styles.th}>Variance</th>
              </tr>
            </thead>
            <tbody>
              {biasAudit.tests?.map((test, i) => (
                <tr key={i}>
                  <td style={styles.td}>{test.test_type.replace(/_/g, ' ')}</td>
                  <td style={styles.td}>
                    <span style={{
                      ...styles.badge,
                      ...(test.passed ? styles.successBadge : styles.dangerBadge)
                    }}>
                      {test.passed ? 'Passed' : 'Failed'}
                    </span>
                  </td>
                  <td style={styles.td}>{(test.confidence * 100).toFixed(1)}%</td>
                  <td style={styles.td}>{test.variance ? (test.variance * 100).toFixed(1) + '%' : 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {biasAudit.retraining_required && (
            <div style={{marginTop: '16px', padding: '12px', backgroundColor: '#fef3c7', borderRadius: '8px'}}>
              <strong>⚠️ Retraining Required:</strong> {biasAudit.retraining_reason}
            </div>
          )}

          <div style={{marginTop: '16px', fontSize: '12px', color: '#64748b'}}>
            Protected characteristics tested: {biasAudit.protected_characteristics_tested?.join(', ')}
            <br />
            Audit hash (SHA-256): {biasAudit.audit_hash?.substring(0, 16)}...
          </div>
        </div>
      )}

      {/* Legal Sandbox Reviews */}
      {legalReviews && legalReviews.count > 0 && (
        <div style={styles.sectionCard}>
          <div style={styles.sectionTitle}>
            ⚖️ Legal Sandbox - Pending Reviews ({legalReviews.count})
          </div>
          
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Proof ID</th>
                <th style={styles.th}>Content Type</th>
                <th style={styles.th}>Risk Score</th>
                <th style={styles.th}>Triggers</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {legalReviews.pending_reviews?.map((review) => (
                <tr key={review.proof_id}>
                  <td style={styles.td}>{review.proof_id.substring(0, 12)}...</td>
                  <td style={styles.td}>{review.content_type}</td>
                  <td style={styles.td}>
                    <span style={{
                      ...styles.badge,
                      ...(review.risk_score >= 8 ? styles.dangerBadge : 
                          review.risk_score >= 5 ? styles.warningBadge : 
                          styles.successBadge)
                    }}>
                      {review.risk_score.toFixed(1)}/10
                    </span>
                  </td>
                  <td style={styles.td}>{review.triggers_detected}</td>
                  <td style={styles.td}>
                    <span style={{
                      ...styles.badge,
                      ...(review.sandbox_status === 'REQUIRES_COUNSEL' ? styles.dangerBadge : styles.warningBadge)
                    }}>
                      {review.sandbox_status}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <button 
                      style={{...styles.button, ...styles.approveButton}}
                      onClick={() => approveProof(review.proof_id)}
                    >
                      Approve
                    </button>
                    <button 
                      style={{...styles.button, ...styles.rejectButton}}
                      onClick={() => rejectProof(review.proof_id)}
                    >
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Immutable Log Verification */}
      {logVerification && (
        <div style={styles.sectionCard}>
          <div style={styles.sectionTitle}>
            🔐 Immutable Audit Log Verification
          </div>
          
          <div style={{display: 'flex', alignItems: 'center', gap: '16px'}}>
            <div style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              backgroundColor: logVerification.chain_verified ? '#dcfce7' : '#fee2e2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '28px'
            }}>
              {logVerification.chain_verified ? '✓' : '✗'}
            </div>
            <div>
              <div style={{fontSize: '18px', fontWeight: '600', marginBottom: '4px'}}>
                Chain Status: {logVerification.status.toUpperCase()}
              </div>
              <div style={{fontSize: '14px', color: '#64748b'}}>
                {logVerification.statistics?.total_entries || 0} entries |
                SHA-256 blockchain-style verification |
                Last hash: {logVerification.statistics?.last_hash?.substring(0, 16)}...
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GovernanceDashboard;
