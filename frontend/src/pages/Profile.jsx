import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Activity, Clock, Trophy, TrendingUp, Calendar } from 'lucide-react';
import { motion } from 'framer-motion';

const StatCard = ({ title, value, icon: Icon, color }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    style={{
      background: 'white',
      padding: '24px',
      borderRadius: '20px',
      boxShadow: '0 10px 30px rgba(0,0,0,0.05)',
      display: 'flex',
      alignItems: 'center',
      gap: '20px',
      flex: 1,
      minWidth: '200px'
    }}
  >
    <div style={{ padding: '15px', borderRadius: '15px', background: `${color}20`, color: color }}>
      <Icon size={28} />
    </div>
    <div>
      <h3 style={{ margin: 0, fontSize: '2rem', fontWeight: '800', color: '#1a1a1a' }}>{value}</h3>
      <p style={{ margin: 0, color: '#888', fontSize: '0.9rem', fontWeight: '600' }}>{title}</p>
    </div>
  </motion.div>
);

const Profile = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      if (user?.email) {
        try {
          const res = await axios.post('http://127.0.0.1:5000/api/user/stats', { email: user.email });
          setStats(res.data);
        } catch (err) {
          console.error("Failed to load stats", err);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchStats();
  }, [user]);

  if (!user) return <div style={{ padding: '40px', textAlign: 'center' }}>Please log in to view profile.</div>;

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px' }}>
      
      {/* HEADER */}
      <div style={{ marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '800', marginBottom: '10px' }}>
          Hello, <span style={{ color: 'var(--primary-color)' }}>{user.name}</span>
        </h1>
        <p style={{ color: '#666', fontSize: '1.1rem' }}>Here is your performance summary for this week.</p>
      </div>

      {/* STATS GRID */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '40px' }}>
        <StatCard title="Total Workouts" value={stats?.total_workouts || 0} icon={Activity} color="#FF6B6B" />
        <StatCard title="Total Reps" value={stats?.total_reps || 0} icon={TrendingUp} color="#4ECDC4" />
        <StatCard title="Minutes Trained" value={stats?.total_minutes || 0} icon={Clock} color="#FFD93D" />
        <StatCard title="Accuracy Score" value={`${stats?.accuracy || 0}%`} icon={Trophy} color="#6C5CE7" />
      </div>

      {/* GRAPH SECTION */}
      <div style={{ background: 'white', padding: '30px', borderRadius: '24px', boxShadow: '0 10px 40px rgba(0,0,0,0.05)' }}>
        <h3 style={{ marginBottom: '30px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Calendar size={20} color="var(--primary-color)" /> Recent Activity
        </h3>
        
        {loading ? (
          <p>Loading data...</p>
        ) : stats?.graph_data?.length > 0 ? (
          <div style={{ display: 'flex', alignItems: 'flex-end', height: '200px', gap: '15px' }}>
            {stats.graph_data.map((day, index) => (
              <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                <motion.div 
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.min(day.reps * 3, 150)}px` }} // Scale bars
                  style={{ width: '100%', background: 'var(--primary-color)', borderRadius: '8px', opacity: 0.8 }}
                />
                <span style={{ fontSize: '0.8rem', color: '#888', fontWeight: '600' }}>{day.date.slice(5)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '40px', textAlign: 'center', background: '#f9f9f9', borderRadius: '15px', color: '#888' }}>
            No workout data available yet. Start your first session!
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;