import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext'; 
import { GoogleOAuthProvider } from '@react-oauth/google'; 

import Dashboard from './Dashboard';
import Tracker from './Tracker';
import Report from './Report';
import Tutorial from './Tutorial'; 
import Profile from './pages/Profile';
import Navbar from './components/Navbar';
import * as Pages from './pages/PlaceholderPages';

// ✅ YOUR NEW CLIENT ID IS HERE
const GOOGLE_CLIENT_ID = "254404106678-ql7lb3kidfsvdjk5a4fcjl7t7kn61aos.apps.googleusercontent.com"; 

const Layout = ({ children }) => {
  const location = useLocation();
  const showNavbar = location.pathname !== '/track';

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
              {/* Main Pages */}
              <Route path="/" element={<Dashboard />} />
              <Route path="/track" element={<Tracker />} />
              <Route path="/report" element={<Report />} />
              
              {/* Training Section */}
              <Route path="/training/library" element={<Tutorial />} /> 
              <Route path="/training/detail" element={<Pages.ExerciseDetail />} />
              
              {/* Auth */}
              <Route path="/auth/login" element={<Pages.Login />} />
              <Route path="/auth/signup" element={<Pages.Signup />} />
              <Route path="/auth/onboarding" element={<Pages.Onboarding />} />

              {/* Profile */}
              <Route path="/profile/overview" element={<Profile />} />
              <Route path="/profile/medical" element={<Pages.MedicalInfo />} />
              <Route path="/profile/preferences" element={<Pages.Preferences />} />

              {/* Programs */}
              <Route path="/programs/my-programs" element={<Pages.MyPrograms />} />
              <Route path="/programs/custom" element={<Pages.CustomProgram />} />

              {/* Analytics */}
              <Route path="/analytics/accuracy" element={<Pages.AccuracyGraphs />} />
              <Route path="/analytics/risk" element={<Pages.RiskPrediction />} />

              {/* Community */}
              <Route path="/community/achievements" element={<Pages.Achievements />} />
              <Route path="/community/challenges" element={<Pages.Challenges />} />
              <Route path="/community/therapist" element={<Pages.TherapistModule />} />

              {/* Support */}
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