import React, { useState } from 'react';
import SuccessionShieldEnterprise from './components/SuccessionShieldEnterprise';
import DocumentUploadStation from './components/DocumentUploadStation';
import ContractorDocVerifier from './components/ContractorDocVerifier';
import SentinelLiveFeed from './components/SentinelLiveFeed';
import VeteranDashboard from './components/VeteranDashboard';

/**
 * Main Application Component - Unified Compliance Command Center
 * 
 * ConComplyAi - AI-driven platform for verifying contractor documentation
 * Integrated with Sentinel-Scope for real-time monitoring
 * 
 * Features:
 * - Site compliance dashboard (violation detection) - "Validator Station"
 * - Veteran Dashboard - Action Center (2027 enhancements)
 * - Sentinel Live Feed - Real-time monitoring
 * - Document upload and processing
 * - Document verification with comparison view
 */
function App() {
  const [activeView, setActiveView] = useState('veteran');
  const [processedDocument, setProcessedDocument] = useState(null);

  const handleDocumentProcessed = (doc) => {
    setProcessedDocument(doc);
    setActiveView('verification');
  };

  return (
    <div className="App">
      {/* Navigation */}
      <nav style={styles.navigation}>
        <div style={styles.navBrand}>
          🏗️ ConComplyAi - Compliance Command Center
        </div>
        <div style={styles.navLinks}>
          <button 
            style={activeView === 'veteran' ? styles.navButtonActive : styles.navButton}
            onClick={() => setActiveView('veteran')}
          >
            🎯 Veteran Dashboard
          </button>
          <button 
            style={activeView === 'dashboard' ? styles.navButtonActive : styles.navButton}
            onClick={() => setActiveView('dashboard')}
          >
            ✓ Validator Station
          </button>
          <button 
            style={activeView === 'sentinel' ? styles.navButtonActive : styles.navButton}
            onClick={() => setActiveView('sentinel')}
          >
            🔭 Sentinel Live Feed
          </button>
          <button 
            style={activeView === 'upload' ? styles.navButtonActive : styles.navButton}
            onClick={() => setActiveView('upload')}
          >
            ⬆️ Upload Documents
          </button>
          {processedDocument && (
            <button 
              style={activeView === 'verification' ? styles.navButtonActive : styles.navButton}
              onClick={() => setActiveView('verification')}
            >
              🔍 Document Verification
            </button>
          )}
        </div>
      </nav>

      {/* Content */}
      <div style={styles.content}>
        {activeView === 'veteran' && (
          <VeteranDashboard />
        )}

        {activeView === 'dashboard' && (
          <SuccessionShieldEnterprise />
        )}

        {activeView === 'sentinel' && (
          <SentinelLiveFeed />
        )}

        {activeView === 'upload' && (
          <DocumentUploadStation onDocumentProcessed={handleDocumentProcessed} />
        )}

        {activeView === 'verification' && processedDocument && (
          <ContractorDocVerifier verificationPayload={processedDocument} />
        )}
      </div>
    </div>
  );
}

const styles = {
  navigation: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 32px',
    backgroundColor: '#1f2937',
    borderBottom: '3px solid #3b82f6'
  },
  navBrand: {
    fontSize: '24px',
    fontWeight: '700',
    color: 'white'
  },
  navLinks: {
    display: 'flex',
    gap: '12px'
  },
  navButton: {
    backgroundColor: 'transparent',
    color: '#d1d5db',
    border: 'none',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    borderRadius: '6px',
    transition: 'all 0.2s ease'
  },
  navButtonActive: {
    backgroundColor: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    borderRadius: '6px'
  },
  content: {
    minHeight: 'calc(100vh - 70px)'
  }
};

export default App;
