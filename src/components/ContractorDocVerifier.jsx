import React, { useReducer, useCallback } from 'react';

/**
 * ContractorDocVerifier - Audit Trail Component for Construction Documents
 * 
 * COMPLIANCE FIRST: Every extraction must be auditable
 * Shows confidence scores and source coordinates for each field
 */

const interactionReducer = (state, action) => {
  switch (action.type) {
    case 'HIGHLIGHT_EXTRACTION':
      return { ...state, activeExtraction: action.payload, piiVisible: state.piiVisible };
    case 'TOGGLE_REDACTION':
      return { ...state, activeExtraction: state.activeExtraction, piiVisible: !state.piiVisible };
    case 'CLEAR_HIGHLIGHT':
      return { ...state, activeExtraction: null, piiVisible: state.piiVisible };
    default:
      return state;
  }
};

const ContractorDocVerifier = ({ verificationPayload = null }) => {
  const [interaction, dispatch] = useReducer(interactionReducer, {
    activeExtraction: null,
    piiVisible: false
  });

  // Mock payload for demonstration
  const defaultPayload = {
    doc_identifier: 'COI-HUDSON-001',
    doc_category: 'COI',
    quality_metric: 0.85,
    skew_detected: false,
    crumple_detected: false,
    field_extractions: [
      {
        label: 'contractor_name',
        extracted_value: 'ABC Construction LLC',
        certainty: 0.95,
        bbox: { pg: 1, left: 0.1, top: 0.15, w: 0.3, h: 0.02 },
        method: 'OCR',
        contains_pii: false
      },
      {
        label: 'policy_number',
        extracted_value: 'GL-2024-789456',
        certainty: 0.92,
        bbox: { pg: 1, left: 0.5, top: 0.3, w: 0.25, h: 0.02 },
        method: 'OCR',
        contains_pii: false
      },
      {
        label: 'expiration_date',
        extracted_value: '2025-01-01',
        certainty: 0.91,
        bbox: { pg: 1, left: 0.3, top: 0.35, w: 0.15, h: 0.02 },
        method: 'OCR',
        contains_pii: false,
        exp_classification: 'VALID'
      },
      {
        label: 'gl_coverage_limit',
        extracted_value: '$2,000,000',
        certainty: 0.88,
        bbox: { pg: 1, left: 0.6, top: 0.4, w: 0.15, h: 0.02 },
        method: 'OCR',
        contains_pii: false
      },
      {
        label: 'additional_insured_check',
        extracted_value: 'YES',
        certainty: 0.94,
        bbox: { pg: 1, left: 0.1, top: 0.6, w: 0.1, h: 0.02 },
        method: 'LLM',
        contains_pii: false
      },
      {
        label: 'subrogation_waiver_check',
        extracted_value: 'YES',
        certainty: 0.93,
        bbox: { pg: 1, left: 0.1, top: 0.62, w: 0.1, h: 0.02 },
        method: 'LLM',
        contains_pii: false
      }
    ],
    sensitive_data_masked: [],
    compliance_status: true,
    compliance_issues: [],
    processing_cost_usd: 0.0052
  };

  const payload = verificationPayload || defaultPayload;

  const certaintyStyling = useCallback((certainty) => {
    if (certainty >= 0.9) return { bg: '#dcfce7', text: '#166534', label: 'High' };
    if (certainty >= 0.8) return { bg: '#fef3c7', text: '#92400e', label: 'Med' };
    return { bg: '#fee2e2', text: '#991b1b', label: 'Low' };
  }, []);

  const expirationBadgeStyle = useCallback((classification) => {
    const configs = {
      'VALID': { bg: '#10b981', txt: 'Valid' },
      'EXPIRING_SOON': { bg: '#f59e0b', txt: 'Expires <30d' },
      'EXPIRED': { bg: '#ef4444', txt: 'Expired' },
      'NO_EXPIRATION': { bg: '#6b7280', txt: 'N/A' }
    };
    return configs[classification] || configs['NO_EXPIRATION'];
  }, []);

  const humanizeLabel = (machineLabel) => {
    return machineLabel.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  const selectExtraction = useCallback((extraction) => {
    dispatch({ type: 'HIGHLIGHT_EXTRACTION', payload: extraction });
  }, []);

  const togglePII = useCallback(() => {
    dispatch({ type: 'TOGGLE_REDACTION' });
  }, []);

  return (
    <div style={styles.verifierContainer}>
      <div style={styles.headerSection}>
        <h2 style={styles.mainTitle}>Contractor Document Audit: {payload.doc_category}</h2>
        <div style={styles.metadataBar}>
          <span style={styles.metaItem}>ID: {payload.doc_identifier}</span>
          <span style={styles.metaItem}>
            Quality: 
            <strong style={{ 
              color: payload.quality_metric >= 0.8 ? '#10b981' : '#f59e0b',
              marginLeft: '5px'
            }}>
              {(payload.quality_metric * 100).toFixed(0)}%
            </strong>
          </span>
          <span style={styles.metaItem}>Cost: ${payload.processing_cost_usd.toFixed(4)}</span>
        </div>
      </div>

      {(payload.skew_detected || payload.crumple_detected) && (
        <div style={styles.alertBox}>
          ⚠️ Quality Alert: 
          {payload.skew_detected && ' Document skew detected.'}
          {payload.crumple_detected && ' Physical damage detected.'}
          {' Recommend manual verification.'}
        </div>
      )}

      <div style={styles.splitLayout}>
        {/* Source Document Panel */}
        <div style={styles.sourcePanel}>
          <div style={styles.panelHeader}>
            <h3 style={styles.panelTitle}>Source Document</h3>
            <button style={styles.piiToggle} onClick={togglePII}>
              {interaction.piiVisible ? '🔒 Mask PII' : '👁️ Reveal PII'}
            </button>
          </div>
          <div style={styles.docViewport}>
            <div style={styles.docPlaceholder}>
              <p style={styles.placeholderText}>📄 {payload.doc_category} Document</p>
              <p style={styles.placeholderSubtext}>Source imagery displays here</p>
              
              {interaction.activeExtraction && interaction.activeExtraction.bbox && (
                <div 
                  style={{
                    ...styles.boundingRect,
                    left: `${interaction.activeExtraction.bbox.left * 100}%`,
                    top: `${interaction.activeExtraction.bbox.top * 100}%`,
                    width: `${interaction.activeExtraction.bbox.w * 100}%`,
                    height: `${interaction.activeExtraction.bbox.h * 100}%`
                  }}
                />
              )}
            </div>
          </div>
        </div>

        {/* Extraction Results Panel */}
        <div style={styles.resultsPanel}>
          <div style={styles.panelHeader}>
            <h3 style={styles.panelTitle}>Extracted Intelligence</h3>
            <div style={styles.statusIndicator}>
              {payload.compliance_status ? (
                <span style={styles.statusPass}>✓ Compliant</span>
              ) : (
                <span style={styles.statusFail}>✗ Non-Compliant</span>
              )}
            </div>
          </div>

          {payload.compliance_issues && payload.compliance_issues.length > 0 && (
            <div style={styles.issuesBlock}>
              <h4 style={styles.issuesTitle}>⚠️ Compliance Issues:</h4>
              <ul style={styles.issuesList}>
                {payload.compliance_issues.map((issue, idx) => (
                  <li key={idx} style={issue.includes('CRITICAL') ? styles.criticalIssue : styles.warningIssue}>
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div style={styles.extractionsList}>
            {payload.field_extractions.map((extraction, idx) => {
              const certStyle = certaintyStyling(extraction.certainty);
              const isActive = interaction.activeExtraction === extraction;
              
              return (
                <div 
                  key={idx}
                  style={{
                    ...styles.extractionCard,
                    ...(isActive ? styles.extractionCardActive : {})
                  }}
                  onClick={() => selectExtraction(extraction)}
                >
                  <div style={styles.extractionHeader}>
                    <span style={styles.extractionLabel}>{humanizeLabel(extraction.label)}</span>
                    <div style={styles.badgeCluster}>
                      {extraction.contains_pii && (
                        <span style={styles.piiBadge}>🔒 PII</span>
                      )}
                      {extraction.exp_classification && (
                        <span style={{
                          ...styles.expBadge,
                          backgroundColor: expirationBadgeStyle(extraction.exp_classification).bg
                        }}>
                          {expirationBadgeStyle(extraction.exp_classification).txt}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div style={styles.extractionValue}>
                    {interaction.piiVisible || !extraction.contains_pii ? extraction.extracted_value : '***REDACTED***'}
                  </div>
                  
                  <div style={styles.extractionMeta}>
                    <span style={{
                      ...styles.certBadge,
                      backgroundColor: certStyle.bg,
                      color: certStyle.text
                    }}>
                      {certStyle.label} {(extraction.certainty * 100).toFixed(0)}%
                    </span>
                    <span style={styles.methodBadge}>
                      {extraction.method}
                    </span>
                    {extraction.bbox && (
                      <span style={styles.locationBadge}>
                        📍 Pg {extraction.bbox.pg}
                      </span>
                    )}
                  </div>

                  {isActive && (
                    <div style={styles.extractionHint}>
                      <p style={styles.hintText}>
                        Source location highlighted above
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {payload.sensitive_data_masked && payload.sensitive_data_masked.length > 0 && (
            <div style={styles.privacyBlock}>
              <h4 style={styles.privacyTitle}>🔒 Privacy Safeguards</h4>
              <p style={styles.privacyText}>{payload.sensitive_data_masked.length} sensitive field(s) identified</p>
              <ul style={styles.privacyList}>
                {payload.sensitive_data_masked.map((mask, idx) => (
                  <li key={idx} style={styles.privacyItem}>
                    {mask.field_name}: {mask.pii_type}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {payload.doc_category === 'COI' && (
        <div style={styles.insuranceChecklist}>
          <h3 style={styles.checklistTitle}>Insurance Mandate Verification</h3>
          <div style={styles.checklistGrid}>
            {payload.field_extractions.map(ext => {
              if (ext.label === 'additional_insured_check') {
                return (
                  <div key="ai" style={ext.extracted_value === 'YES' ? styles.checkPassed : styles.checkFailed}>
                    {ext.extracted_value === 'YES' ? '✓' : '✗'} Additional Insured
                  </div>
                );
              }
              if (ext.label === 'subrogation_waiver_check') {
                return (
                  <div key="sw" style={ext.extracted_value === 'YES' ? styles.checkPassed : styles.checkFailed}>
                    {ext.extracted_value === 'YES' ? '✓' : '✗'} Subrogation Waiver
                  </div>
                );
              }
              if (ext.label === 'per_project_aggregate_check') {
                return (
                  <div key="ppa" style={ext.extracted_value === 'YES' ? styles.checkPassed : styles.checkFailed}>
                    {ext.extracted_value === 'YES' ? '✓' : '✗'} Per Project Aggregate
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      )}

      <div style={styles.actionBar}>
        <button style={{...styles.actionBtn, ...styles.btnApprove}} disabled={!payload.compliance_status}>
          ✓ Approve
        </button>
        <button style={{...styles.actionBtn, ...styles.btnReject}}>
          ✗ Reject
        </button>
        <button style={{...styles.actionBtn, ...styles.btnManual}}>
          📝 Manual Review
        </button>
      </div>
    </div>
  );
};

const styles = {
  verifierContainer: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '20px',
    backgroundColor: '#f9fafb'
  },
  headerSection: {
    marginBottom: '20px'
  },
  mainTitle: {
    fontSize: '24px',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '10px'
  },
  metadataBar: {
    display: 'flex',
    gap: '20px',
    fontSize: '14px',
    color: '#6b7280'
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center'
  },
  alertBox: {
    backgroundColor: '#fef3c7',
    border: '1px solid #f59e0b',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '20px',
    color: '#92400e',
    fontSize: '14px'
  },
  splitLayout: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '20px',
    marginBottom: '20px'
  },
  sourcePanel: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  },
  resultsPanel: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    maxHeight: '800px',
    overflowY: 'auto'
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '15px'
  },
  panelTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827'
  },
  piiToggle: {
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '13px',
    cursor: 'pointer'
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center'
  },
  statusPass: {
    backgroundColor: '#dcfce7',
    color: '#166534',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600'
  },
  statusFail: {
    backgroundColor: '#fee2e2',
    color: '#991b1b',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600'
  },
  docViewport: {
    border: '2px dashed #d1d5db',
    borderRadius: '8px',
    minHeight: '600px',
    position: 'relative',
    backgroundColor: '#f9fafb'
  },
  docPlaceholder: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '600px',
    position: 'relative'
  },
  placeholderText: {
    fontSize: '20px',
    color: '#6b7280',
    margin: '10px 0'
  },
  placeholderSubtext: {
    fontSize: '14px',
    color: '#9ca3af'
  },
  boundingRect: {
    position: 'absolute',
    border: '2px solid #3b82f6',
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    pointerEvents: 'none',
    transition: 'all 0.2s ease'
  },
  issuesBlock: {
    backgroundColor: '#fef3c7',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '15px'
  },
  issuesTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#92400e',
    marginBottom: '8px'
  },
  issuesList: {
    margin: '0',
    paddingLeft: '20px'
  },
  criticalIssue: {
    color: '#991b1b',
    fontWeight: '600',
    marginBottom: '5px'
  },
  warningIssue: {
    color: '#92400e',
    marginBottom: '5px'
  },
  extractionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  extractionCard: {
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '12px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    backgroundColor: 'white'
  },
  extractionCardActive: {
    border: '2px solid #3b82f6',
    backgroundColor: '#eff6ff'
  },
  extractionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px'
  },
  extractionLabel: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151'
  },
  badgeCluster: {
    display: 'flex',
    gap: '6px'
  },
  piiBadge: {
    backgroundColor: '#fef3c7',
    color: '#92400e',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600'
  },
  expBadge: {
    color: 'white',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600'
  },
  extractionValue: {
    fontSize: '16px',
    color: '#111827',
    marginBottom: '8px',
    fontWeight: '500'
  },
  extractionMeta: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap'
  },
  certBadge: {
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600'
  },
  methodBadge: {
    backgroundColor: '#e5e7eb',
    color: '#374151',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px'
  },
  locationBadge: {
    backgroundColor: '#dbeafe',
    color: '#1e40af',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px'
  },
  extractionHint: {
    marginTop: '8px',
    padding: '8px',
    backgroundColor: '#eff6ff',
    borderRadius: '4px'
  },
  hintText: {
    margin: '0',
    fontSize: '12px',
    color: '#1e40af',
    fontStyle: 'italic'
  },
  privacyBlock: {
    marginTop: '15px',
    padding: '12px',
    backgroundColor: '#f3f4f6',
    borderRadius: '8px'
  },
  privacyTitle: {
    fontSize: '15px',
    fontWeight: '600',
    color: '#374151',
    marginBottom: '8px'
  },
  privacyText: {
    fontSize: '13px',
    color: '#6b7280',
    marginBottom: '8px'
  },
  privacyList: {
    margin: '0',
    paddingLeft: '20px',
    fontSize: '13px',
    color: '#374151'
  },
  privacyItem: {
    marginBottom: '4px'
  },
  insuranceChecklist: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '20px',
    marginBottom: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
  },
  checklistTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827',
    marginBottom: '12px'
  },
  checklistGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '10px'
  },
  checkPassed: {
    backgroundColor: '#dcfce7',
    color: '#166534',
    padding: '10px',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px'
  },
  checkFailed: {
    backgroundColor: '#fee2e2',
    color: '#991b1b',
    padding: '10px',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px'
  },
  actionBar: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end'
  },
  actionBtn: {
    padding: '10px 20px',
    borderRadius: '6px',
    border: 'none',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'opacity 0.2s ease'
  },
  btnApprove: {
    backgroundColor: '#10b981',
    color: 'white'
  },
  btnReject: {
    backgroundColor: '#ef4444',
    color: 'white'
  },
  btnManual: {
    backgroundColor: '#6b7280',
    color: 'white'
  }
};

export default ContractorDocVerifier;
