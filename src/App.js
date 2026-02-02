import React from 'react';
import SuccessionShieldEnterprise from './components/SuccessionShieldEnterprise';

/**
 * Main Application Component
 * 
 * This demonstrates how to use the ConComplyAi dashboard
 * in your React application.
 */
function App() {
  // TODO: Replace with actual API calls to your ConComplyAI backend
  // Example API integration:
  // 
  // useEffect(() => {
  //   fetch('/api/compliance-data')
  //     .then(res => res.json())
  //     .then(data => setComplianceData(data));
  // }, []);

  return (
    <div className="App">
      {/* 
        Basic Usage (design only, no data):
      */}
      <SuccessionShieldEnterprise />

      {/* 
        Advanced Usage (with your custom data from API):
        <SuccessionShieldEnterprise
          complianceData={yourComplianceData}
          metrics={yourMetrics}
          violationTrends={yourViolationTrends}
          riskDistribution={yourRiskDistribution}
        />
      */}
    </div>
  );
}

export default App;
