import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Icosahedron, MeshDistortMaterial, Environment, Sphere } from '@react-three/drei';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Activity, Shield, Zap, Eye, ArrowRight, Lock } from 'lucide-react';

// --- 3D Hero Element ---
const HeroGraphic = () => {
  const mesh = useRef();
  useFrame((state) => {
    if(mesh.current) {
        mesh.current.rotation.x = state.clock.getElapsedTime() * 0.2;
        mesh.current.rotation.y = state.clock.getElapsedTime() * 0.15;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <group scale={1.2}>
         {/* Core Sphere */}
        <Sphere args={[1, 64, 64]} scale={1.8}>
            <MeshDistortMaterial 
                color="#69B341" 
                envMapIntensity={1} 
                clearcoat={1} 
                clearcoatRoughness={0} 
                metalness={0.1} 
                distort={0.3} 
                speed={2}
            />
        </Sphere>
        {/* Wireframe Outer Shell */}
        <Icosahedron args={[1, 2]} ref={mesh} scale={2.6}>
            <meshStandardMaterial color="#2C5D31" wireframe transparent opacity={0.3} />
        </Icosahedron>
      </group>
      <Environment preset="city" />
    </Float>
  );
};

// --- Reusable Components ---
const SectionTitle = ({ title, subtitle }) => (
    <div style={{ textAlign: 'center', marginBottom: '60px' }}>
        <h2 style={{ fontSize: '2.5rem', color: '#1A3C34', fontWeight: '800', marginBottom: '15px' }}>{title}</h2>
        <p style={{ color: '#4A635D', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto' }}>{subtitle}</p>
    </div>
);

const BenefitCard = ({ icon: Icon, title, text }) => (
    <motion.div 
        whileHover={{ y: -10 }}
        style={{ 
            background: '#fff', 
            padding: '40px 30px', 
            borderRadius: '20px', 
            boxShadow: '0 10px 30px rgba(0,0,0,0.04)',
            border: '1px solid rgba(0,0,0,0.03)'
        }}
    >
        <div style={{ 
            width: '60px', height: '60px', borderRadius: '50%', 
            background: 'rgba(105, 179, 65, 0.1)', display: 'flex', 
            alignItems: 'center', justifyContent: 'center', marginBottom: '20px' 
        }}>
            <Icon size={28} color="#69B341" />
        </div>
        <h3 style={{ color: '#1A3C34', fontSize: '1.3rem', marginBottom: '10px' }}>{title}</h3>
        <p style={{ color: '#4A635D', lineHeight: '1.6' }}>{text}</p>
    </motion.div>
);

const StepCard = ({ num, title, desc }) => (
    <div style={{ flex: 1, textAlign: 'left', padding: '0 20px', position: 'relative' }}>
        <div style={{ fontSize: '4rem', fontWeight: '900', color: 'rgba(105, 179, 65, 0.15)', position: 'absolute', top: '-30px', left: '10px', zIndex: 0 }}>{num}</div>
        <h3 style={{ position: 'relative', zIndex: 1, color: '#1A3C34', fontSize: '1.5rem', marginBottom: '10px' }}>{title}</h3>
        <p style={{ position: 'relative', zIndex: 1, color: '#4A635D' }}>{desc}</p>
    </div>
);

const Dashboard = () => {
  const navigate = useNavigate();

  return (
    <div style={{ width: '100%', background: '#F9F7F3', overflowX: 'hidden' }}>
      
      {/* 1. HERO SECTION */}
      <section style={{ 
          minHeight: '90vh', display: 'flex', alignItems: 'center', 
          padding: '0 5%', position: 'relative' 
      }}>
        <div style={{ flex: 1, zIndex: 2 }}>
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}>
                <div style={{ 
                    display: 'inline-block', padding: '8px 16px', borderRadius: '30px', 
                    background: 'rgba(44, 93, 49, 0.08)', color: '#2C5D31', fontWeight: '600', 
                    marginBottom: '25px', fontSize: '0.9rem' 
                }}>
                    AI-POWERED REHABILITATION
                </div>
                <h1 style={{ fontSize: '4.5rem', fontWeight: '900', color: '#1A3C34', lineHeight: '1.1', marginBottom: '25px' }}>
                    Precision Recovery <br/>
                    <span style={{ color: '#69B341' }}>In Your Control.</span>
                </h1>
                <p style={{ fontSize: '1.25rem', color: '#4A635D', maxWidth: '550px', marginBottom: '40px', lineHeight: '1.6' }}>
                    Advanced Computer Vision for posture correction and injury prevention. 
                    Real-time feedback, anytime, anywhere.
                </p>
                
                <div style={{ display: 'flex', gap: '20px' }}>
                    {/* UPDATED: Removed "Login" button, repurposed "Create Account" to "Start Recovery" -> /track */}
                    <button 
                        onClick={() => navigate('/track')}
                        style={{ 
                            padding: '16px 40px', borderRadius: '50px', border: 'none', 
                            background: '#2C5D31', color: '#fff', fontSize: '1.1rem', fontWeight: '700',
                            cursor: 'pointer', boxShadow: '0 10px 25px rgba(44, 93, 49, 0.3)',
                            transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: '10px'
                        }}
                    >
                        Start Recovery <ArrowRight size={20} />
                    </button>
                </div>
            </motion.div>
        </div>

        {/* 3D Visual */}
        <div style={{ flex: 1, height: '600px', position: 'relative' }}>
            <Canvas camera={{ position: [0, 0, 5] }}>
                <ambientLight intensity={0.5} />
                <HeroGraphic />
            </Canvas>
            
            {/* Visual Flair Card (Non-Functional) */}
            <motion.div 
                initial={{ opacity: 0, x: 50 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5, duration: 0.8 }}
                style={{
                    position: 'absolute', bottom: '20%', right: '10%',
                    background: 'rgba(255, 255, 255, 0.9)', padding: '20px', borderRadius: '15px',
                    boxShadow: '0 20px 40px rgba(0,0,0,0.1)', backdropFilter: 'blur(10px)',
                    display: 'flex', alignItems: 'center', gap: '15px', zIndex: 10
                }}
            >
                <div style={{ background: '#E8F5E9', padding: '12px', borderRadius: '50%' }}>
                    <Activity color="#2C5D31" size={24} />
                </div>
                <div>
                    <div style={{ fontWeight: 'bold', color: '#1A3C34' }}>98% Accuracy</div>
                    <div style={{ fontSize: '0.8rem', color: '#69B341' }}>Pose Estimation Active</div>
                </div>
            </motion.div>
        </div>
      </section>


      {/* 2. ABOUT & BENEFITS */}
      <section style={{ padding: '100px 5%' }}>
        <SectionTitle 
            title="Why PhysioCheck?" 
            subtitle="We bridge the gap between clinical therapy and home exercise using medical-grade AI analysis."
        />
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '30px', maxWidth: '1200px', margin: '0 auto' }}>
            <BenefitCard 
                icon={Eye} 
                title="Computer Vision" 
                text="Our AI analyzes body posture and joint angles in real-time, detecting micro-errors invisible to the naked eye."
            />
            <BenefitCard 
                icon={Shield} 
                title="Injury Prevention" 
                text="Get instant alerts when you over-extend or break form, significantly reducing the risk of strain or injury."
            />
            <BenefitCard 
                icon={Zap} 
                title="Instant Feedback" 
                text="No more guessing. Receive corrective guidance instantly on your screen as you perform each repetition."
            />
            <BenefitCard 
                icon={Lock} 
                title="Private & Secure" 
                text="Your data is encrypted. Video processing happens securely, ensuring your privacy is never compromised."
            />
        </div>
      </section>


      {/* 3. HOW IT WORKS */}
      <section style={{ padding: '100px 5%', background: '#fff' }}>
         <SectionTitle 
            title="How It Works" 
            subtitle="Professional-grade analysis with zero hardware. Just you and your camera."
        />
        
        <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'center', gap: '50px', maxWidth: '1000px', margin: '0 auto', flexWrap: 'wrap' }}>
            <StepCard 
                num="01" 
                title="Set Up" 
                desc="Place your device on a stable surface. Ensure your full body is visible in the camera frame."
            />
            <StepCard 
                num="02" 
                title="Analyze" 
                desc="Our AI builds a 33-point skeletal wireframe of your body to track movement in 3D space."
            />
            <StepCard 
                num="03" 
                title="Correct" 
                desc="Follow visual guides. If your form deviates, the system alerts you to correct it immediately."
            />
        </div>
      </section>


      {/* 4. CTA BANNER */}
      <section style={{ padding: '80px 5%' }}>
        <div style={{ 
            background: 'linear-gradient(135deg, #1A3C34 0%, #2C5D31 100%)', 
            borderRadius: '30px', padding: '80px 40px', textAlign: 'center', color: '#fff',
            maxWidth: '1200px', margin: '0 auto', boxShadow: '0 20px 50px rgba(26, 60, 52, 0.2)'
        }}>
            <h2 style={{ fontSize: '3rem', fontWeight: '800', marginBottom: '20px' }}>Start Your Recovery Journey</h2>
            <p style={{ fontSize: '1.2rem', opacity: 0.9, maxWidth: '600px', margin: '0 auto 40px auto' }}>
                Join thousands of users trusting PhysioCheck for safe, effective, and smart rehabilitation.
            </p>
            {/* UPDATED: Direct Link to Tracker */}
            <button 
                onClick={() => navigate('/track')}
                style={{ 
                    padding: '18px 45px', borderRadius: '50px', border: 'none', 
                    background: '#fff', color: '#1A3C34', fontSize: '1.1rem', fontWeight: '800',
                    cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '10px'
                }}
            >
                Start Recovery <ArrowRight size={20} />
            </button>
        </div>
      </section>


      {/* 5. FOOTER */}
      <footer style={{ padding: '50px 5%', textAlign: 'center', borderTop: '1px solid rgba(0,0,0,0.05)' }}>
        <h3 style={{ color: '#1A3C34', fontWeight: '800', fontSize: '1.5rem', marginBottom: '20px' }}>
            PHYSIO<span style={{ color: '#69B341' }}>CHECK</span>
        </h3>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '30px', marginBottom: '30px', color: '#4A635D', fontSize: '0.9rem' }}>
            <span>About Us</span>
            <span>Privacy Policy</span>
            <span>Terms of Service</span>
            <span>Contact Support</span>
        </div>
        <div style={{ color: '#aaa', fontSize: '0.8rem' }}>
            © 2024 PhysioCheck AI. All rights reserved.
        </div>
      </footer>

    </div>
  );
};

export default Dashboard;