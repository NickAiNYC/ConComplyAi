# ConComplyAi Dashboard - Integration Guide

## Overview

The ConComplyAi dashboard is a React-based web interface for monitoring construction compliance metrics. It provides a clean, professional design ready to be populated with real-time data from your API.

## Installation

```bash
# Install Node.js dependencies
npm install
```

This will install:
- React 18.2.0
- Recharts 2.10.3 (charting library)
- react-scripts 5.0.1 (build tools)

## Running the Dashboard

### Development Mode
```bash
npm start
```
Opens the dashboard at `http://localhost:3000` with hot-reloading enabled.

### Production Build
```bash
npm run build
```
Creates an optimized production build in the `build/` directory.

### Serving Production Build
```bash
npm install -g serve
serve -s build
```

## Dashboard Components

### SuccessionShieldEnterprise.jsx
Located at: `src/components/SuccessionShieldEnterprise.jsx`

This is the main dashboard component with the following sections:

1. **Header**: Title and filters (time range, site selection)
2. **Key Metrics Grid**: 6 metric cards showing:
   - Total Sites Monitored
   - Active Violations
   - Compliance Score
   - Cost Savings
   - Avg Processing Time
   - AI Accuracy

3. **Charts**:
   - Compliance Trends Over Time (Area Chart)
   - Violation Trends by Type (Line Chart)
   - Risk Distribution (Pie Chart)
   - Critical Violations (Bar Chart)
   - Multi-Agent Performance (Bar Chart)

## Integration with Your API

The dashboard accepts the following props:

```javascript
<SuccessionShieldEnterprise
  complianceData={[
    { month: 'Jan', compliant: 85, nonCompliant: 15, criticalViolations: 3 },
    // ... more data
  ]}
  violationTrends={[
    { date: '2024-01', scaffolding: 12, ppe: 8, electrical: 5, fallProtection: 7 },
    // ... more data
  ]}
  riskDistribution={[
    { name: 'Low Risk', value: 65, color: '#22c55e' },
    { name: 'Medium Risk', value: 25, color: '#eab308' },
    { name: 'High Risk', value: 8, color: '#f97316' },
    { name: 'Critical', value: 2, color: '#ef4444' }
  ]}
  metrics={{
    totalSites: 1247,
    activeViolations: 23,
    avgComplianceScore: 94,
    costSavings: 1490000,
    processingTime: 2.3,
    aiAccuracy: 92
  }}
/>
```

### Example API Integration

```javascript
import React, { useState, useEffect } from 'react';
import SuccessionShieldEnterprise from './components/SuccessionShieldEnterprise';

function App() {
  const [dashboardData, setDashboardData] = useState({
    complianceData: [],
    violationTrends: [],
    riskDistribution: [],
    metrics: {}
  });

  useEffect(() => {
    // Fetch data from your ConComplyAI API
    fetch('/api/dashboard-data')
      .then(res => res.json())
      .then(data => setDashboardData(data))
      .catch(err => console.error('Error fetching dashboard data:', err));
  }, []);

  return (
    <div className="App">
      <SuccessionShieldEnterprise
        complianceData={dashboardData.complianceData}
        violationTrends={dashboardData.violationTrends}
        riskDistribution={dashboardData.riskDistribution}
        metrics={dashboardData.metrics}
      />
    </div>
  );
}

export default App;
```

## API Endpoint Requirements

To populate the dashboard, your backend should provide an endpoint that returns data in this format:

```json
{
  "complianceData": [
    {
      "month": "Jan",
      "compliant": 85,
      "nonCompliant": 15,
      "criticalViolations": 3
    }
  ],
  "violationTrends": [
    {
      "date": "2024-01",
      "scaffolding": 12,
      "ppe": 8,
      "electrical": 5,
      "fallProtection": 7
    }
  ],
  "riskDistribution": [
    {
      "name": "Low Risk",
      "value": 65,
      "color": "#22c55e"
    }
  ],
  "metrics": {
    "totalSites": 1247,
    "activeViolations": 23,
    "avgComplianceScore": 94,
    "costSavings": 1490000,
    "processingTime": 2.3,
    "aiAccuracy": 92
  }
}
```

## Customization

### Styling
All styles are inline in the component for easy customization. Key style objects:
- `styles.dashboard`: Main container
- `styles.metricCard`: Metric card styling
- `styles.chartCard`: Chart container styling

### Colors
Default color palette:
- Green: `#22c55e` (Low Risk, Success)
- Yellow: `#eab308` (Medium Risk, Warning)
- Orange: `#f97316` (High Risk, Alert)
- Red: `#ef4444` (Critical, Danger)

## File Structure

```
ConComplyAi/
├── package.json              # Node.js dependencies
├── public/
│   └── index.html           # HTML entry point
├── src/
│   ├── index.js             # React entry point
│   ├── index.css            # Global styles
│   ├── App.js               # Main app component
│   └── components/
│       └── SuccessionShieldEnterprise.jsx  # Dashboard component
└── build/                   # Production build (generated)
```

## Browser Support

The dashboard supports all modern browsers:
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Production build size: ~155 KB (gzipped)
- CSS size: ~298 B (gzipped)
- Responsive design works on all screen sizes

## Troubleshooting

### Port Already in Use
If port 3000 is already in use:
```bash
PORT=3001 npm start
```

### Build Errors
Clear cache and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

### Recharts Not Working
Ensure Recharts is properly installed:
```bash
npm install recharts --save
```

## Next Steps

1. Connect the dashboard to your ConComplyAI Python backend API
2. Implement authentication if needed
3. Add real-time updates using WebSockets or polling
4. Customize the color scheme to match your brand
5. Add more charts and metrics as needed

## Support

For issues or questions about the dashboard integration, refer to:
- [Recharts Documentation](https://recharts.org/)
- [React Documentation](https://react.dev/)
- [Create React App Documentation](https://create-react-app.dev/)
