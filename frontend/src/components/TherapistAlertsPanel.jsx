import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Bell, Clock, ExternalLink } from 'lucide-react';

const TherapistAlertsPanel = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const [notifRes, patRes] = await Promise.all([
          axios.get('http://localhost:5001/api/therapist/notifications'),
          axios.get('http://localhost:5001/api/therapist/patients')
        ]);
        const riskAlerts = (patRes.data.patients || []).filter(p => p.status === 'High Risk' || p.status === 'Alert').map(p => ({
            id: `risk-${p.id}`, 
            severity: p.status === 'High Risk' ? 'CRITICAL' : 'WARNING', 
            border: p.status === 'High Risk' ? '#EF4444' : '#F59E0B',
            bg: p.status === 'High Risk' ? 'rgba(239, 68, 68, 0.04)' : 'rgba(245, 158, 11, 0.04)',
            title: p.name, 
            message: p.status === 'High Risk' ? 'Critical drop in compliance' : 'Adherence variance detected',
            time: 'LIVE', isPatient: true, email: p.email
        }));
        setAlerts([...riskAlerts, ...(notifRes.data || [])].slice(0, 6));
        setLoading(false);
      } catch (err) { setLoading(false); }
    };
    fetchAlerts();
  }, []);

  if (loading) return <div style={styles.skeleton}>Analyzing Stream...</div>;

  const hasCritical = alerts.some(a => a.severity === 'CRITICAL');

  return (
    <div style={{
      ...styles.container, 
      borderTop: `4px solid ${hasCritical ? '#EF4444' : '#0F172A'}`,
      backgroundColor: '#FFFFFF'
    }}>
      <div style={styles.header}><h3 style={styles.headerTitle}>Priority Alerts</h3><span style={styles.countBadge}>{alerts.length}</span></div>
      <div style={styles.list}>
        {alerts.map((alert, i) => (
          <motion.div 
            key={alert.id} 
            style={{
              ...styles.alertItem, 
              borderLeft: `5px solid ${alert.border || '#0F172A'}`,
              backgroundColor: alert.bg || '#FFFFFF'
            }} 
            onClick={() => alert.isPatient && navigate(`/therapist/patient-detail/${alert.email}`)}
          >
            <div style={styles.alertTop}><span style={{...styles.severity, color: alert.border}}>{alert.severity || 'SYSTEM'}</span><span style={styles.time}><Clock size={12} /> {alert.time || alert.date}</span></div>
            <div style={styles.titleRow}><strong style={styles.alertTitle}>{alert.title || 'System'}</strong>{alert.isPatient && <ExternalLink size={14} color="#94A3B8" />}</div>
            <p style={styles.msg}>{alert.message}</p>
          </motion.div>
        ))}
      </div>
      <button style={styles.fullLogBtn} onClick={() => navigate('/therapist/notifications')}>Access Notification Ledger</button>
    </div>
  );
};

const styles = {
  container: { backgroundColor: '#FFF', borderRadius: '16px', boxShadow: '0 6px 20px rgba(15, 23, 42, 0.06)', overflow: 'hidden' },
  header: { padding: '24px', borderBottom: '1px solid #F1F5F9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  headerTitle: { margin: 0, fontSize: '1.1rem', color: '#0F172A', fontWeight: '800' },
  countBadge: { backgroundColor: '#F1F5F9', color: '#475569', padding: '4px 10px', borderRadius: '8px', fontSize: '0.85rem', fontWeight: '700' },
  list: { maxHeight: '450px', overflowY: 'auto' },
  alertItem: { padding: '20px 24px', borderBottom: '1px solid #F1F5F9', cursor: 'pointer', transition: 'background 0.2s' },
  alertTop: { display: 'flex', justifyContent: 'space-between', marginBottom: '8px' },
  severity: { fontSize: '0.7rem', fontWeight: '900', letterSpacing: '0.1em' },
  time: { fontSize: '0.75rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '4px' },
  titleRow: { display: 'flex', justifyContent: 'space-between', marginBottom: '4px' },
  alertTitle: { color: '#1E293B', fontSize: '1rem', fontWeight: '700' },
  msg: { color: '#64748B', fontSize: '0.9rem', margin: 0, fontWeight: '500' },
  fullLogBtn: { width: '100%', padding: '18px', background: '#F8FAFC', border: 'none', color: '#6366F1', cursor: 'pointer', fontWeight: '700' },
  skeleton: { padding: '40px', textAlign: 'center', backgroundColor: '#FFF', borderRadius: '16px' }
};

export default TherapistAlertsPanel;