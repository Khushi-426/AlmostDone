import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Timer, ArrowLeft, StopCircle, CheckCircle, 
  Activity, AlertCircle, Play, Dumbbell, Wifi, WifiOff, User, Mic 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from './context/AuthContext'; 
import { io } from 'socket.io-client';
import AICoach from './components/AICoach';

// --- MOCK DATA: EXERCISES ---
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
  const { user } = useAuth();
  
  // --- STATES ---
  const [viewMode, setViewMode] = useState('LIBRARY'); 
  const [selectedExercise, setSelectedExercise] = useState(null);
  
  const [active, setActive] = useState(false);
  const [data, setData] = useState(null);
  const [sessionTime, setSessionTime] = useState(0);
  const [feedback, setFeedback] = useState("Initializing...");
  const [videoTimestamp, setVideoTimestamp] = useState(Date.now());
  const [connectionStatus, setConnectionStatus] = useState('DISCONNECTED');
  
  const [calibrationProgress, setCalibrationProgress] = useState(0);
  const [countdownValue, setCountdownValue] = useState(null);

  const [socket, setSocket] = useState(null);
  const timerRef = useRef(null);
  
  // --- 1. SETUP SOCKET ---
  useEffect(() => {
    const newSocket = io('http://localhost:5000');
    setSocket(newSocket);

    newSocket.on('connect', () => {
        console.log("WebSocket Connected");
        setConnectionStatus('CONNECTED');
    });

    newSocket.on('disconnect', () => {
        setConnectionStatus('DISCONNECTED');
    });

    newSocket.on('session_stopped', () => {
         navigate('/report');
    });

    newSocket.on('workout_update', (json) => {
        setData(json);
        handleWorkoutUpdate(json);
    });

    return () => {
        newSocket.close();
        window.speechSynthesis.cancel();
    };
  }, [navigate]); 

  // --- 2. LOGIC HANDLER ---
  const handleWorkoutUpdate = (json) => {
      // CALIBRATION
      if (json.status === 'CALIBRATION') {
          setFeedback(json.calibration?.message || "Calibrating...");
          setCalibrationProgress(json.calibration?.progress || 0);
          setCountdownValue(null);
      } 
      // COUNTDOWN
      else if (json.status === 'COUNTDOWN') {
          setFeedback("Get Ready!");
          setCountdownValue(json.remaining);
          setCalibrationProgress(100);
      } 
      // ACTIVE
      else if (json.status === 'ACTIVE') {
          setCountdownValue(null);
          
          const rightMsg = json.RIGHT?.feedback || "";
          const leftMsg = json.LEFT?.feedback || "";
          
          // Helper to check if a message is an actual "Problem"
          const isProblem = (msg) => {
              if (!msg) return false;
              const safeMessages = ["Maintain Form", "Initializing...", "Looking Strong!", "Great Control!", "Perfect Form!", "Keep Pushing!", "Solid Rep!", "Nice Pace!"];
              return !safeMessages.includes(msg);
          };

          let displayMsg = "MAINTAIN FORM";
          let color = "#76B041"; // Green

          // PRIORITY LOGIC
          if (isProblem(leftMsg)) {
              displayMsg = `LEFT: ${leftMsg}`;
              color = "#D32F2F"; // Red
          } 
          else if (isProblem(rightMsg)) {
              displayMsg = `RIGHT: ${rightMsg}`;
              color = "#D32F2F"; // Red
          }
          else {
              if (rightMsg !== "Maintain Form" && rightMsg !== "") displayMsg = rightMsg;
              else if (leftMsg !== "Maintain Form" && leftMsg !== "") displayMsg = leftMsg;
          }
          
          setFeedback(displayMsg);
          
          const fbBox = document.getElementById('feedback-box');
          if(fbBox) {
              fbBox.style.color = color;
              fbBox.style.borderColor = color;
          }
      }
  };

  // --- 3. SESSION CONTROL ---
  const startSession = async () => {
    try {
        setConnectionStatus('CONNECTING');
        
        setFeedback("Aligning...");
        setCalibrationProgress(0);
        setCountdownValue(null);
        setData(prev => ({ ...prev, status: 'CALIBRATION' }));

        const res = await fetch('http://localhost:5000/start_tracking');
        if (!res.ok) throw new Error('Server error');
        
        const json = await res.json();
        if (json.status === 'success') {
          setVideoTimestamp(Date.now());
          setActive(true);
          setSessionTime(0);
          
          if(timerRef.current) clearInterval(timerRef.current);
          timerRef.current = setInterval(() => setSessionTime(t => t + 1), 1000);
        }
    } catch (e) {
        alert("Could not connect to AI Server.");
        setConnectionStatus('DISCONNECTED');
    }
  };

  const stopSession = () => {
    if(socket) {
        socket.emit('stop_session', { 
            email: user?.email,
            exercise: selectedExercise?.title || 'Freestyle' 
        });
    }
    setActive(false);
    clearInterval(timerRef.current);
  };

  // --- 4. BOT INTERACTION HANDLERS ---
  const handleListeningChange = (isListening) => {
      if(socket) {
          socket.emit('toggle_listening', { active: isListening });
      }
  };

  const handleBotCommand = (action) => {
      console.log("Tracker Received Command:", action);
      if (action === 'STOP') {
          stopSession();
      } 
      else if (action === 'RECALIBRATE') {
          startSession(); 
      }
  };

  const formatTime = (s) => {
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // --- RENDER HELPERS ---
  const renderLibrary = () => (
    <motion.div 
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
      style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 5%', width: '100%' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '50px' }}>
        <div>
            <h1 style={{ fontSize: '2.5rem', color: '#1A3C34', fontWeight: '800', marginBottom: '10px' }}>Exercise Library</h1>
            <p style={{ color: '#4A635D', fontSize: '1.1rem' }}>Select a routine to start your guided recovery session.</p>
        </div>
        <button onClick={() => navigate('/')} style={{ background: '#fff', border: '1px solid #ddd', padding: '10px 20px', borderRadius: '30px', color: '#4A635D', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600' }}>
            <ArrowLeft size={18} /> Dashboard
        </button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '30px' }}>
        {EXERCISES.map((ex) => (
            <motion.div 
                key={ex.id}
                whileHover={{ y: -5, boxShadow: '0 15px 30px rgba(0,0,0,0.08)' }}
                onClick={() => { setSelectedExercise(ex); setViewMode('DEMO'); }}
                style={{ background: '#fff', borderRadius: '25px', padding: '30px', boxShadow: '0 5px 20px rgba(0,0,0,0.04)', cursor: 'pointer', border: ex.recommended ? '2px solid #69B341' : '1px solid transparent', position: 'relative' }}
            >
                {ex.recommended && <div style={{ position: 'absolute', top: '20px', right: '20px', background: '#E8F5E9', color: '#2C5D31', padding: '6px 14px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '6px' }}><CheckCircle size={14} /> RECOMMENDED</div>}
                <div style={{ width: '60px', height: '60px', borderRadius: '18px', background: ex.color, marginBottom: '25px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Dumbbell color={ex.iconColor} size={28} /></div>
                <h3 style={{ fontSize: '1.5rem', color: '#1A3C34', marginBottom: '8px', fontWeight: '700' }}>{ex.title}</h3>
                <div style={{ fontSize: '0.85rem', color: '#888', fontWeight: '600', marginBottom: '20px', textTransform: 'uppercase' }}>{ex.category}</div>
                <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: '20px', display: 'flex', gap: '20px', fontSize: '0.9rem', color: '#666', fontWeight: '500' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Timer size={16} /> {ex.duration}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Activity size={16} /> {ex.difficulty}</span>
                </div>
            </motion.div>
        ))}
      </div>
    </motion.div>
  );

  const renderDemo = () => (
    <motion.div initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -50 }} style={{ height: '100vh', display: 'flex', background: '#F9F7F3' }}>
      <div style={{ flex: '0 0 450px', padding: '40px', display: 'flex', flexDirection: 'column', background: '#fff', borderRight: '1px solid rgba(0,0,0,0.05)', zIndex: 10 }}>
        <button onClick={() => setViewMode('LIBRARY')} style={{ background: 'transparent', border: 'none', color: '#666', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '30px', fontWeight: '600', alignSelf: 'flex-start' }}><ArrowLeft size={18} /> Back</button>
        <h1 style={{ fontSize: '2.5rem', color: '#1A3C34', fontWeight: '800', marginBottom: '10px' }}>{selectedExercise.title}</h1>
        <div style={{ display: 'inline-block', padding: '5px 12px', background: '#f0f0f0', borderRadius: '8px', fontSize: '0.85rem', color: '#666', fontWeight: '600', width: 'fit-content', marginBottom: '20px' }}>{selectedExercise.category}</div>
        
        {/* --- [UPDATED] VOICE BOT INSTRUCTIONS --- */}
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '15px', margin: '10px 0', border: '1px solid #eee' }}>
            <h3 style={{ fontSize: '1rem', color: '#1A3C34', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Mic size={18} color="#2196F3" /> Voice Command Guide
            </h3>
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '12px', lineHeight: '1.4' }}>
                Control your session hands-free. Show the V-Sign to activate listening.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem', color: '#444', fontWeight: '500' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '8px', borderRadius: '8px', border: '1px solid #eee' }}>
                    <span style={{ background: '#E3F2FD', color: '#2196F3', padding: '4px 8px', borderRadius: '6px', fontWeight: 'bold' }}>✌️ V-SIGN</span>
                    <span>Hold "Peace" sign to wake up the bot</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '8px', borderRadius: '8px', border: '1px solid #eee' }}>
                    <span style={{ background: '#E8F5E9', color: '#2C5D31', padding: '4px 8px', borderRadius: '6px', fontWeight: 'bold' }}>🗣 COMMANDS</span>
                    <span>"Recalibrate", "Stop", "Align Me"</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '8px', borderRadius: '8px', border: '1px solid #eee' }}>
                    <span style={{ background: '#FFF3E0', color: '#EF6C00', padding: '4px 8px', borderRadius: '6px', fontWeight: 'bold' }}>💬 CHAT</span>
                    <span>"What's my best rep?", "History?"</span>
                </div>
            </div>
        </div>

        <div style={{ marginTop: 'auto' }}>
            <button 
                onClick={() => { 
                    if (!user) { alert("Please login to start."); navigate('/auth/login'); return; }
                    setViewMode('SESSION'); startSession(); 
                }}
                style={{ width: '100%', padding: '18px', borderRadius: '50px', border: 'none', background: 'linear-gradient(135deg, #1A3C34 0%, #2C5D31 100%)', color: '#fff', fontSize: '1.1rem', fontWeight: '700', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', boxShadow: '0 10px 25px rgba(44, 93, 49, 0.3)' }}
            >
                <Play size={20} fill="currentColor" /> Start Session
            </button>
        </div>
      </div>
      <div style={{ flex: 1, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <video src="/bicep_demo.mp4" controls autoPlay loop muted playsInline style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
      </div>
    </motion.div>
  );

  const renderSession = () => (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ height: '100vh', display: 'flex', overflow: 'hidden', background: 'var(--bg-color)' }}>
      {/* Sidebar Split */}
      <div style={{ width: '340px', background: '#fff', borderRight: '1px solid #eee', display: 'flex', flexDirection: 'column', zIndex: 10 }}>
        
        {/* UPPER HALF: STATS */}
        <div style={{ flex: '0 0 50%', display: 'flex', flexDirection: 'column', overflowY: 'auto', borderBottom: '2px solid #f0f0f0' }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #eee', textAlign: 'center' }}>
                <div style={{ fontSize: '0.8rem', color: '#888', fontWeight: '700', letterSpacing: '1px', marginBottom: '8px', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{selectedExercise?.title}</span>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        {connectionStatus === 'CONNECTED' ? <Wifi size={16} color="#69B341" title="Connected" /> : <WifiOff size={16} color="#D32F2F" title="Disconnected" />}
                    </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', color: '#2C5D31', fontSize: '2.5rem', fontWeight: '800' }}>
                    <Timer size={32} /> {formatTime(sessionTime)}
                </div>
            </div>
            <div style={{ padding: '15px' }}>
                {['RIGHT', 'LEFT'].map(arm => {
                    const metrics = data ? data[arm] : null;
                    return (
                    <div key={arm} style={{ marginBottom: '10px', background: '#f8f9fa', borderRadius: '18px', padding: '15px', border: '1px solid #eee' }}>
                        <h3 style={{ margin: '0 0 10px 0', color: '#444', fontSize: '0.75rem', fontWeight: '800', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #eee', paddingBottom: '8px' }}>
                            {arm} ARM <span style={{color: '#2C5D31'}}>{metrics ? metrics.stage : '--'}</span>
                        </h3>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '10px' }}>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.65rem', color: '#aaa', fontWeight: '700' }}>REPS</div>
                                <div style={{ fontSize: '1.8rem', fontWeight: '800', color: '#222' }}>{metrics ? metrics.rep_count : '--'}</div>
                            </div>
                            <div style={{ textAlign: 'center' }}>
                                <div style={{ fontSize: '0.65rem', color: '#aaa', fontWeight: '700' }}>ANGLE</div>
                                <div style={{ fontSize: '1.8rem', fontWeight: '800', fontFamily: 'monospace', color: '#222' }}>{metrics ? metrics.angle : '--'}°</div>
                            </div>
                        </div>
                    </div>
                )})}
            </div>
            <div style={{ padding: '0 20px 20px 20px', marginTop: 'auto' }}>
                <button onClick={stopSession} style={{ width: '100%', padding: '12px', borderRadius: '50px', border: 'none', fontWeight: '800', cursor: 'pointer', fontSize: '0.9rem', background: '#D32F2F', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', boxShadow: '0 8px 20px rgba(211, 47, 47, 0.3)' }}>
                    <StopCircle size={20}/> END SESSION
                </button>
            </div>
        </div>

        {/* LOWER HALF: AI ROBOT */}
        <div style={{ flex: '1', overflow: 'hidden', position: 'relative' }}>
            <AICoach 
                data={data}
                feedback={feedback}
                exerciseName={selectedExercise?.title || 'Workout'}
                active={active}
                gesture={data?.gesture}
                onCommand={handleBotCommand} 
                onListeningChange={handleListeningChange}
                userEmail={user?.email} 
            />
        </div>
      </div>

      {/* Camera Feed */}
      <div style={{ flex: 1, position: 'relative', background: '#222', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
        <div style={{ width: '100%', height: '100%', position: 'relative' }}>
            {active ? (
                <img src={`http://localhost:5000/video_feed?t=${videoTimestamp}`} style={{ width: '100%', height: '100%', objectFit: 'contain' }} alt="Stream" />
            ) : (
                <div style={{ color: 'white', position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Initializing Camera...</div>
            )}

            {data?.status === 'CALIBRATION' && (
                <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    width: '300px', height: '500px', pointerEvents: 'none', opacity: 0.6,
                    border: '4px dashed rgba(255,255,255,0.5)', borderRadius: '150px 150px 0 0',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <User size={120} color="rgba(255,255,255,0.5)" />
                    <div style={{ position: 'absolute', bottom: '-40px', color: '#fff', background: 'rgba(0,0,0,0.5)', padding: '5px 10px', borderRadius: '10px' }}>
                        Align Here
                    </div>
                </div>
            )}
            
            <AnimatePresence>
                {data?.status === 'CALIBRATION' && (
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        style={{
                            position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.1)', 
                            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start',
                            paddingTop: '50px'
                        }}
                    >
                        <h2 style={{ color: '#fff', fontSize: '2rem', marginBottom: '20px', textShadow: '0 2px 10px rgba(0,0,0,0.8)' }}>
                            {feedback}
                        </h2>
                        <div style={{ width: '60%', height: '12px', background: 'rgba(255,255,255,0.2)', borderRadius: '6px', overflow: 'hidden' }}>
                            <motion.div 
                                animate={{ width: `${calibrationProgress}%` }}
                                style={{ height: '100%', background: '#00E676' }}
                            />
                        </div>
                    </motion.div>
                )}

                {data?.status === 'COUNTDOWN' && (
                    <motion.div
                        initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 1.5, opacity: 0 }}
                        key={countdownValue}
                        style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.2)' }}
                    >
                        <div style={{ fontSize: '10rem', fontWeight: '900', color: '#fff', textShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>{countdownValue}</div>
                    </motion.div>
                )}

                {data?.status === 'ACTIVE' && (
                    <motion.div initial={{ y: 50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} id="feedback-box" style={{ position: 'absolute', bottom: '50px', left: '50%', transform: 'translateX(-50%)', background: 'rgba(255,255,255,0.95)', padding: '15px 40px', borderRadius: '50px', fontSize: '1.5rem', fontWeight: '800', color: '#222', whiteSpace: 'nowrap', boxShadow: '0 20px 40px rgba(0,0,0,0.3)', backdropFilter: 'blur(10px)', display: 'flex', alignItems: 'center', gap: '15px', border: '3px solid transparent', transition: 'all 0.3s ease' }}>
                       {feedback.includes('MAINTAIN') || feedback.includes('Looking') || feedback.includes('Great') ? <CheckCircle size={28}/> : <AlertCircle size={28}/>} 
                       {feedback}
                    </motion.div>
                )}
            </AnimatePresence>
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