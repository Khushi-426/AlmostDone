import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistAnalytics = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAggregateData();
  }, []);

  const fetchAggregateData = async () => {
    try {
      // Reuse the existing patient endpoint
      const res = await axios.get('http://localhost:5001/api/therapist/patients');
      const patients = res.data.patients || [];

      // Calculate Aggregates
      const totalPatients = patients.length;
      const activePatients = patients.filter(p => p.status !== 'High Risk').length; // Assuming High Risk might imply inactivity or issues
      const totalCompliance = patients.reduce((acc, p) => acc + (p.compliance || 0), 0);
      const avgCompliance = totalPatients > 0 ? Math.round(totalCompliance / totalPatients) : 0;
      
      const riskDistribution = {
        stable: patients.filter(p => p.status === 'Stable').length,
        alert: patients.filter(p => p.status === 'Alert').length,
        highRisk: patients.filter(p => p.status === 'High Risk').length,
      };

      setStats({
        totalPatients,
        activePatients,
        avgCompliance,
        riskDistribution
      });
      setLoading(false);

    } catch (err) {
      console.error("Error loading analytics:", err);
      setLoading(false);
    }
  };

  if (loading) return <div style={{padding:'40px', textAlign:'center'}}>Loading System Analytics...</div>;

  return (
    <div style={styles.container}>
      <button onClick={() => navigate('/therapist-dashboard')} style={styles.backButton}>← Back to Dashboard</button>
      <h1 style={styles.header}>Clinic Performance Analytics</h1>

      {/* --- KPI CARDS --- */}
      <div style={styles.kpiGrid}>
        <div style={styles.kpiCard}>
          <h3 style={styles.kpiTitle}>Total Patients</h3>
          <p style={{...styles.kpiValue, color: '#1890ff'}}>{stats.totalPatients}</p>
        </div>
        <div style={styles.kpiCard}>
          <h3 style={styles.kpiTitle}>Avg. Compliance</h3>
          <p style={{...styles.kpiValue, color: stats.avgCompliance > 70 ? '#52c41a' : '#faad14'}}>
            {stats.avgCompliance}%
          </p>
        </div>
        <div style={styles.kpiCard}>
          <h3 style={styles.kpiTitle}>At-Risk Patients</h3>
          <p style={{...styles.kpiValue, color: '#f5222d'}}>{stats.riskDistribution.highRisk}</p>
          <span style={{fontSize:'0.8rem', color:'#888'}}>Require Immediate Attention</span>
        </div>
      </div>

      {/* --- CHARTS SECTION (Visualized via CSS Bars) --- */}
      <div style={styles.chartsGrid}>
        
        {/* Risk Distribution Chart */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>Patient Risk Distribution</h3>
          <div style={styles.barContainer}>
            <div style={styles.barRow}>
              <span style={styles.label}>Stable</span>
              <div style={{...styles.bar, width: `${(stats.riskDistribution.stable / stats.totalPatients)*100}%`, backgroundColor:'#52c41a'}}></div>
              <span style={styles.count}>{stats.riskDistribution.stable}</span>
            </div>
            <div style={styles.barRow}>
              <span style={styles.label}>Alert</span>
              <div style={{...styles.bar, width: `${(stats.riskDistribution.alert / stats.totalPatients)*100}%`, backgroundColor:'#faad14'}}></div>
              <span style={styles.count}>{stats.riskDistribution.alert}</span>
            </div>
            <div style={styles.barRow}>
              <span style={styles.label}>High Risk</span>
              <div style={{...styles.bar, width: `${(stats.riskDistribution.highRisk / stats.totalPatients)*100}%`, backgroundColor:'#f5222d'}}></div>
              <span style={styles.count}>{stats.riskDistribution.highRisk}</span>
            </div>
          </div>
        </div>

        {/* System Health Status */}
        <div style={styles.chartCard}>
          <h3 style={styles.chartTitle}>System Health</h3>
          <p style={{margin:'20px 0', color:'#555'}}>
            The AI Engine is actively monitoring <strong>{stats.totalPatients}</strong> patients.
            Currently, <strong>{stats.riskDistribution.stable}</strong> are performing within expected recovery parameters.
          </p>
          <button style={styles.actionButton} onClick={() => navigate('/therapist/monitoring')}>
            Go to Patient Monitoring
          </button>
        </div>
      </div>
    </div>
  );
};

// Styles
const styles = {
  container: { padding: '30px', backgroundColor: '#f0f2f5', minHeight: '100vh', fontFamily: 'Inter, sans-serif' },
  backButton: { background: 'none', border: 'none', color: '#1890ff', cursor: 'pointer', marginBottom: '20px', textDecoration: 'underline' },
  header: { color: '#003a8c', marginBottom: '30px' },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '30px' },
  kpiCard: { backgroundColor: 'white', padding: '25px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', textAlign: 'center' },
  kpiTitle: { margin: 0, color: '#666', fontSize: '1rem' },
  kpiValue: { fontSize: '2.5rem', fontWeight: 'bold', margin: '10px 0' },
  chartsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' },
  chartCard: { backgroundColor: 'white', padding: '25px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' },
  chartTitle: { margin: '0 0 20px 0', color: '#333' },
  barContainer: { display: 'flex', flexDirection: 'column', gap: '15px' },
  barRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  label: { width: '80px', fontSize: '0.9rem', color: '#555' },
  bar: { height: '12px', borderRadius: '6px', minWidth: '5px', transition: 'width 0.5s' },
  count: { fontWeight: 'bold', color: '#333' },
  actionButton: { width: '100%', padding: '12px', backgroundColor: '#1890ff', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }
};

export default TherapistAnalytics;