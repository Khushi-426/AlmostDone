import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Timer, ArrowLeft, StopCircle, Info, CheckCircle, 
  ChevronRight, Activity, AlertCircle, Play, Dumbbell 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './context/AuthContext'; // IMPORT AUTH CONTEXT

// --- MOCK DATA: EXERCISE LIBRARY ---
const EXERCISES = [
  {
    id: 'bicep_curl',
    title: 'Bicep Curls',
    category: 'Strength • Arms',
    duration: '5 Mins',
    difficulty: 'Beginner',
    recommended: true,
    description: 'A fundamental exercise for building upper arm strength and stability.',
    instructions: [
      "Stand with feet shoulder-width apart.",
      "Keep elbows close to your torso at all times.",
      "Contract biceps to curl weights upwards.",
      "Lower slowly to starting position.",
      "Avoid swinging your body."
    ],
    color: '#E8F5E9',
    iconColor: '#2C5D31'
  },
  {
    id: 'shoulder_press',
    title: 'Shoulder Press',
    category: 'Mobility • Shoulders',
    duration: '8 Mins',
    difficulty: 'Intermediate',
    recommended: false,
    description: 'Overhead press to improve shoulder mobility and strength.',
    instructions: [
        "Hold weights at shoulder level with palms facing forward.",
        "Push weights up until arms are fully extended.",
        "Lower back down slowly to the starting position.",
        "Keep your back straight throughout."
    ],
    color: '#FFF3E0',
    iconColor: '#EF6C00'
  }
];

const Tracker = () => {
  const navigate = useNavigate();
  const { user } = useAuth(); // GET USER INFO
  
  // --- STATES ---
  // Flow: LIBRARY -> DEMO -> SESSION
  const [viewMode, setViewMode] = useState('LIBRARY'); 
  const [selectedExercise, setSelectedExercise] = useState(null);
  
  // Tracker Logic States
  const [active, setActive] = useState(false);
  const [data, setData] = useState(null);
  const [sessionTime, setSessionTime] = useState(0);
  const [feedback, setFeedback] = useState("Press Start");
  const [videoTimestamp, setVideoTimestamp] = useState(Date.now());
  
  const intervalRef = useRef(null);
  const timerRef = useRef(null);

  // --- SESSION CONTROL FUNCTIONS ---
  const startSession = async () => {
    try {
        const res = await fetch('http://localhost:5000/start_tracking');
        const json = await res.json();
        if (json.status === 'success') {
          setVideoTimestamp(Date.now());
          setActive(true);
          setSessionTime(0);
          // Polling for data
          intervalRef.current = setInterval(fetchData, 100);
          // Session Timer
          timerRef.current = setInterval(() => setSessionTime(t => t + 1), 1000);
        }
    } catch (e) {
        alert("Could not connect to AI Server. Is 'app.py' running?");
    }
  };

  const stopSession = async () => {
    try {
        // Send POST request with User Email to save data
        await fetch('http://localhost:5000/stop_tracking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: user?.email }) 
        });
    } catch(e) { console.error("Error stopping session:", e) }
    
    setActive(false);
    clearInterval(intervalRef.current);
    clearInterval(timerRef.current);
    navigate('/report'); // Go to report after finishing
  };

  const fetchData = async () => {
    try {
      const res = await fetch('http://localhost:5000/data_feed');
      const json = await res.json();
      setData(json);
      
      if (json.status === 'COUNTDOWN') {
        setFeedback(`Starting in ${json.remaining}...`);
      } else if (json.status === 'ACTIVE') {
        let msg = "MAINTAIN FORM";
        let color = "#76B041"; 

        if (json.RIGHT.feedback) { msg = `RIGHT: ${json.RIGHT.feedback}`; color = "#D32F2F"; }
        else if (json.LEFT.feedback) { msg = `LEFT: ${json.LEFT.feedback}`; color = "#D32F2F"; }
        
        setFeedback(msg);
        const fbBox = document.getElementById('feedback-box');
        if(fbBox) {
            fbBox.style.color = color;
            fbBox.style.borderColor = color;
        }
      }
    } catch (err) { console.error(err); }
  };

  useEffect(() => {
    return () => { clearInterval(intervalRef.current); clearInterval(timerRef.current); }
  }, []);

  const formatTime = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // --- VIEW 1: EXERCISE LIBRARY ---
  const renderLibrary = () => (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
      style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 5%', width: '100%' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '50px' }}>
        <div>
            <h1 style={{ fontSize: '2.5rem', color: '#1A3C34', fontWeight: '800', marginBottom: '10px' }}>
                Exercise Library
            </h1>
            <p style={{ color: '#4A635D', fontSize: '1.1rem' }}>Select a routine to start your guided recovery session.</p>
        </div>
        <button 
            onClick={() => navigate('/')} 
            style={{ 
                background: '#fff', border: '1px solid #ddd', padding: '10px 20px', borderRadius: '30px',
                color: '#4A635D', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px',
                fontWeight: '600', transition: 'all 0.2s'
            }}
        >
            <ArrowLeft size={18} /> Dashboard
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '30px' }}>
        {EXERCISES.map((ex) => (
            <motion.div 
                key={ex.id}
                whileHover={{ y: -5, boxShadow: '0 15px 30px rgba(0,0,0,0.08)' }}
                onClick={() => { setSelectedExercise(ex); setViewMode('DEMO'); }}
                style={{ 
                    background: '#fff', borderRadius: '25px', padding: '30px', 
                    boxShadow: '0 5px 20px rgba(0,0,0,0.04)', cursor: 'pointer',
                    border: ex.recommended ? '2px solid #69B341' : '1px solid transparent',
                    position: 'relative', overflow: 'hidden'
                }}
            >
                {ex.recommended && (
                    <div style={{ 
                        position: 'absolute', top: '20px', right: '20px', 
                        background: '#E8F5E9', color: '#2C5D31', padding: '6px 14px', 
                        borderRadius: '20px', fontSize: '0.75rem', fontWeight: '800',
                        display: 'flex', alignItems: 'center', gap: '6px'
                    }}>
                        <CheckCircle size={14} /> RECOMMENDED
                    </div>
                )}
                
                <div style={{ 
                    width: '60px', height: '60px', borderRadius: '18px', 
                    background: ex.color, marginBottom: '25px', 
                    display: 'flex', alignItems: 'center', justifyContent: 'center' 
                }}>
                    <Dumbbell color={ex.iconColor} size={28} />
                </div>

                <h3 style={{ fontSize: '1.5rem', color: '#1A3C34', marginBottom: '8px', fontWeight: '700' }}>{ex.title}</h3>
                <div style={{ fontSize: '0.85rem', color: '#888', fontWeight: '600', marginBottom: '20px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    {ex.category}
                </div>
                
                <p style={{ color: '#555', fontSize: '0.95rem', marginBottom: '25px', lineHeight: '1.6' }}>{ex.description}</p>
                
                <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: '20px', display: 'flex', gap: '20px', fontSize: '0.9rem', color: '#666', fontWeight: '500' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Timer size={16} /> {ex.duration}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Activity size={16} /> {ex.difficulty}
                    </span>
                </div>
            </motion.div>
        ))}
      </div>
    </motion.div>
  );

  // --- VIEW 2: DEMO & INSTRUCTIONS ---
  const renderDemo = () => (
    <motion.div 
      initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -50 }}
      style={{ height: '100vh', display: 'flex', background: '#F9F7F3' }}
    >
      {/* Left: Info Panel */}
      <div style={{ flex: '0 0 450px', padding: '40px', display: 'flex', flexDirection: 'column', overflowY: 'auto', background: '#fff', borderRight: '1px solid rgba(0,0,0,0.05)', zIndex: 10 }}>
        <button 
            onClick={() => setViewMode('LIBRARY')} 
            style={{ 
                background: 'transparent', border: 'none', color: '#666', 
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', 
                marginBottom: '30px', fontWeight: '600', alignSelf: 'flex-start' 
            }}
        >
            <ArrowLeft size={18} /> Back to Library
        </button>
        
        <h1 style={{ fontSize: '2.5rem', color: '#1A3C34', fontWeight: '800', marginBottom: '10px' }}>{selectedExercise.title}</h1>
        <div style={{ display: 'inline-block', padding: '5px 12px', background: '#f0f0f0', borderRadius: '8px', fontSize: '0.85rem', color: '#666', fontWeight: '600', width: 'fit-content', marginBottom: '30px' }}>
            {selectedExercise.category}
        </div>

        <div style={{ marginBottom: '30px' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#1A3C34', marginBottom: '15px', fontSize: '1.1rem' }}>
                <Info size={20} color="#69B341"/> Instructions
            </h3>
            <ul style={{ listStyle: 'none', padding: 0 }}>
                {selectedExercise.instructions.map((step, i) => (
                    <li key={i} style={{ display: 'flex', gap: '15px', marginBottom: '15px', color: '#555', lineHeight: '1.5', fontSize: '0.95rem' }}>
                        <span style={{ color: '#69B341', fontWeight: 'bold' }}>{i+1}.</span>
                        {step}
                    </li>
                ))}
            </ul>
        </div>

        <div style={{ marginTop: 'auto' }}>
            {/* UPDATED START BUTTON WITH AUTH CHECK */}
            <button 
                onClick={() => { 
                    if (!user) {
                        alert("You must be logged in to start a training session.");
                        navigate('/auth/login');
                        return;
                    }
                    setViewMode('SESSION'); 
                    startSession(); 
                }}
                style={{ 
                    width: '100%', padding: '18px', borderRadius: '50px', border: 'none',
                    background: 'linear-gradient(135deg, #1A3C34 0%, #2C5D31 100%)', 
                    color: '#fff', fontSize: '1.1rem', fontWeight: '700',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                    boxShadow: '0 10px 25px rgba(44, 93, 49, 0.3)', transition: 'transform 0.1s'
                }}
                onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.98)'}
                onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
                <Play size={20} fill="currentColor" /> Start Session
            </button>
        </div>
      </div>

      {/* Right: Demo Video */}
      <div style={{ flex: 1, background: '#000', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <video 
            src="/bicep_demo.mp4" 
            controls 
            autoPlay 
            loop 
            muted 
            playsInline
            style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
          />
          
          <div style={{ position: 'absolute', top: '30px', right: '30px', background: 'rgba(0,0,0,0.6)', padding: '10px 20px', borderRadius: '30px', color: '#fff', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', gap: '10px' }}>
             <Activity size={18} color="#69B341" /> Demo Mode
          </div>
      </div>
    </motion.div>
  );

  // --- VIEW 3: ACTIVE SESSION ---
  const renderSession = () => (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      style={{ height: '100vh', display: 'flex', overflow: 'hidden', background: 'var(--bg-color)' }}
    >
      {/* Sidebar: Metrics */}
      <div style={{ width: '340px', background: '#fff', borderRight: '1px solid #eee', display: 'flex', flexDirection: 'column', zIndex: 10 }}>
        
        {/* Header */}
        <div style={{ padding: '30px', borderBottom: '1px solid #eee', textAlign: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: '#888', fontWeight: '700', letterSpacing: '1px', marginBottom: '8px', textTransform: 'uppercase' }}>
            {selectedExercise?.title}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', color: '#2C5D31', fontSize: '2.5rem', fontWeight: '800' }}>
            <Timer size={32} />
            {formatTime(sessionTime)}
          </div>
        </div>

        {/* Real-time Data */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '25px' }}>
            {['RIGHT', 'LEFT'].map(arm => {
                const metrics = data ? data[arm] : null;
                return (
                <div key={arm} style={{ marginBottom: '25px', background: '#f8f9fa', borderRadius: '18px', padding: '20px', border: '1px solid #eee' }}>
                    <h3 style={{ margin: '0 0 15px 0', color: '#444', fontSize: '0.85rem', fontWeight: '800', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
                        {arm} ARM
                        <span style={{color: '#2C5D31'}}>{metrics ? metrics.stage : '--'}</span>
                    </h3>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '15px' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.7rem', color: '#aaa', fontWeight: '700' }}>REPS</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: '800', color: '#222' }}>{metrics ? metrics.rep_count : '--'}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.7rem', color: '#aaa', fontWeight: '700' }}>ANGLE</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: '800', fontFamily: 'monospace', color: '#222' }}>{metrics ? metrics.angle : '--'}°</div>
                        </div>
                    </div>
                    {/* Visual Bar */}
                    <div style={{ height: '6px', background: '#e0e0e0', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: metrics ? `${(metrics.angle / 180) * 100}%` : '0%', height: '100%', background: '#2C5D31', transition: 'width 0.1s linear' }} />
                    </div>
                </div>
            )})}
        </div>

        {/* Stop Button */}
        <div style={{ padding: '25px', borderTop: '1px solid #eee' }}>
            <button 
                onClick={stopSession}
                style={{ 
                    width: '100%', padding: '16px', borderRadius: '50px', border: 'none', 
                    fontWeight: '800', cursor: 'pointer', fontSize: '1rem',
                    background: '#D32F2F', color: '#fff',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                    boxShadow: '0 8px 20px rgba(211, 47, 47, 0.3)'
                }}
            >
                <StopCircle size={20}/> END SESSION
            </button>
        </div>
      </div>

      {/* Camera Feed */}
      <div style={{ flex: 1, position: 'relative', background: '#333', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            {active ? (
                <img 
                    src={`http://localhost:5000/video_feed?t=${videoTimestamp}`} 
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
                    alt="Stream"
                />
            ) : (
                <div style={{ color: 'white' }}>Initializing Camera...</div>
            )}

            {active && (
                <div id="feedback-box" style={{ 
                    position: 'absolute', bottom: '50px', left: '50%', transform: 'translateX(-50%)',
                    background: 'rgba(255,255,255,0.9)', padding: '15px 40px', borderRadius: '50px',
                    fontSize: '1.5rem', fontWeight: '800', color: '#222', whiteSpace: 'nowrap',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.3)', backdropFilter: 'blur(10px)',
                    display: 'flex', alignItems: 'center', gap: '10px'
                }}>
                   {feedback === 'MAINTAIN FORM' ? <CheckCircle size={28}/> : <AlertCircle size={28}/>} {feedback}
                </div>
            )}
        </div>
      </div>
    </motion.div>
  );

  return (
    <div style={{ background: '#F9F7F3', minHeight: '100vh' }}>
        <AnimatePresence mode="wait">
            {viewMode === 'LIBRARY' && renderLibrary()}
            {viewMode === 'DEMO' && renderDemo()}
            {viewMode === 'SESSION' && renderSession()}
        </AnimatePresence>
    </div>
  );
};

export default Tracker;