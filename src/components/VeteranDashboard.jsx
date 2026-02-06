import React, { useState, useEffect } from 'react';

/**
 * VeteranDashboard - Action Center (2027 Enhancements)
 * 
 * Transform from display dashboard to Action Center with:
 * - Fix Compliance button triggering BrokerLiaison agent
 * - Vision-Lead correlation display
 * - Profitability drain calculations
 * - Agent handshake tracking
 */
const VeteranDashboard = () => {
  const [leads, setLeads] = useState([]);
  const [selectedLead, setSelectedLead] = useState(null);
  const [draftingEndorsement, setDraftingEndorsement] = useState(false);
  const [endorsementResult, setEndorsementResult] = useState(null);
  const [calculatingRisk, setCalculatingRisk] = useState(false);
  const [riskResult, setRiskResult] = useState(null);
  const [agentStats, setAgentStats] = useState(null);

  // Mock ScopeSignal leads data
  useEffect(() => {
    const mockLeads = [
      {
        signal_id: 'SIG-001',
        project_id: 'PROJ-2027-001',
        project_name: 'Hudson Yards Tower C',
        project_address: '450 W 33rd St, New York, NY',
        contractor_name: 'Premier Construction LLC',
        status: 'CONTESTABLE',
        missing_endorsements: [
          'Additional Insured - Primary & Non-Contributory',
          'Waiver of Subrogation',
          'Per Project Aggregate'
        ],
        insurance_gaps: [
          'Pollution Liability missing',
          'Professional Liability inadequate'
        ],
        agency_requirements: ['SCA', 'DDC'],
        broker_name: 'Marsh & McLennan',
        broker_email: 'nyc.construction@marsh.com',
        has_active_monitoring: true,
        project_value: 2500000,
        profit_margin: 0.15
      },
      {
        signal_id: 'SIG-002',
        project_id: 'PROJ-2027-002',
        project_name: 'Brooklyn School Renovation',
        project_address: '123 Atlantic Ave, Brooklyn, NY',
        contractor_name: 'EduBuild Systems',
        status: 'CONTESTABLE',
        missing_endorsements: [
          'Additional Insured',
          'Notice of Cancellation - 30 days'
        ],
        insurance_gaps: [
          'Lead-Based Paint Coverage missing'
        ],
        agency_requirements: ['SCA', 'HPD'],
        broker_name: 'Willis Towers Watson',
        broker_email: 'schools@willistowerswatson.com',
        has_active_monitoring: true,
        project_value: 1200000,
        profit_margin: 0.18
      },
      {
        signal_id: 'SIG-003',
        project_id: 'PROJ-2027-003',
        project_name: 'Queens Highway Expansion',
        project_address: 'Grand Central Parkway, Queens, NY',
        contractor_name: 'RoadMaster Inc',
        status: 'MONITORING',
        missing_endorsements: [
          'Highway Traffic Liability'
        ],
        insurance_gaps: [],
        agency_requirements: ['DOT'],
        broker_name: 'Aon Construction',
        broker_email: 'transport@aon.com',
        has_active_monitoring: false,
        project_value: 3800000,
        profit_margin: 0.12
      }
    ];
    
    setLeads(mockLeads);
  }, []);

  // Fetch agent statistics
  useEffect(() => {
    fetchAgentStats();
  }, []);

  const fetchAgentStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/agent-statistics');
      const data = await response.json();
      setAgentStats(data);
    } catch (error) {
      console.error('Error fetching agent stats:', error);
    }
  };

  const handleFixCompliance = async (lead) => {
    setSelectedLead(lead);
    setDraftingEndorsement(true);
    setEndorsementResult(null);

    try {
      const response = await fetch('http://localhost:8000/api/broker-liaison/draft-endorsement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signal_id: lead.signal_id,
          project_id: lead.project_id,
          project_name: lead.project_name,
          project_address: lead.project_address,
          contractor_name: lead.contractor_name,
          missing_endorsements: lead.missing_endorsements,
          insurance_gaps: lead.insurance_gaps,
          agency_requirements: lead.agency_requirements,
          broker_name: lead.broker_name,
          broker_email: lead.broker_email
        })
      });

      const result = await response.json();
      setEndorsementResult(result);
      fetchAgentStats(); // Refresh stats
    } catch (error) {
      console.error('Error drafting endorsement:', error);
      setEndorsementResult({ status: 'error', detail: error.message });
    } finally {
      setDraftingEndorsement(false);
    }
  };

  const calculateProfitabilityDrain = async (lead) => {
    setSelectedLead(lead);
    setCalculatingRisk(true);
    setRiskResult(null);

    try {
      const response = await fetch('http://localhost:8000/api/predictive-risk/profitability-drain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          signal_id: lead.signal_id,
          project_id: lead.project_id,
          project_value: lead.project_value,
          profit_margin: lead.profit_margin,
          insurance_gaps: lead.insurance_gaps,
          missing_endorsements: lead.missing_endorsements,
          agency_requirements: lead.agency_requirements
        })
      });

      const result = await response.json();
      setRiskResult(result);
      fetchAgentStats(); // Refresh stats
    } catch (error) {
      console.error('Error calculating risk:', error);
      setRiskResult({ status: 'error', detail: error.message });
    } finally {
      setCalculatingRisk(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'CONTESTABLE': '#f59e0b',
      'MONITORING': '#3b82f6',
      'QUALIFIED': '#22c55e',
      'DISQUALIFIED': '#ef4444'
    };
    return colors[status] || '#6b7280';
  };

  const getRecommendationBadge = (recommendation) => {
    const badges = {
      'bid_with_caution': { text: 'Bid with Caution', color: '#eab308' },
      'bid_after_compliance': { text: 'Fix Compliance First', color: '#f59e0b' },
      'do_not_bid': { text: 'Do Not Bid', color: '#ef4444' }
    };
    return badges[recommendation] || { text: recommendation, color: '#6b7280' };
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
    statsBar: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px',
      marginBottom: '24px'
    },
    statCard: {
      backgroundColor: 'white',
      padding: '16px',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0'
    },
    statLabel: {
      fontSize: '12px',
      color: '#64748b',
      marginBottom: '4px',
      fontWeight: '500'
    },
    statValue: {
      fontSize: '24px',
      fontWeight: '700',
      color: '#1e293b'
    },
    statSubtext: {
      fontSize: '11px',
      color: '#22c55e',
      marginTop: '4px'
    },
    leadsGrid: {
      display: 'grid',
      gap: '20px',
      marginBottom: '32px'
    },
    leadCard: {
      backgroundColor: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0'
    },
    leadHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      marginBottom: '16px'
    },
    leadTitle: {
      fontSize: '20px',
      fontWeight: '600',
      color: '#1e293b',
      marginBottom: '4px'
    },
    leadAddress: {
      fontSize: '14px',
      color: '#64748b'
    },
    statusBadge: {
      padding: '6px 12px',
      borderRadius: '6px',
      fontSize: '12px',
      fontWeight: '600',
      color: 'white'
    },
    leadDetails: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '16px',
      marginBottom: '16px'
    },
    detailSection: {
      marginBottom: '12px'
    },
    sectionTitle: {
      fontSize: '12px',
      fontWeight: '600',
      color: '#64748b',
      marginBottom: '8px',
      textTransform: 'uppercase'
    },
    list: {
      paddingLeft: '20px',
      fontSize: '14px',
      color: '#1e293b'
    },
    listItem: {
      marginBottom: '4px'
    },
    actions: {
      display: 'flex',
      gap: '12px',
      marginTop: '16px'
    },
    button: {
      padding: '10px 20px',
      borderRadius: '8px',
      border: 'none',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.2s ease'
    },
    primaryButton: {
      backgroundColor: '#3b82f6',
      color: 'white'
    },
    secondaryButton: {
      backgroundColor: '#f1f5f9',
      color: '#1e293b'
    },
    modal: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    },
    modalContent: {
      backgroundColor: 'white',
      padding: '32px',
      borderRadius: '12px',
      maxWidth: '800px',
      maxHeight: '80vh',
      overflow: 'auto',
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
    },
    modalTitle: {
      fontSize: '24px',
      fontWeight: '700',
      color: '#1e293b',
      marginBottom: '16px'
    },
    resultSection: {
      marginBottom: '20px',
      padding: '16px',
      backgroundColor: '#f8fafc',
      borderRadius: '8px'
    },
    closeButton: {
      marginTop: '24px',
      padding: '10px 20px',
      backgroundColor: '#1e293b',
      color: 'white',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      fontWeight: '600'
    },
    monitorBadge: {
      display: 'inline-block',
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: '600',
      backgroundColor: '#22c55e',
      color: 'white',
      marginLeft: '8px'
    }
  };

  return (
    <div style={styles.dashboard}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🎯 Veteran Dashboard - Action Center</h1>
        <p style={styles.subtitle}>
          2027 ConComply-Scope Suite | Multi-Agent Intelligence System
        </p>
      </div>

      {/* Agent Statistics */}
      {agentStats && (
        <div style={styles.statsBar}>
          <div style={styles.statCard}>
            <div style={styles.statLabel}>BrokerLiaison Requests</div>
            <div style={styles.statValue}>{agentStats.broker_liaison?.requests_drafted || 0}</div>
            <div style={styles.statSubtext}>
              ${(agentStats.broker_liaison?.avg_cost_per_request || 0).toFixed(4)}/request
              {agentStats.broker_liaison?.meets_efficiency_target && ' ✓ Target'}
            </div>
          </div>
          
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Feasibility Assessments</div>
            <div style={styles.statValue}>{agentStats.feasibility_agent?.assessments_completed || 0}</div>
            <div style={styles.statSubtext}>
              ${(agentStats.feasibility_agent?.avg_cost_per_assessment || 0).toFixed(4)}/assessment
              {agentStats.feasibility_agent?.meets_efficiency_target && ' ✓ Target'}
            </div>
          </div>
          
          <div style={styles.statCard}>
            <div style={styles.statLabel}>Cost Efficiency</div>
            <div style={styles.statValue}>$0.007</div>
            <div style={styles.statSubtext}>Target per document</div>
          </div>

          <div style={styles.statCard}>
            <div style={styles.statLabel}>Active Leads</div>
            <div style={styles.statValue}>{leads.filter(l => l.status === 'CONTESTABLE').length}</div>
            <div style={styles.statSubtext}>Contestable opportunities</div>
          </div>
        </div>
      )}

      {/* ScopeSignal Leads */}
      <div style={styles.leadsGrid}>
        {leads.map(lead => (
          <div key={lead.signal_id} style={styles.leadCard}>
            <div style={styles.leadHeader}>
              <div>
                <div style={styles.leadTitle}>
                  {lead.project_name}
                  {lead.has_active_monitoring && (
                    <span style={styles.monitorBadge}>🔭 MONITORING</span>
                  )}
                </div>
                <div style={styles.leadAddress}>
                  {lead.project_address} • {lead.contractor_name}
                </div>
              </div>
              <span style={{...styles.statusBadge, backgroundColor: getStatusColor(lead.status)}}>
                {lead.status}
              </span>
            </div>

            <div style={styles.leadDetails}>
              <div>
                <div style={styles.detailSection}>
                  <div style={styles.sectionTitle}>Missing Endorsements ({lead.missing_endorsements.length})</div>
                  <ul style={styles.list}>
                    {lead.missing_endorsements.map((e, i) => (
                      <li key={i} style={styles.listItem}>{e}</li>
                    ))}
                  </ul>
                </div>

                <div style={styles.detailSection}>
                  <div style={styles.sectionTitle}>Insurance Gaps ({lead.insurance_gaps.length})</div>
                  <ul style={styles.list}>
                    {lead.insurance_gaps.length > 0 ? (
                      lead.insurance_gaps.map((g, i) => (
                        <li key={i} style={styles.listItem}>{g}</li>
                      ))
                    ) : (
                      <li style={styles.listItem}>None detected</li>
                    )}
                  </ul>
                </div>
              </div>

              <div>
                <div style={styles.detailSection}>
                  <div style={styles.sectionTitle}>Agency Requirements</div>
                  <ul style={styles.list}>
                    {lead.agency_requirements.map((a, i) => (
                      <li key={i} style={styles.listItem}>{a}</li>
                    ))}
                  </ul>
                </div>

                <div style={styles.detailSection}>
                  <div style={styles.sectionTitle}>Broker Contact</div>
                  <div style={{fontSize: '14px', color: '#1e293b'}}>
                    {lead.broker_name}
                    <br />
                    {lead.broker_email}
                  </div>
                </div>
              </div>
            </div>

            <div style={styles.detailSection}>
              <div style={styles.sectionTitle}>Project Financials</div>
              <div style={{fontSize: '14px', color: '#1e293b'}}>
                Value: ${(lead.project_value).toLocaleString()} | 
                Profit Margin: {(lead.profit_margin * 100).toFixed(0)}%
              </div>
            </div>

            <div style={styles.actions}>
              <button
                style={{...styles.button, ...styles.primaryButton}}
                onClick={() => handleFixCompliance(lead)}
                disabled={draftingEndorsement}
              >
                {draftingEndorsement && selectedLead?.signal_id === lead.signal_id 
                  ? '⏳ Drafting...' 
                  : '📧 Fix Compliance'}
              </button>
              
              <button
                style={{...styles.button, ...styles.secondaryButton}}
                onClick={() => calculateProfitabilityDrain(lead)}
                disabled={calculatingRisk}
              >
                {calculatingRisk && selectedLead?.signal_id === lead.signal_id 
                  ? '⏳ Calculating...' 
                  : '📊 Calculate Risk'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Endorsement Result Modal */}
      {endorsementResult && (
        <div style={styles.modal} onClick={() => setEndorsementResult(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalTitle}>
              ✅ Endorsement Request Drafted
            </div>

            {endorsementResult.status === 'success' ? (
              <>
                <div style={styles.resultSection}>
                  <strong>Request ID:</strong> {endorsementResult.request_id}
                  <br />
                  <strong>Urgency:</strong> {endorsementResult.urgency.toUpperCase()}
                  <br />
                  <strong>Endorsements:</strong> {endorsementResult.required_endorsements.length}
                </div>

                <div style={styles.resultSection}>
                  <strong>Subject:</strong>
                  <div>{endorsementResult.subject}</div>
                </div>

                <div style={styles.resultSection}>
                  <strong>Email Body:</strong>
                  <pre style={{whiteSpace: 'pre-wrap', fontSize: '12px'}}>
                    {endorsementResult.body}
                  </pre>
                </div>

                {endorsementResult.decision_proof && (
                  <div style={styles.resultSection}>
                    <strong>🔍 Agent Handshake (Task 3 - Governance Audit):</strong>
                    <br />
                    From: {endorsementResult.decision_proof.agent_handshake?.from_agent || 'N/A'}
                    <br />
                    To: {endorsementResult.decision_proof.agent_handshake?.to_agent || 'N/A'}
                    <br />
                    Status: {endorsementResult.decision_proof.agent_handshake?.validation_status || 'N/A'}
                    <br />
                    Confidence: {(endorsementResult.decision_proof.confidence * 100).toFixed(1)}%
                  </div>
                )}

                <div style={styles.resultSection}>
                  <strong>📊 Cost Efficiency:</strong>
                  <br />
                  Cost: ${endorsementResult.statistics.avg_cost_per_request.toFixed(4)}
                  <br />
                  Target: ${endorsementResult.statistics.target_cost}
                  <br />
                  Status: {endorsementResult.statistics.meets_efficiency_target ? '✅ MEETS TARGET' : '⚠️ ABOVE TARGET'}
                </div>
              </>
            ) : (
              <div style={{color: '#ef4444'}}>
                Error: {endorsementResult.detail}
              </div>
            )}

            <button style={styles.closeButton} onClick={() => setEndorsementResult(null)}>
              Close
            </button>
          </div>
        </div>
      )}

      {/* Risk Result Modal */}
      {riskResult && (
        <div style={styles.modal} onClick={() => setRiskResult(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalTitle}>
              📊 Profitability Drain Analysis
            </div>

            {riskResult.status === 'success' ? (
              <>
                <div style={styles.resultSection}>
                  <strong>Feasibility Score:</strong> {riskResult.feasibility_score.toFixed(1)}/100
                  <br />
                  <strong>Confidence:</strong> {(riskResult.confidence * 100).toFixed(1)}%
                  <br />
                  <strong>Recommendation:</strong>{' '}
                  <span style={{
                    ...styles.statusBadge,
                    backgroundColor: getRecommendationBadge(riskResult.recommendation).color
                  }}>
                    {getRecommendationBadge(riskResult.recommendation).text}
                  </span>
                </div>

                <div style={styles.resultSection}>
                  <strong>💰 Financial Impact (Task 4 - Profitability Drain):</strong>
                  <br />
                  Projected Premium Increase: ${riskResult.projected_premium_increase.toLocaleString()}
                  <br />
                  Profitability Drain: {riskResult.profitability_drain_percent.toFixed(1)}% of profit margin
                  <br />
                  Recommended Bid Adjustment: +${riskResult.estimated_bid_adjustment.toLocaleString()}
                </div>

                <div style={styles.resultSection}>
                  <strong>🎯 Risk Factors (Skeptical Veteran Logic):</strong>
                  <ul style={styles.list}>
                    {Object.entries(riskResult.risk_factors).map(([key, value]) => (
                      <li key={key} style={styles.listItem}>
                        {key.replace(/_/g, ' ')}: {typeof value === 'number' ? value.toFixed(2) : value}
                      </li>
                    ))}
                  </ul>
                </div>

                <div style={styles.resultSection}>
                  <strong>💡 Reasoning Chain:</strong>
                  <ol style={{paddingLeft: '20px', fontSize: '14px'}}>
                    {riskResult.reasoning.map((r, i) => (
                      <li key={i} style={styles.listItem}>{r}</li>
                    ))}
                  </ol>
                </div>

                <div style={styles.resultSection}>
                  <strong>📊 Cost Efficiency:</strong>
                  <br />
                  Tokens: {riskResult.cost_efficiency.tokens_used}
                  <br />
                  Cost: ${riskResult.cost_efficiency.cost_usd.toFixed(4)}
                  <br />
                  Status: {riskResult.cost_efficiency.meets_target ? '✅ MEETS $0.007 TARGET' : '⚠️ ABOVE TARGET'}
                </div>
              </>
            ) : (
              <div style={{color: '#ef4444'}}>
                Error: {riskResult.detail}
              </div>
            )}

            <button style={styles.closeButton} onClick={() => setRiskResult(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default VeteranDashboard;
