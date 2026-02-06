import React, { useState, useEffect } from 'react';

/**
 * SentinelLiveFeed - Real-time monitoring dashboard
 * 
 * Displays live feed of:
 * - Document detections
 * - Expiration warnings
 * - Compliance violations
 * - Site updates
 * 
 * Integrated from Sentinel-Scope into ConComplyAi
 */
const SentinelLiveFeed = () => {
  const [events, setEvents] = useState([]);
  const [statistics, setStatistics] = useState(null);
  const [filter, setFilter] = useState('all'); // all, critical, unprocessed
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [loading, setLoading] = useState(false);

  // Fetch events from API
  const fetchEvents = async () => {
    setLoading(true);
    try {
      const unprocessedOnly = filter === 'unprocessed';
      const response = await fetch(
        `http://localhost:8000/api/sentinel/feed?limit=50&unprocessed_only=${unprocessedOnly}`
      );
      const data = await response.json();
      
      let filteredEvents = data.events || [];
      
      // Apply critical filter
      if (filter === 'critical') {
        filteredEvents = filteredEvents.filter(e => e.priority <= 2);
      }
      
      setEvents(filteredEvents);
    } catch (error) {
      console.error('Error fetching events:', error);
    }
    setLoading(false);
  };

  // Fetch statistics
  const fetchStatistics = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/sentinel/statistics');
      const data = await response.json();
      setStatistics(data);
    } catch (error) {
      console.error('Error fetching statistics:', error);
    }
  };

  // Mark event as processed
  const markProcessed = async (eventId) => {
    try {
      await fetch(`http://localhost:8000/api/sentinel/mark-processed/${eventId}`, {
        method: 'POST'
      });
      fetchEvents(); // Refresh
    } catch (error) {
      console.error('Error marking event:', error);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    fetchEvents();
    fetchStatistics();

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchEvents();
        fetchStatistics();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [filter, autoRefresh]);

  // Get event icon
  const getEventIcon = (eventType) => {
    const icons = {
      DOCUMENT_DETECTED: '📄',
      EXPIRATION_WARNING: '⚠️',
      COMPLIANCE_VIOLATION: '🚨',
      SITE_UPDATE: '📍'
    };
    return icons[eventType] || '📋';
  };

  // Get priority color
  const getPriorityColor = (priority) => {
    if (priority === 1) return '#ef4444'; // Critical - Red
    if (priority === 2) return '#f59e0b'; // High - Orange
    if (priority === 3) return '#eab308'; // Medium - Yellow
    return '#6b7280'; // Info - Gray
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>🔭 Sentinel Live Feed</h1>
          <p style={styles.subtitle}>Real-time compliance monitoring</p>
        </div>
        <div style={styles.controls}>
          <label style={styles.checkbox}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            <span style={{ marginLeft: '6px' }}>Auto-refresh</span>
          </label>
        </div>
      </div>

      {/* Statistics Cards */}
      {statistics && (
        <div style={styles.statsGrid}>
          <div style={styles.statCard}>
            <div style={styles.statValue}>{statistics.total_events}</div>
            <div style={styles.statLabel}>Total Events</div>
          </div>
          <div style={styles.statCard}>
            <div style={{...styles.statValue, color: '#f59e0b'}}>
              {statistics.unprocessed_events}
            </div>
            <div style={styles.statLabel}>Unprocessed</div>
          </div>
          <div style={styles.statCard}>
            <div style={{...styles.statValue, color: '#ef4444'}}>
              {statistics.critical_events}
            </div>
            <div style={styles.statLabel}>Critical</div>
          </div>
          <div style={styles.statCard}>
            <div style={{
              ...styles.statValue,
              fontSize: '20px',
              color: statistics.monitoring_active ? '#10b981' : '#6b7280'
            }}>
              {statistics.monitoring_active ? '🟢 Active' : '⚫ Inactive'}
            </div>
            <div style={styles.statLabel}>Monitoring Status</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div style={styles.filters}>
        <button
          style={filter === 'all' ? styles.filterButtonActive : styles.filterButton}
          onClick={() => setFilter('all')}
        >
          All Events
        </button>
        <button
          style={filter === 'critical' ? styles.filterButtonActive : styles.filterButton}
          onClick={() => setFilter('critical')}
        >
          Critical Only
        </button>
        <button
          style={filter === 'unprocessed' ? styles.filterButtonActive : styles.filterButton}
          onClick={() => setFilter('unprocessed')}
        >
          Unprocessed
        </button>
      </div>

      {/* Events Feed */}
      <div style={styles.feed}>
        {loading && events.length === 0 ? (
          <div style={styles.loading}>Loading events...</div>
        ) : events.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔭</div>
            <div style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
              No Events Yet
            </div>
            <div style={{ color: '#6b7280' }}>
              Sentinel is monitoring. New events will appear here in real-time.
            </div>
          </div>
        ) : (
          events.map((event) => (
            <div key={event.event_id} style={styles.eventCard}>
              <div style={styles.eventHeader}>
                <div style={styles.eventIcon}>
                  {getEventIcon(event.event_type)}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={styles.eventTitle}>
                    {event.event_type.replace(/_/g, ' ')}
                  </div>
                  <div style={styles.eventSource}>
                    Source: {event.source}
                  </div>
                </div>
                <div style={styles.eventMeta}>
                  <div
                    style={{
                      ...styles.priorityBadge,
                      backgroundColor: getPriorityColor(event.priority)
                    }}
                  >
                    P{event.priority}
                  </div>
                  <div style={styles.timestamp}>
                    {formatTime(event.timestamp)}
                  </div>
                </div>
              </div>

              {/* Event Data */}
              <div style={styles.eventData}>
                {Object.entries(event.data).slice(0, 3).map(([key, value]) => (
                  <div key={key} style={styles.dataRow}>
                    <span style={styles.dataKey}>{key}:</span>
                    <span style={styles.dataValue}>
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div style={styles.eventActions}>
                {!event.processed && (
                  <button
                    style={styles.actionButton}
                    onClick={() => markProcessed(event.event_id)}
                  >
                    ✓ Mark Processed
                  </button>
                )}
                {event.processed && (
                  <span style={styles.processedBadge}>✓ Processed</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    padding: '24px',
    backgroundColor: '#f9fafb',
    minHeight: '100vh'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '24px'
  },
  title: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 8px 0'
  },
  subtitle: {
    fontSize: '16px',
    color: '#6b7280',
    margin: 0
  },
  controls: {
    display: 'flex',
    gap: '16px'
  },
  checkbox: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '14px',
    color: '#374151',
    cursor: 'pointer'
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    marginBottom: '24px'
  },
  statCard: {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    textAlign: 'center'
  },
  statValue: {
    fontSize: '32px',
    fontWeight: '700',
    color: '#3b82f6',
    marginBottom: '8px'
  },
  statLabel: {
    fontSize: '14px',
    color: '#6b7280',
    fontWeight: '500'
  },
  filters: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px'
  },
  filterButton: {
    padding: '10px 20px',
    backgroundColor: 'white',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#374151',
    cursor: 'pointer',
    transition: 'all 0.2s'
  },
  filterButtonActive: {
    padding: '10px 20px',
    backgroundColor: '#3b82f6',
    border: '1px solid #3b82f6',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '600',
    color: 'white',
    cursor: 'pointer'
  },
  feed: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  loading: {
    textAlign: 'center',
    padding: '40px',
    fontSize: '16px',
    color: '#6b7280'
  },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    backgroundColor: 'white',
    borderRadius: '8px',
    border: '2px dashed #d1d5db'
  },
  eventCard: {
    backgroundColor: 'white',
    borderRadius: '8px',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #e5e7eb'
  },
  eventHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '12px'
  },
  eventIcon: {
    fontSize: '24px',
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f3f4f6',
    borderRadius: '8px'
  },
  eventTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    textTransform: 'capitalize',
    marginBottom: '4px'
  },
  eventSource: {
    fontSize: '13px',
    color: '#6b7280'
  },
  eventMeta: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '6px'
  },
  priorityBadge: {
    padding: '4px 10px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '600',
    color: 'white'
  },
  timestamp: {
    fontSize: '12px',
    color: '#9ca3af'
  },
  eventData: {
    backgroundColor: '#f9fafb',
    padding: '12px',
    borderRadius: '6px',
    marginBottom: '12px'
  },
  dataRow: {
    fontSize: '13px',
    marginBottom: '6px',
    display: 'flex',
    gap: '8px'
  },
  dataKey: {
    fontWeight: '600',
    color: '#374151',
    minWidth: '120px'
  },
  dataValue: {
    color: '#6b7280',
    wordBreak: 'break-word'
  },
  eventActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'flex-end'
  },
  actionButton: {
    padding: '8px 16px',
    backgroundColor: '#10b981',
    border: 'none',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    color: 'white',
    cursor: 'pointer',
    transition: 'background-color 0.2s'
  },
  processedBadge: {
    padding: '8px 16px',
    backgroundColor: '#e5e7eb',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#6b7280'
  }
};

export default SentinelLiveFeed;
