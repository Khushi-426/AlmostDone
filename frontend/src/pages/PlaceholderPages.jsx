import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { User, Stethoscope, Mail, Lock, ShieldCheck } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import './Auth.css';

// --- CUSTOM GOOGLE BUTTON (Uses new CSS class) ---
const GoogleButton = ({ onClick }) => (
  <button type="button" onClick={onClick} className="google-btn">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
    Continue with Google
  </button>
);

export const Login = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [role, setRole] = useState('patient');
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await axios.post('http://127.0.0.1:5000/api/auth/google', {
          token: tokenResponse.access_token,
          role: role
        });
        login(res.data);
        navigate('/profile/overview');
      } catch (err) {
        setError('Google Login Failed');
      }
    },
    onError: () => setError('Google Login Failed'),
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('http://127.0.0.1:5000/api/auth/login', formData);
      login(res.data);
      navigate('/profile/overview');
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
           <h2>Welcome Back</h2>
           <p>Log in to your {role} portal</p>
        </div>
        
        <div className="role-switcher">
          <div className={`role-tab ${role === 'patient' ? 'active' : ''}`} onClick={() => setRole('patient')}>
            <User size={18} /> Patient
          </div>
          <div className={`role-tab ${role === 'therapist' ? 'active' : ''}`} onClick={() => setRole('therapist')}>
            <Stethoscope size={18} /> Therapist
          </div>
        </div>

        {error && <div style={{color: '#d32f2f', background: '#ffebee', padding: '10px', borderRadius: '8px', textAlign: 'center', marginBottom: '15px', fontSize: '0.9rem'}}>{error}</div>}

        <form onSubmit={handleLogin}>
          <div className="input-group">
            <Mail size={20} className="input-icon" />
            <input 
              className="auth-input" 
              type="email" 
              placeholder="Email Address" 
              required 
              onChange={(e) => setFormData({...formData, email: e.target.value})} 
            />
          </div>
          <div className="input-group">
            <Lock size={20} className="input-icon" />
            <input 
              className="auth-input" 
              type="password" 
              placeholder="Password" 
              required 
              onChange={(e) => setFormData({...formData, password: e.target.value})} 
            />
          </div>
          <button type="submit" className="auth-btn">Log In</button>
        </form>

        <div className="or-divider">OR</div>
        
        <GoogleButton onClick={() => googleLogin()} />

        <div className="auth-footer">
          Don't have an account? <Link to="/auth/signup" className="auth-link">Sign Up</Link>
        </div>
      </div>
    </div>
  );
};

export const Signup = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [role, setRole] = useState('patient');
  const [formData, setFormData] = useState({ name: '', email: '', password: '', licenseId: '' });
  const [otpSent, setOtpSent] = useState(false);
  const [otp, setOtp] = useState('');
  const [message, setMessage] = useState('');

  const googleSignup = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await axios.post('http://127.0.0.1:5000/api/auth/google', {
          token: tokenResponse.access_token,
          role: role
        });
        login(res.data);
        navigate('/auth/onboarding');
      } catch (err) {
        setMessage('Google Signup Failed');
      }
    },
    onError: () => setMessage('Google Signup Failed'),
  });

  const handleSendOtp = async (e) => {
    e.preventDefault();
    try {
        await axios.post('http://127.0.0.1:5000/api/auth/send-otp', { email: formData.email });
        setOtpSent(true);
        setMessage('OTP sent to your email!');
    } catch (err) {
        setMessage(err.response?.data?.error || 'Failed to send OTP');
    }
  };

  const handleVerifyAndSignup = async () => {
    try {
        const res = await axios.post('http://127.0.0.1:5000/api/auth/signup-verify', {
            ...formData, otp, role
        });
        login(res.data.user);
        navigate('/auth/onboarding');
    } catch (err) {
        setMessage(err.response?.data?.error || 'Verification failed');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header"><h2>Create Account</h2></div>
        
        <div className="role-switcher">
          <div className={`role-tab ${role === 'patient' ? 'active' : ''}`} onClick={() => setRole('patient')}>
            <User size={18} /> Patient
          </div>
          <div className={`role-tab ${role === 'therapist' ? 'active' : ''}`} onClick={() => setRole('therapist')}>
            <Stethoscope size={18} /> Therapist
          </div>
        </div>

        {message && <div style={{color: otpSent ? '#2e7d32' : '#d32f2f', background: otpSent ? '#e8f5e9' : '#ffebee', padding: '10px', borderRadius: '8px', textAlign: 'center', marginBottom: '15px', fontSize: '0.9rem'}}>{message}</div>}

        {!otpSent ? (
            <form onSubmit={handleSendOtp}>
                <div className="input-group"><User size={20} className="input-icon" /><input className="auth-input" type="text" placeholder="Full Name" required onChange={(e) => setFormData({...formData, name: e.target.value})} /></div>
                <div className="input-group"><Mail size={20} className="input-icon" /><input className="auth-input" type="email" placeholder="Email Address" required onChange={(e) => setFormData({...formData, email: e.target.value})} /></div>
                {role === 'therapist' && (<div className="input-group"><ShieldCheck size={20} className="input-icon" /><input className="auth-input" type="text" placeholder="Medical License ID" required onChange={(e) => setFormData({...formData, licenseId: e.target.value})} /></div>)}
                <div className="input-group"><Lock size={20} className="input-icon" /><input className="auth-input" type="password" placeholder="Create Password" required onChange={(e) => setFormData({...formData, password: e.target.value})} /></div>
                <button type="submit" className="auth-btn">Verify Email & Signup</button>
            </form>
        ) : (
            <div>
                <div className="input-group">
                    <input 
                        className="auth-input" 
                        type="text" 
                        placeholder="Enter 6-digit OTP" 
                        value={otp} 
                        onChange={(e) => setOtp(e.target.value)} 
                        style={{textAlign: 'center', letterSpacing: '5px', fontSize: '1.2rem', paddingLeft: '15px'}} 
                    />
                </div>
                <button onClick={handleVerifyAndSignup} className="auth-btn">Confirm OTP</button>
            </div>
        )}

        {!otpSent && (
            <>
                <div className="or-divider">OR</div>
                <GoogleButton onClick={() => googleSignup()} />
            </>
        )}

        <div className="auth-footer">
            Already have an account? <Link to="/auth/login" className="auth-link">Log In</Link>
        </div>
      </div>
    </div>
  );
};

// ... Placeholder components remain unchanged ...
const pageStyle = { padding: '40px', textAlign: 'center', color: '#666' };
export const Onboarding = () => (<div style={pageStyle}><h1>Welcome Aboard!</h1><Link to="/profile/overview" className="auth-link">Continue to Dashboard</Link></div>);
const Placeholder = ({ title }) => (<div style={pageStyle}><h1>{title}</h1><p>Coming Soon</p></div>);
export const ProfileOverview = () => <Placeholder title="Profile Overview" />;
export const MedicalInfo = () => <Placeholder title="Medical Info" />;
export const Preferences = () => <Placeholder title="Preferences" />;
export const MyPrograms = () => <Placeholder title="My Programs" />;
export const CustomProgram = () => <Placeholder title="Custom Program" />;
export const AccuracyGraphs = () => <Placeholder title="Accuracy Analytics" />;
export const RiskPrediction = () => <Placeholder title="Risk Prediction" />;
export const Achievements = () => <Placeholder title="Achievements" />;
export const Challenges = () => <Placeholder title="Challenges" />;
export const TherapistModule = () => <Placeholder title="Find a Therapist" />;
export const FAQ = () => <Placeholder title="FAQ" />;
export const Contact = () => <Placeholder title="Contact Support" />;
export const Legal = () => <Placeholder title="Legal" />;
export const ExerciseDetail = () => <Placeholder title="Exercise Detail" />;