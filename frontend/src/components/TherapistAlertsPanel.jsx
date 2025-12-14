import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistAlertsPanel = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      // 1. Fetch System Notifications (Protocol changes, etc.)
      const notifRes = await axios.get('http://localhost:5001/api/therapist/notifications');
      
      // 2. Fetch Patients to find "High Risk" ones dynamically
      const patRes = await axios.get('http://localhost:5001/api/therapist/patients');
      
      const systemEvents = notifRes.data || [];
      const patients = patRes.data.patients || [];

      // 3. Generate "Urgent" alerts for High Risk patients
      const riskAlerts = patients
        .filter(p => p.status === 'High Risk' || p.status === 'Alert')
        .map(p => ({
          id: `risk-${p.id}`,
          type: p.status === 'High Risk' ? 'Critical' : 'Warning',
          title: p.name,
          message: p.status === 'High Risk' ? 'Patient is Non-Compliant (High Risk)' : 'Patient compliance is dropping',
          time: 'Live Status',
          isPatient: true,
          email: p.email
        }));

      // 4. Combine and Sort
      const combined = [...riskAlerts, ...systemEvents].slice(0, 5); // Show top 5
      setAlerts(combined);
      setLoading(false);

    } catch (err) {
      console.error("Error fetching alerts:", err);
      setLoading(false);
    }
  };

  if (loading) return <div className="p-4 bg-white rounded shadow">Loading Alerts...</div>;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={{ fontSize: '1.2rem' }}>🔔</span>
        <h3 style={{ margin: 0, marginLeft: '10px', color: '#d32f2f' }}>Urgent Alerts ({alerts.length})</h3>
      </div>
      
      <div style={styles.list}>
        {alerts.length === 0 ? (
          <p style={{ padding: '15px', color: '#666' }}>No urgent alerts right now.</p>
        ) : (
          alerts.map((alert) => (
            <div 
              key={alert.id} 
              style={{
                ...styles.alertItem, 
                borderLeft: alert.type === 'Critical' ? '4px solid #d32f2f' : '4px solid #ed6c02'
              }}
              onClick={() => alert.isPatient && navigate(`/therapist/patient-detail/${alert.email}`)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong style={{ color: '#333' }}>{alert.title || 'System'}</strong>
                <span style={{ fontSize: '0.8rem', color: '#888' }}>{alert.time || alert.date}</span>
              </div>
              <div style={{ color: alert.type === 'Critical' ? '#d32f2f' : '#555', fontSize: '0.9rem' }}>
                {alert.message}
              </div>
            </div>
          ))
        )}
      </div>
      <button style={styles.viewAllBtn} onClick={() => navigate('/therapist/notifications')}>
        View Full Notification Log →
      </button>
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    overflow: 'hidden',
    flex: '1',
    minWidth: '300px'
  },
  header: {
    padding: '15px 20px',
    borderBottom: '1px solid #eee',
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#fff5f5'
  },
  list: {
    maxHeight: '300px',
    overflowY: 'auto'
  },
  alertItem: {
    padding: '15px 20px',
    borderBottom: '1px solid #f0f0f0',
    cursor: 'pointer',
    transition: 'background 0.2s',
  },
  viewAllBtn: {
    width: '100%',
    padding: '12px',
    background: 'none',
    border: 'none',
    color: '#1976d2',
    cursor: 'pointer',
    fontWeight: '600',
    borderTop: '1px solid #eee'
  }
};

export default TherapistAlertsPanel;