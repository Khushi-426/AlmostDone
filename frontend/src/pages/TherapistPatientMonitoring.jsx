import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistPatientMonitoring = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRealPatients();
  }, []);

  const fetchRealPatients = async () => {
    try {
      // Fetch from the API
      const response = await axios.get('http://localhost:5001/api/therapist/patients');
      setPatients(response.data.patients);
      setLoading(false);
    } catch (err) {
      console.error("Error loading patients:", err);
      setError("Failed to load patient data from database.");
      setLoading(false);
    }
  };

  const handleBack = () => {
    navigate('/therapist-dashboard');
  };

  // Helper to determine color based on status text
  const getStatusColor = (status) => {
    switch (status) {
      case 'Stable': return '#52c41a'; // Green
      case 'Alert': return '#faad14';  // Orange
      case 'High Risk': return '#f5222d'; // Red
      default: return '#d9d9d9'; // Grey
    }
  };

  if (loading) return <div style={{padding: '40px', textAlign:'center'}}>Loading real patient data...</div>;
  if (error) return <div style={{padding: '40px', textAlign:'center', color:'red'}}>{error}</div>;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.headerRow}>
        <button onClick={handleBack} style={styles.backButton}>
          ← Back to Dashboard
        </button>
        <h2 style={styles.pageTitle}>Patient Monitoring Overview ({patients.length} Active)</h2>
      </div>

      {/* Legend */}
      <div style={styles.legendContainer}>
        <span style={{ fontWeight: 'bold', marginRight: '15px' }}>Status Legend:</span>
        <span style={styles.legendItem}><span style={{...styles.dot, backgroundColor: '#52c41a'}}></span> Stable (Compliant)</span>
        <span style={styles.legendItem}><span style={{...styles.dot, backgroundColor: '#faad14'}}></span> Alert (Low Compliance)</span>
        <span style={styles.legendItem}><span style={{...styles.dot, backgroundColor: '#f5222d'}}></span> High Risk (Non-Compliant)</span>
      </div>

      {/* Real Data Grid */}
      <div style={styles.grid}>
        {patients.length > 0 ? (
          patients.map((patient) => {
            const statusColor = getStatusColor(patient.status);
            
            return (
              <div key={patient.id} style={{...styles.card, borderLeft: `6px solid ${statusColor}`}}>
                <div style={styles.cardHeader}>
                  <h3 style={styles.patientName}>{patient.name}</h3>
                </div>
                
                <div style={styles.infoRow}>
                  <strong>Email:</strong> {patient.email}
                </div>
                
                <div style={styles.infoRow}>
                  <strong>Status:</strong> 
                  <span style={{color: statusColor, fontWeight: 'bold', marginLeft: '5px'}}>
                    {patient.status}
                  </span>
                </div>
                
                <div style={styles.infoRow}>
                  <strong>Last Session:</strong> {patient.last_session}
                </div>

                {/* Compliance Bar */}
                <div style={{marginTop: '15px'}}>
                  <div style={{display:'flex', justifyContent:'space-between', marginBottom:'5px'}}>
                    <span style={{fontSize:'0.9rem', fontWeight:'600'}}>Compliance</span>
                    <span style={{fontSize:'0.9rem'}}>{patient.compliance}%</span>
                  </div>
                  <div style={styles.progressBarBg}>
                    <div style={{
                      ...styles.progressBarFill, 
                      width: `${patient.compliance}%`,
                      backgroundColor: statusColor
                    }}></div>
                  </div>
                </div>

                {/* ✅ UPDATED BUTTON: Now navigates to the dynamic detail page */}
                <button 
                  style={styles.actionButton}
                  onClick={() => navigate(`/therapist/patient-detail/${patient.email}`)}
                >
                  View Detailed Report
                </button>
              </div>
            );
          })
        ) : (
          <div style={{gridColumn: '1/-1', textAlign: 'center', padding: '40px', color: '#666'}}>
            No patients found in your MongoDB database. Ask a user to sign up!
          </div>
        )}
      </div>
    </div>
  );
};

// --- Styles ---
const styles = {
  container: {
    padding: '30px',
    backgroundColor: '#f5f7fa',
    minHeight: '100vh',
    fontFamily: "'Inter', sans-serif",
  },
  headerRow: {
    marginBottom: '20px',
  },
  backButton: {
    background: 'none',
    border: 'none',
    color: '#1890ff',
    cursor: 'pointer',
    fontSize: '1rem',
    marginBottom: '10px',
    padding: 0,
    textDecoration: 'underline'
  },
  pageTitle: {
    color: '#003a8c',
    margin: 0,
    fontSize: '1.8rem'
  },
  legendContainer: {
    backgroundColor: 'white',
    padding: '15px 20px',
    borderRadius: '8px',
    marginBottom: '30px',
    boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '20px'
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.9rem',
    color: '#555'
  },
  dot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    display: 'inline-block',
    marginRight: '8px'
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '25px',
  },
  card: {
    backgroundColor: 'white',
    borderRadius: '10px',
    padding: '20px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    transition: 'transform 0.2s',
  },
  cardHeader: {
      marginBottom: '10px'
  },
  patientName: {
    margin: '0 0 15px 0',
    color: '#003a8c',
    fontSize: '1.4rem'
  },
  infoRow: {
    marginBottom: '8px',
    color: '#555',
    fontSize: '0.95rem'
  },
  progressBarBg: {
    height: '10px',
    width: '100%',
    backgroundColor: '#f0f0f0',
    borderRadius: '5px',
    overflow: 'hidden'
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.5s ease-in-out'
  },
  actionButton: {
    marginTop: '20px',
    width: '100%',
    padding: '10px',
    backgroundColor: '#1890ff',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background 0.2s'
  }
};

export default TherapistPatientMonitoring;