import React, { useEffect, useState } from 'react';
import { useAuth } from './context/AuthContext'; 
import { useNavigate } from 'react-router-dom'; 
import TherapistAlertsPanel from './components/TherapistAlertsPanel.jsx';
import axios from 'axios';
import { motion } from 'framer-motion';
import { 
  Users, Activity, BookOpen, ClipboardList, 
  Bell, BarChart3, LogOut, ChevronRight, AlertTriangle, ShieldCheck 
} from 'lucide-react';

const TherapistDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate(); 
  const [stats, setStats] = useState({
    totalPatients: 0,
    activeProtocols: 0,
    highRiskCount: 0,
    newPatientsLastMonth: 0
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get('http://localhost:5001/api/therapist/patients');
        const patients = res.data.patients || [];
        const active = patients.filter(p => p.hasActiveProtocol).length;
        const highRisk = patients.filter(p => p.status === 'High Risk').length;
        const oneMonthAgo = new Date();
        oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
        const newPatients = patients.filter(p => new Date(p.date_joined) >= oneMonthAgo).length;

        setStats({ 
            totalPatients: patients.length, 
            activeProtocols: active, 
            highRiskCount: highRisk,
            newPatientsLastMonth: newPatients 
        });
      } catch (error) {
        console.error("Error fetching stats:", error);
      }
    };
    fetchStats();
  }, [user]);

  const handleLogout = () => { if (logout) logout(); navigate('/auth/login'); };

  const actionZones = [
    { title: 'Patient Monitoring', label: 'Review Compliance & Risk', icon: <Users size={22}/>, path: '/therapist/monitoring', desc: 'Real-time adherence & status tracking', border: '#6366F1' },
    { title: 'Advanced Analytics', label: 'AI Recovery Insights', icon: <BarChart3 size={22}/>, path: '/therapist/analytics', desc: 'Neural forecasting of patient progress', border: '#6366F1' },
    { title: 'Exercise Library', label: 'Clinical Movement Repository', icon: <BookOpen size={22}/>, path: '/therapist/library', desc: 'Standardized therapeutic movements', border: '#0F172A' },
    { title: 'Protocol Manager', label: 'Treatment Design & Assignment', icon: <ClipboardList size={22}/>, path: '/therapist/protocols', desc: 'Prescribe recovery pathways', border: '#0F172A' },
  ];

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={styles.container}>
      {/* AI GRID OVERLAY LAYER */}
      <div style={styles.gridOverlay}></div>

      <div style={styles.contentWrapper}>
        <header style={styles.header}>
          <div>
            <div style={styles.badge}><span style={styles.pulse}></span> Live Monitoring Active</div>
            <h1 style={styles.headerTitle}>Clinical Command Center</h1>
            <p style={styles.headerSubtitle}>Lead Clinician: Dr. {user?.name || 'Therapist'}</p>
          </div>
          <button onClick={handleLogout} style={styles.logoutBtn}>
            <LogOut size={16} style={{marginRight: '8px'}}/> Logout
          </button>
        </header>

        <section style={styles.sectionWrapper}>
          <div style={styles.statsGrid}>
            <StatCard label="Total Patient Load" value={stats.totalPatients} icon={<Users color="#6366F1"/>} subText="Total onboarded population" border="#6366F1" />
            <StatCard label="Critical Risk Cases" value={stats.highRiskCount} icon={<AlertTriangle color="#EF4444"/>} color="#EF4444" subText="Urgent intervention required" border={stats.highRiskCount > 0 ? "#EF4444" : "#22C55E"} isRisk={stats.highRiskCount > 0} />
            <StatCard label="Active Protocols" value={stats.activeProtocols} icon={<Activity color="#14B8A6"/>} subText="In-progress treatment plans" border="#22C55E" />
            <StatCard label="System Integrity" value="Stable" icon={<ShieldCheck color="#0F172A"/>} subText="AI Monitoring active" border="#0F172A" />
          </div>
        </section>

        <div style={styles.mainLayout}>
          <div style={styles.alertsWrapper}>
            <TherapistAlertsPanel />
          </div>

          <div style={styles.actionsWrapper}>
            <div style={styles.actionGrid}>
              {actionZones.map((zone, idx) => (
                <motion.div key={idx} whileHover={{ y: -4, boxShadow: '0 8px 25px rgba(15, 23, 42, 0.1)' }} style={{...styles.actionCard, borderTop: `4px solid ${zone.border}`}} onClick={() => navigate(zone.path)}>
                  <div style={styles.actionIconWrapper}>{zone.icon}</div>
                  <div style={{flex: 1}}>
                    <span style={styles.actionLabel}>{zone.label}</span>
                    <h3 style={styles.actionTitle}>{zone.title}</h3>
                    <p style={styles.actionDesc}>{zone.desc}</p>
                  </div>
                  <ChevronRight size={20} color="#CBD5E1" />
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

const StatCard = ({ label, value, icon, subText, color = '#111827', border, isRisk = false }) => (
  <motion.div style={{
    ...styles.statCard, 
    borderTop: `4px solid ${border}`,
    backgroundColor: isRisk ? 'rgba(239, 68, 68, 0.04)' : '#FFFFFF'
  }}>
    <div style={styles.statTop}><span style={styles.statLabel}>{label}</span><div style={styles.statIconBg}>{icon}</div></div>
    <h2 style={{...styles.statValue, color}}>{value}</h2>
    <p style={styles.statSubText}>{subText}</p>
  </motion.div>
);

const styles = {
  container: { 
    backgroundColor: '#F3F6FB', 
    minHeight: '100vh', 
    position: 'relative', 
    overflowX: 'hidden' 
  },
  // Technical Grid Pattern
  gridOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundImage: `radial-gradient(rgba(99, 102, 241, 0.04) 1px, transparent 0)`,
    backgroundSize: '24px 24px',
    pointerEvents: 'none',
    zIndex: 0
  },
  contentWrapper: {
    position: 'relative',
    zIndex: 1,
    padding: '40px'
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '40px' },
  badge: { backgroundColor: '#E0F2FE', color: '#0369A1', padding: '4px 12px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '700', marginBottom: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px' },
  pulse: { width: '8px', height: '8px', backgroundColor: '#0EA5E9', borderRadius: '50%' },
  headerTitle: { color: '#0F172A', fontSize: '2.5rem', fontWeight: '800', margin: 0 },
  headerSubtitle: { color: '#64748B', fontSize: '1.1rem', margin: '4px 0 0 0' },
  logoutBtn: { display: 'flex', alignItems: 'center', padding: '10px 20px', backgroundColor: '#FFF', border: '1px solid #E2E8F0', borderRadius: '12px', color: '#64748B', cursor: 'pointer' },
  sectionWrapper: { backgroundColor: '#EEF2F7', padding: '24px', borderRadius: '20px', marginBottom: '40px', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)' },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px' },
  statCard: { backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '16px', boxShadow: '0 6px 20px rgba(15, 23, 42, 0.06)' },
  statTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' },
  statLabel: { color: '#64748B', fontSize: '0.85rem', fontWeight: '700', textTransform: 'uppercase' },
  statIconBg: { backgroundColor: '#F1F5F9', padding: '10px', borderRadius: '12px' },
  statValue: { fontSize: '2.8rem', fontWeight: '800', margin: 0 },
  statSubText: { color: '#94A3B8', fontSize: '0.85rem', marginTop: '10px', margin: 0 },
  mainLayout: { display: 'grid', gridTemplateColumns: '1fr 1.6fr', gap: '32px' },
  alertsWrapper: { backgroundColor: '#EEF2F7', padding: '20px', borderRadius: '20px', height: 'fit-content' },
  actionsWrapper: { backgroundColor: '#EEF2F7', padding: '20px', borderRadius: '20px' },
  actionGrid: { display: 'grid', gridTemplateColumns: '1fr', gap: '16px' },
  actionCard: { backgroundColor: '#FFFFFF', padding: '24px', borderRadius: '16px', display: 'flex', alignItems: 'center', gap: '24px', cursor: 'pointer', boxShadow: '0 6px 20px rgba(15, 23, 42, 0.06)' },
  actionIconWrapper: { color: '#6366F1', backgroundColor: '#EEF2FF', padding: '14px', borderRadius: '14px' },
  actionLabel: { color: '#14B8A6', fontSize: '0.75rem', fontWeight: '800', textTransform: 'uppercase' },
  actionTitle: { color: '#0F172A', fontSize: '1.3rem', fontWeight: '700', margin: '2px 0' },
  actionDesc: { color: '#64748B', fontSize: '0.95rem', margin: 0 },
};

export default TherapistDashboard;