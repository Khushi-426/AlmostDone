import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchAICommentary } from '../services/aiService';
import { Mic } from 'lucide-react';

// --- 3D IMPORTS ---
import { Canvas, useFrame } from '@react-three/fiber';
import { 
    Environment, 
    Float, 
    ContactShadows, 
    Sphere, 
    MeshDistortMaterial 
} from '@react-three/drei';
import * as THREE from 'three';

const Avatar3D = ({ state }) => {
    const mesh = useRef();
    const light = useRef();
    
    useFrame((state, delta) => {
        if (!mesh.current) return;
        
        if (state === 'THINKING') {
            mesh.current.distort = THREE.MathUtils.lerp(mesh.current.distort, 0.85, 0.1);
            mesh.current.speed = THREE.MathUtils.lerp(mesh.current.speed, 5, 0.1);
        } else {
            mesh.current.distort = THREE.MathUtils.lerp(mesh.current.distort, 0.5, 0.1);
            mesh.current.speed = THREE.MathUtils.lerp(mesh.current.speed, 3, 0.1);
        }
    });

    const colors = {
        IDLE: "#69B341",       
        LISTENING: "#2196F3", 
        SPEAKING: "#00E676",   
        THINKING: "#FF9800",  
        ERROR: "#D32F2F"       
    };

    const activeColor = new THREE.Color(colors[state] || colors.IDLE);

    return (
        <group>
            <Float speed={2.5} rotationIntensity={1.5} floatIntensity={1.5}>
                <Sphere args={[1.2, 64, 64]} ref={mesh}>
                    <MeshDistortMaterial 
                        color={activeColor} 
                        envMapIntensity={1.0} 
                        clearcoat={1} 
                        clearcoatRoughness={0.2} 
                        metalness={0.2} 
                        roughness={0.3} 
                        distort={0.5}   
                        speed={3}       
                    />
                </Sphere>
                <pointLight ref={light} position={[0, 0, 0]} intensity={2.5} distance={6} color={activeColor} />
            </Float>
            <ContactShadows opacity={0.4} scale={12} blur={3.5} far={10} resolution={256} color="#1A3C34" />
        </group>
    );
};

const AICoach = ({ data, feedback, exerciseName, active, gesture, onCommand, onListeningChange, userEmail }) => {
    const [message, setMessage] = useState("Standing by...");
    const [botState, setBotState] = useState('IDLE'); 
    const [micError, setMicError] = useState(false);
    
    const recognitionRef = useRef(null);
    const isListeningForWakeWord = useRef(true);
    const isBotSpeaking = useRef(false);
    const lastGestureRef = useRef(null);
    const listenTimeoutRef = useRef(null);
    const lastFeedbackRef = useRef("");

    // --- 1. SEAMLESS TTS LOGIC ---
    const speak = (text, onEndCallback = null) => {
        if (!window.speechSynthesis) return;
        
        isBotSpeaking.current = true;
        window.speechSynthesis.cancel();
        setBotState('SPEAKING');
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.1; 
        
        utterance.onend = () => {
            isBotSpeaking.current = false;
            setBotState(prevState => {
                if (prevState === 'SPEAKING') return 'IDLE';
                return prevState;
            });
            if (onEndCallback) onEndCallback();
            else if (!listenTimeoutRef.current) isListeningForWakeWord.current = true;
        };
        
        utterance.onerror = () => {
            isBotSpeaking.current = false;
            setBotState('IDLE');
        };

        window.speechSynthesis.speak(utterance);
    };

    // --- 2. ACTIVATION MODES ---
    const activateListeningMode = () => {
        console.log("🎤 Listening Mode ACTIVATED");
        if (isBotSpeaking.current) {
            window.speechSynthesis.cancel();
            isBotSpeaking.current = false;
        }

        isListeningForWakeWord.current = false;
        if (onListeningChange) onListeningChange(true); 
        
        setBotState('LISTENING');
        setMessage("Listening...");
        
        speak("Yes?", () => {
             setBotState('LISTENING');
             startSilenceTimer(); 
        });
    };

    const deactivateListeningMode = () => {
        console.log("🚫 Listening Mode OFF");
        if (listenTimeoutRef.current) clearTimeout(listenTimeoutRef.current);
        listenTimeoutRef.current = null;
        
        isListeningForWakeWord.current = true;
        setBotState('IDLE');
        if (onListeningChange) onListeningChange(false); 
    };

    const startSilenceTimer = () => {
        if (listenTimeoutRef.current) clearTimeout(listenTimeoutRef.current);
        listenTimeoutRef.current = setTimeout(() => {
            speak("Resuming exercise.", () => deactivateListeningMode());
        }, 7000); 
    };

    // --- 3. SPEECH RECOGNITION ---
    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setMicError(true);
            setMessage("No Voice Support");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true; 
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => setMicError(false);
        recognition.onerror = (e) => {
            if (e.error === 'not-allowed') {
                setMicError(true);
                setBotState('ERROR');
                setMessage("Mic Access Denied");
            }
        };

        recognition.onresult = async (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
            console.log("Heard:", transcript);

            const isPriority = isStopCommand(transcript);

            if (isPriority) {
                if (isBotSpeaking.current) {
                    window.speechSynthesis.cancel();
                    isBotSpeaking.current = false;
                }
            } else {
                if (isBotSpeaking.current) return;
            }

            if (!isListeningForWakeWord.current) {
                if (listenTimeoutRef.current) clearTimeout(listenTimeoutRef.current);
            }

            if (isStopCommand(transcript)) { 
                await executeCommand("stop", "Stopping session."); 
                return; 
            }
            
            if (isListeningForWakeWord.current) {
                if (transcript.includes("madona") || transcript.includes("madonna") || transcript.includes("hey bot")) {
                    activateListeningMode();
                }
            } 
            else {
                await processSmartQuery(transcript);
            }
        };

        recognition.onend = () => {
            if(active && !micError) {
                try { recognition.start(); } catch(e){}
            }
        };

        recognitionRef.current = recognition;
        if (active) {
            try { recognition.start(); } catch(e){}
        }

        return () => { 
            if (recognitionRef.current) recognitionRef.current.stop(); 
            if (listenTimeoutRef.current) clearTimeout(listenTimeoutRef.current);
        };
    }, [active]);

    // --- 4. GESTURE TRIGGER (FIXED) ---
    useEffect(() => {
        // [FIX] Removed "botState === IDLE" check. Now FORCE triggers if V_SIGN is seen.
        if (gesture === 'V_SIGN' && lastGestureRef.current !== 'V_SIGN') {
            console.log("✌️ V-Sign Triggered (FORCE)");
            activateListeningMode();
        }
        lastGestureRef.current = gesture;
    }, [gesture]);

    const isStopCommand = (text) => 
        text.includes("stop") || text.includes("quit") || text.includes("end session") || text.includes("finish");

    const executeCommand = async (cmd, reply) => {
        if (onCommand) onCommand(cmd.toUpperCase());
        speak(reply, () => deactivateListeningMode());
    };

    const processSmartQuery = async (text) => {
        setBotState('THINKING');
        
        try {
            const context = { 
                email: userEmail, 
                exercise: exerciseName, 
                reps: (data?.LEFT?.rep_count || 0) + (data?.RIGHT?.rep_count || 0) 
            };
            
            const aiResponse = await fetchAICommentary(context, text);
            console.log("🤖 GEMINI REPLIED:", aiResponse);
            
            if (aiResponse.includes("ACTION: RECALIBRATE")) {
                executeCommand("recalibrate", "On it. Recalibrating.");
            } else if (aiResponse.includes("ACTION: STOP")) {
                executeCommand("stop", "Stopping session.");
            } else if (aiResponse.includes("ACTION: STATS")) {
                const r = data?.RIGHT?.rep_count || 0;
                const l = data?.LEFT?.rep_count || 0;
                speak(`You have done ${r+l} reps total.`, () => deactivateListeningMode());
            } else {
                speak(aiResponse, () => deactivateListeningMode());
            }
        } catch (error) {
            console.error("AI Connection Error:", error);
            speak("I'm having trouble connecting to my brain.", () => deactivateListeningMode());
        }
    };

    useEffect(() => {
        if (!active || botState !== 'IDLE' || !isListeningForWakeWord.current || isBotSpeaking.current) return;
        const currentFeedback = feedback;
        if (currentFeedback && currentFeedback !== lastFeedbackRef.current) {
             lastFeedbackRef.current = currentFeedback;
             if (!currentFeedback.includes("MAINTAIN") && !currentFeedback.includes("Initializing")) {
                 setMessage(currentFeedback);
                 speak(currentFeedback);
             }
        }
    }, [data, feedback, active]);

    return (
        <div style={{ height: '100%', width: '100%', background: 'linear-gradient(180deg, #F0F8FF 0%, #E6F4EA 100%)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', borderTop: '2px solid #eee' }}>
            
            <div style={{ width: '250px', height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Canvas shadows dpr={[1, 2]} camera={{ position: [0, 0, 4.5], fov: 50 }}>
                    <ambientLight intensity={0.7} />
                    <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1.5} castShadow />
                    <Environment preset="city" />
                    <Avatar3D state={micError ? 'ERROR' : botState} />
                </Canvas>
            </div>

            <AnimatePresence mode='wait'>
                <motion.div key={message} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={{ background: '#fff', padding: '12px 18px', borderRadius: '20px', boxShadow: '0 4px 15px rgba(0,0,0,0.05)', marginTop: '0px', maxWidth: '90%', border: '1px solid #e1e1e1', zIndex: 10 }}>
                    <p style={{ margin: 0, color: '#1A3C34', fontWeight: '600', fontSize: '0.9rem' }}>"{message}"</p>
                </motion.div>
            </AnimatePresence>

            <div style={{ position: 'absolute', bottom: '10px', right: '10px', fontSize: '0.65rem', color: micError ? '#D32F2F' : '#aaa', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Mic size={10} color={botState === 'LISTENING' ? '#2196F3' : '#aaa'} /> 
                {micError ? "MIC ACCESS DENIED" : (botState === 'LISTENING' ? 'LISTENING (7s)' : 'AI ACTIVE')}
            </div>
            {gesture === 'V_SIGN' && <div style={{ position: 'absolute', top: '10px', left: '10px', background: '#E3F2FD', color: '#2196F3', padding: '4px 8px', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 'bold' }}>✌️ V-Sign</div>}
        </div>
    );
};

export default AICoach;