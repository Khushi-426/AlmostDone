import React, { useEffect, useState } from 'react';
import { useAuth } from './context/AuthContext'; 
import { useNavigate } from 'react-router-dom'; 
import TherapistAlertsPanel from './components/TherapistAlertsPanel.jsx';
import axios from 'axios';

const TherapistDashboard = () => {
  // 1. Get logout function from AuthContext
  const { user, logout } = useAuth();
  const navigate = useNavigate(); 
  
  const [stats, setStats] = useState({
    totalPatients: 0,
    activeProtocols: 0,
    newPatientsLastMonth: 0
  });

  // FETCH DASHBOARD STATS
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await axios.get('http://localhost:5001/api/therapist/patients');
        const patients = res.data.patients; 
        
        if (!patients) return;

        const total = patients.length;
        const active = patients.filter(p => p.hasActiveProtocol).length || 0;
        
        const oneMonthAgo = new Date();
        oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
        const newPatients = patients.filter(p => new Date(p.date_joined) >= oneMonthAgo).length;

        setStats({ totalPatients: total, activeProtocols: active, newPatientsLastMonth: newPatients });

      } catch (error) {
        console.error("Error fetching stats:", error);
      }
    };

    fetchStats();
  }, [user]);

  const displayName = user?.name || user?.email || 'Therapist';

  // --- LOGOUT HANDLER ---
  const handleLogout = () => {
    // 1. Clear Auth State
    if (logout) logout(); 
    // 2. Redirect to Login Page
    navigate('/auth/login'); 
  };

  // Navigation Handlers
  const handleGoToPatientMonitoring = () => navigate('/therapist/monitoring');
  const handleGoToLibrary = () => navigate('/therapist/library');
  const handleGoToProtocolManager = () => navigate('/therapist/protocols');
  const handleGoToNotifications = () => navigate('/therapist/notifications');
  const handleGoToAnalytics = () => navigate('/therapist/analytics');

  return (
    <div style={styles.dashboardContainer}>
      {/* HEADER SECTION WITH LOGOUT */}
      <div style={styles.headerRow}>
        <div>
            <h1 style={styles.headerText}>Welcome, Dr. {displayName}</h1>
            <p style={{ fontSize: '1.1rem', color: '#555' }}>Dashboard Summary & Quick Actions</p>
        </div>
        
        {/* LOGOUT BUTTON */}
        <button onClick={handleLogout} style={styles.logoutButton}>
            Logout / Switch User
        </button>
      </div>

      {/* Top Section: Alerts Panel + Quick Stats */}
      <div style={styles.topSection}>
        <div style={{ flex: '2', minWidth: '300px' }}>
             <TherapistAlertsPanel />
        </div>
        
        <div style={styles.quickStatsCard}>
            <h2 style={{color: '#0050b3', margin: '0 0 10px 0'}}>Total Patients</h2>
            <p style={{fontSize: '3.5rem', margin: '0', fontWeight: 'bold', color: '#333'}}>
                {stats.totalPatients}
            </p>
            <div style={{marginTop: '15px'}}>
                <p style={{color: '#52c41a', fontWeight: 'bold', margin: '5px 0'}}>
                    {stats.activeProtocols} Active Protocols
                </p>
                <p style={{color: '#888', fontSize: '0.9rem', margin: '0'}}>
                    +{stats.newPatientsLastMonth} new this month
                </p>
            </div>
        </div>
      </div>

      {/* Main Grid */}
      <div style={styles.mainGrid}>
        
        <div style={styles.cardStyle}>
          <h2 style={styles.cardHeaderStyle}>Patient Monitoring</h2>
          <p>Review compliance, risk status, and session data for all assigned patients.</p>
          <button style={styles.buttonStyle} onClick={handleGoToPatientMonitoring}>Go to Monitoring</button>
        </div>

        <div style={styles.cardStyle}>
          <h2 style={styles.cardHeaderStyle}>Advanced Analytics</h2>
          <p>Visualize Quality Score trends, functional improvements, and AI forecasts.</p>
          <button style={styles.buttonStyle} onClick={handleGoToAnalytics}>View Analytics</button>
        </div>

        <div style={styles.cardStyle}>
          <h2 style={styles.cardHeaderStyle}>Exercise Library</h2>
          <p>Create, categorize, and manage the core exercises used in protocols.</p>
          <button style={styles.buttonStyle} onClick={handleGoToLibrary}>Manage Library</button>
        </div>

        <div style={styles.cardStyle}>
          <h2 style={styles.cardHeaderStyle}>Protocols & Assignment</h2>
          <p>Define sets, reps, and difficulty, then assign protocols to patients.</p>
          <button style={styles.buttonStyle} onClick={handleGoToProtocolManager}>Manage Protocols</button>
        </div>
        
        <div style={styles.cardStyle}>
          <h2 style={styles.cardHeaderStyle}>Notifications Log</h2>
          <p>View automated reminders, confirmations, and low adherence alerts.</p>
          <button style={styles.buttonStyle} onClick={handleGoToNotifications}>View Notifications</button>
        </div>
      </div>
    </div>
  );
};

// --- Styles ---
const styles = {
    dashboardContainer: { 
        padding: '30px', 
        backgroundColor: '#f0f2f5', 
        minHeight: '100vh',
        fontFamily: "'Inter', sans-serif",
    },
    headerRow: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '30px',
        borderBottom: '2px solid #e2e8f0',
        paddingBottom: '20px'
    },
    headerText: { 
        color: '#1a365d', 
        fontSize: '2.2rem',
        marginBottom: '5px',
        fontWeight: '700',
        margin: 0
    },
    logoutButton: {
        padding: '10px 20px',
        backgroundColor: '#fff',
        color: '#d32f2f',
        border: '2px solid #d32f2f',
        borderRadius: '8px',
        fontWeight: 'bold',
        cursor: 'pointer',
        transition: '0.2s',
        fontSize: '0.9rem'
    },
    topSection: {
        display: 'flex',
        flexWrap: 'wrap', 
        gap: '20px',
        marginBottom: '40px'
    },
    quickStatsCard: {
        backgroundColor: 'white',
        padding: '30px',
        borderRadius: '16px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
        flex: '1 1 250px', 
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center'
    },
    mainGrid: { 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
        gap: '30px', 
    },
    cardStyle: { 
        backgroundColor: 'white', 
        padding: '30px', 
        borderRadius: '16px', 
        boxShadow: '0 4px 6px rgba(0,0,0,0.02)',
        border: '1px solid #e2e8f0',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
    },
    cardHeaderStyle: { 
        marginBottom: '15px', 
        color: '#2c5282',
        fontSize: '1.5rem',
        fontWeight: '600'
    },
    buttonStyle: { 
        padding: '12px 20px', 
        backgroundColor: '#3182ce', 
        color: 'white', 
        border: 'none', 
        borderRadius: '8px', 
        cursor: 'pointer', 
        marginTop: '20px',
        fontWeight: '600',
        width: '100%',
    }
};

export default TherapistDashboard;