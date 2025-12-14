import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const TherapistPatientDetail = () => {
  const { email } = useParams(); // We get the email from the URL
  const navigate = useNavigate();
  
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDetails = async () => {
      try {
        // Use the existing analytics endpoint from your backend
        const res = await axios.post('http://localhost:5001/api/user/analytics_detailed', { email });
        setAnalytics(res.data);
        setLoading(false);
      } catch (err) {
        console.error(err);
        setLoading(false);
      }
    };
    fetchDetails();
  }, [email]);

  if (loading) return <div className="p-10 text-center">Loading Patient Report...</div>;
  if (!analytics) return <div className="p-10 text-center text-red-500">No data found for this patient.</div>;

  return (
    <div style={styles.container}>
      <button onClick={() => navigate(-1)} style={styles.backButton}>← Back</button>
      
      <div style={styles.header}>
        <h1 style={{margin:0}}>Patient Report: {email}</h1>
        <span style={styles.badge}>Total Sessions: {analytics.total_sessions || 0}</span>
      </div>

      <div style={styles.grid}>
        {/* Card 1: Accuracy */}
        <div style={styles.card}>
          <h3>Avg Accuracy</h3>
          <p style={{fontSize: '2.5rem', color: '#1890ff', fontWeight:'bold'}}>
            {analytics.average_accuracy || 0}%
          </p>
        </div>

        {/* Card 2: Total Reps */}
        <div style={styles.card}>
          <h3>Total Reps</h3>
          <p style={{fontSize: '2.5rem', color: '#52c41a', fontWeight:'bold'}}>
            {analytics.total_reps || 0}
          </p>
        </div>
      </div>

      {/* Session History Table */}
      <div style={styles.section}>
        <h2 style={{color: '#333', marginBottom:'15px'}}>Session History</h2>
        {(!analytics.history || analytics.history.length === 0) ? (
          <p>No sessions recorded yet.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr style={{backgroundColor:'#f5f5f5', textAlign:'left'}}>
                <th style={styles.th}>Date</th>
                <th style={styles.th}>Exercise</th>
                <th style={styles.th}>Reps</th>
                <th style={styles.th}>Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {analytics.history.map((session, idx) => (
                <tr key={idx} style={{borderBottom:'1px solid #eee'}}>
                  <td style={styles.td}>{session.date}</td>
                  <td style={styles.td}>{session.exercise}</td>
                  <td style={styles.td}>{session.reps}</td>
                  <td style={styles.td}>
                    <span style={{
                      padding:'4px 8px', 
                      borderRadius:'4px',
                      backgroundColor: session.accuracy > 80 ? '#f6ffed' : '#fff1f0',
                      color: session.accuracy > 80 ? '#52c41a' : '#f5222d'
                    }}>
                      {session.accuracy}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

const styles = {
  container: { padding: '30px', backgroundColor: '#f5f7fa', minHeight: '100vh', fontFamily:'Inter, sans-serif' },
  backButton: { background: 'none', border: 'none', color: '#1890ff', cursor: 'pointer', marginBottom: '20px', fontSize:'1rem' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' },
  badge: { backgroundColor: '#e6f7ff', color: '#1890ff', padding: '8px 15px', borderRadius: '20px', fontWeight: 'bold' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '30px' },
  card: { backgroundColor: 'white', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)', textAlign:'center' },
  section: { backgroundColor: 'white', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '12px', borderBottom: '2px solid #eee', color: '#666' },
  td: { padding: '12px', color: '#333' }
};

export default TherapistPatientDetail;