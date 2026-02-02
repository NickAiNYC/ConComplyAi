import React, { useState } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

/**
 * ConComplyAi Dashboard
 * 
 * A comprehensive dashboard for construction compliance monitoring with:
 * - Site compliance overview
 * - Violation trends over time
 * - Risk distribution analysis
 * - Agent performance metrics
 * - Cost savings visualization
 * 
 * @param {Object} props - Component props
 * @param {Array} props.complianceData - Array of compliance data points
 * @param {Array} props.violationTrends - Array of violation trend data
 * @param {Array} props.riskDistribution - Array of risk distribution data
 * @param {Object} props.metrics - Overall metrics object
 */
const SuccessionShieldEnterprise = ({
  complianceData = [],
  violationTrends = [],
  riskDistribution = [],
  metrics = {}
}) => {
  // State for active filters
  const [timeRange, setTimeRange] = useState('30d');
  const [selectedSite, setSelectedSite] = useState('all');

  // Empty data - design only
  const defaultComplianceData = complianceData.length > 0 ? complianceData : [];
  const defaultViolationTrends = violationTrends.length > 0 ? violationTrends : [];
  const defaultRiskDistribution = riskDistribution.length > 0 ? riskDistribution : [];

  const styles = {
    dashboard: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
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
      marginBottom: '24px'
    },
    filters: {
      display: 'flex',
      gap: '16px',
      marginBottom: '24px'
    },
    select: {
      padding: '8px 16px',
      borderRadius: '8px',
      border: '1px solid #e2e8f0',
      backgroundColor: 'white',
      fontSize: '14px',
      cursor: 'pointer'
    },
    metricsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '20px',
      marginBottom: '32px'
    },
    metricCard: {
      backgroundColor: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0'
    },
    metricLabel: {
      fontSize: '14px',
      color: '#64748b',
      marginBottom: '8px',
      fontWeight: '500'
    },
    metricValue: {
      fontSize: '32px',
      fontWeight: '700',
      color: '#1e293b',
      marginBottom: '4px'
    },
    metricChange: {
      fontSize: '12px',
      color: '#22c55e',
      fontWeight: '500'
    },
    chartsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
      gap: '20px',
      marginBottom: '32px'
    },
    chartCard: {
      backgroundColor: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0'
    },
    chartTitle: {
      fontSize: '18px',
      fontWeight: '600',
      color: '#1e293b',
      marginBottom: '20px'
    },
    fullWidthChart: {
      backgroundColor: 'white',
      padding: '24px',
      borderRadius: '12px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0',
      marginBottom: '32px'
    },
    footer: {
      marginTop: '32px',
      padding: '16px',
      textAlign: 'center',
      color: '#64748b',
      fontSize: '14px'
    }
  };

  return (
    <div style={styles.dashboard}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.title}>🏗️ ConComplyAi</h1>
        <p style={styles.subtitle}>
          AI-Powered Construction Compliance Monitoring & Risk Management
        </p>

        {/* Filters */}
        <div style={styles.filters}>
          <select 
            style={styles.select} 
            value={timeRange} 
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
          </select>
          
          <select 
            style={styles.select}
            value={selectedSite}
            onChange={(e) => setSelectedSite(e.target.value)}
          >
            <option value="all">All Sites</option>
            <option value="hudson-yards">Hudson Yards</option>
            <option value="downtown">Downtown Project</option>
            <option value="waterfront">Waterfront Development</option>
          </select>
        </div>
      </div>

      {/* Key Metrics */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Total Sites Monitored</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Active Violations</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Compliance Score</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Cost Savings</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>Avg Processing Time</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>

        <div style={styles.metricCard}>
          <div style={styles.metricLabel}>AI Accuracy</div>
          <div style={styles.metricValue}>-</div>
          <div style={styles.metricChange}></div>
        </div>
      </div>

      {/* Compliance Trends */}
      <div style={styles.fullWidthChart}>
        <h3 style={styles.chartTitle}>Compliance Trends Over Time</h3>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={defaultComplianceData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Area 
              type="monotone" 
              dataKey="compliant" 
              stackId="1"
              stroke="#22c55e" 
              fill="#22c55e" 
              fillOpacity={0.6}
            />
            <Area 
              type="monotone" 
              dataKey="nonCompliant" 
              stackId="1"
              stroke="#ef4444" 
              fill="#ef4444" 
              fillOpacity={0.6}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Charts Grid */}
      <div style={styles.chartsGrid}>
        {/* Violation Trends */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Violation Trends by Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={defaultViolationTrends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="scaffolding" stroke="#3b82f6" strokeWidth={2} />
              <Line type="monotone" dataKey="ppe" stroke="#8b5cf6" strokeWidth={2} />
              <Line type="monotone" dataKey="electrical" stroke="#f59e0b" strokeWidth={2} />
              <Line type="monotone" dataKey="fallProtection" stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk Distribution */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={defaultRiskDistribution}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {defaultRiskDistribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Critical Violations Trend */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Critical Violations</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={defaultComplianceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="criticalViolations" fill="#ef4444" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Agent Performance */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Multi-Agent Performance</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={[]}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="agent" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="accuracy" fill="#22c55e" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <p>
          🔒 Powered by AI Multi-Agent Architecture
        </p>
        <p style={{ marginTop: '8px', fontSize: '12px' }}>
          <strong>Note:</strong> Connect your ConComplyAI API endpoints to populate this dashboard with real-time data.
        </p>
      </div>
    </div>
  );
};

export default SuccessionShieldEnterprise;
