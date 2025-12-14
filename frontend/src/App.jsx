// frontend/src/App.jsx

import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext'; 
import { GoogleOAuthProvider } from '@react-oauth/google'; 

// --- DASHBOARD COMPONENTS ---
import PatientDashboard from './Dashboard'; 
import TherapistDashboard from './TherapistDashboard'; 
import HomeRedirect from './HomeRedirect'; 

// --- THERAPIST PAGES ---
import TherapistPatientMonitoring from './pages/TherapistPatientMonitoring.jsx'; 
import TherapistExerciseLibrary from './pages/TherapistExerciseLibrary.jsx';
import TherapistProtocolManager from './pages/TherapistProtocolManager.jsx';
import TherapistNotificationLog from './pages/TherapistNotificationLog.jsx';
import TherapistAnalytics from './pages/TherapistAnalytics.jsx'; 
import SessionReviewScreen from './components/SessionReviewScreen.jsx'; 
import TherapistPatientDetail from './pages/TherapistPatientDetail'; 

// --- OTHER PAGES ---
import Tracker from './Tracker';
import Report from './Report';
import Tutorial from './Tutorial'; 
import Profile from './pages/Profile';
import Analytics from './pages/Analytics'; 
import RiskPrediction from './pages/RiskPrediction'; 
import Navbar from './components/Navbar';
import * as Pages from './pages/PlaceholderPages';

const GOOGLE_CLIENT_ID = "254404106678-ql7lb3kidfsvdjk5a4fcjl7t7kn61aos.apps.googleusercontent.com"; 

// --- ✅ UPDATED LAYOUT COMPONENT ---
const Layout = ({ children }) => {
  const location = useLocation();
  
  // 1. Check if we are on the Tracking page
  const isTrackingPage = location.pathname === '/track';

  // 2. Check if we are on ANY Therapist page (Dashboard or sub-pages)
  // This covers '/therapist-dashboard', '/therapist/monitoring', etc.
  const isTherapistPage = location.pathname.startsWith('/therapist');

  // Only show Navbar if we are NOT tracking AND NOT a therapist
  const showNavbar = !isTrackingPage && !isTherapistPage;

  return (
    <>
      {showNavbar && <Navbar />}
      <div style={{ minHeight: 'calc(100vh - 80px)' }}>
        {children}
      </div>
    </>
  );
};

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <Router>
          <Layout>
            <Routes>
              {/* --- MAIN ENTRY POINT --- */}
              <Route path="/" element={<HomeRedirect />} />
              
              {/* --- DASHBOARDS --- */}
              <Route path="/patient-dashboard" element={<PatientDashboard />} />
              <Route path="/therapist-dashboard" element={<TherapistDashboard />} />
              
              {/* --- THERAPIST-ONLY ROUTES --- */}
              <Route path="/therapist/monitoring" element={<TherapistPatientMonitoring />} /> 
              <Route path="/therapist/library" element={<TherapistExerciseLibrary />} />
              <Route path="/therapist/protocols" element={<TherapistProtocolManager />} />
              <Route path="/therapist/notifications" element={<TherapistNotificationLog />} />
              <Route path="/therapist/analytics" element={<TherapistAnalytics />} />
              <Route path="/therapist/session-review/:sessionId" element={<SessionReviewScreen onClose={() => {}} sessionId="MOCK_ID_123" />} />
              <Route path="/therapist/patient-detail/:email" element={<TherapistPatientDetail />} />


              {/* --- PATIENT MAIN PAGES --- */}
              <Route path="/track" element={<Tracker />} />
              <Route path="/report" element={<Report />} />
              
              {/* --- Training Section --- */}
              <Route path="/training/library" element={<Tutorial />} /> 
              <Route path="/training/detail" element={<Pages.ExerciseDetail />} />
              
              {/* --- Authentication --- */}
              <Route path="/auth/login" element={<Pages.Login />} />
              <Route path="/auth/signup" element={<Pages.Signup />} />
              <Route path="/auth/onboarding" element={<Pages.Onboarding />} />

              {/* --- Profile --- */}
              <Route path="/profile/overview" element={<Profile />} />
              <Route path="/profile/medical" element={<Pages.MedicalInfo />} />
              <Route path="/profile/preferences" element={<Pages.Preferences />} />

              {/* --- Programs --- */}
              <Route path="/programs/my-programs" element={<Pages.MyPrograms />} />
              <Route path="/programs/custom" element={<Pages.CustomProgram />} />

              {/* --- ANALYTICS ROUTES --- */}
              <Route path="/analytics/accuracy" element={<Analytics />} />
              <Route path="/analytics/risk" element={<RiskPrediction />} />

              {/* --- Community --- */}
              <Route path="/community/achievements" element={<Pages.Achievements />} />
              <Route path="/community/challenges" element={<Pages.Challenges />} />
              <Route path="/community/therapist" element={<Pages.TherapistModule />} />

              {/* --- Support --- */}
              <Route path="/support/faq" element={<Pages.FAQ />} />
              <Route path="/support/contact" element={<Pages.Contact />} />
              <Route path="/support/legal" element={<Pages.Legal />} />

              <Route path="/tutorial" element={<Tutorial />} />
            </Routes>
          </Layout>
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;