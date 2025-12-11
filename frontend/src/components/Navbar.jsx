import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom'; // Added useNavigate
import { ChevronDown, Activity, User, BookOpen, BarChart2, Users, LifeBuoy, LogOut } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext'; // Import the Auth Context

const NavItem = ({ title, icon: Icon, items, path }) => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const isActive = path ? location.pathname === path : false;

  const containerStyle = {
    padding: '10px 15px',
    cursor: 'pointer',
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: isActive ? 'var(--primary-color)' : 'var(--text-primary)',
    fontWeight: '600',
    textDecoration: 'none'
  };

  if (!items && path) {
    return (
      <Link 
        to={path} 
        style={containerStyle}
        onMouseEnter={(e) => e.target.style.color = 'var(--primary-color)'}
        onMouseLeave={(e) => e.target.style.color = isActive ? 'var(--primary-color)' : 'var(--text-primary)'}
      >
        {Icon && <Icon size={18} />}
        {title}
      </Link>
    );
  }

  return (
    <div 
      className="nav-item"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
      style={containerStyle}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {Icon && <Icon size={18} color="var(--primary-color)" />}
        {title}
        {items && <ChevronDown size={14} style={{ opacity: 0.5 }} />}
      </div>

      <AnimatePresence>
        {isOpen && items && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              minWidth: '220px',
              background: '#ffffff',
              border: '1px solid rgba(0,0,0,0.05)',
              borderRadius: '12px',
              boxShadow: '0 15px 40px rgba(26,60,52,0.1)',
              padding: '10px 0',
              zIndex: 1000,
              overflow: 'hidden'
            }}
          >
            {items.map((sub, idx) => (
              <Link 
                key={idx} 
                to={sub.path}
                style={{ 
                  display: 'block', 
                  padding: '12px 20px', 
                  color: '#666', 
                  textDecoration: 'none',
                  fontSize: '0.9rem',
                  fontWeight: '500',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => { e.target.style.background = '#f5f5f5'; e.target.style.color = 'var(--primary-color)'; }}
                onMouseLeave={(e) => { e.target.style.background = 'transparent'; e.target.style.color = '#666'; }}
              >
                {sub.name}
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const Navbar = () => {
  const { user, logout } = useAuth(); // ACCESS GLOBAL USER STATE
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav style={{ 
      height: '80px', 
      background: 'rgba(255, 255, 255, 0.95)', 
      borderBottom: '1px solid rgba(0,0,0,0.05)',
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'space-between',
      padding: '0 40px',
      position: 'sticky',
      top: 0,
      zIndex: 999,
      backdropFilter: 'blur(10px)'
    }}>
      <Link to="/" style={{ textDecoration: 'none' }}>
        <h2 style={{ margin: 0, color: '#1a1a1a', fontSize: '1.6rem', fontWeight: '800', letterSpacing: '-1px' }}>
          PHYSIO<span style={{ color: 'var(--primary-color)' }}>CHECK</span>
        </h2>
      </Link>

      {/* Center Links */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <NavItem title="Profile" icon={User} items={[
           { name: 'Overview', path: '/profile/overview' },
           { name: 'Medical Info', path: '/profile/medical' }
        ]} />
        <NavItem title="Training" icon={Activity} path="/track" />
        <NavItem title="Programs" icon={BookOpen} items={[
           { name: 'My Programs', path: '/programs/my-programs' }
        ]} />
        <NavItem title="Analytics" icon={BarChart2} items={[
           { name: 'Daily Report', path: '/report' }
        ]} />
        <NavItem title="Community" icon={Users} items={[
           { name: 'Achievements', path: '/community/achievements' }
        ]} />
      </div>

      {/* Auth Buttons - CONDITIONAL RENDERING */}
      <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
        {user ? (
          // IF LOGGED IN
          <>
            <div style={{ textAlign: 'right', marginRight: '10px' }}>
              <span style={{ display: 'block', fontSize: '0.85rem', color: '#888' }}>Welcome back,</span>
              <span style={{ fontWeight: '700', color: 'var(--primary-color)' }}>{user.name}</span>
            </div>
            <button 
              onClick={handleLogout}
              style={{ 
                background: '#f5f5f5', 
                border: 'none', 
                padding: '10px 15px', 
                borderRadius: '12px', 
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontWeight: '600',
                color: '#666'
              }}
            >
              <LogOut size={16} />
              Logout
            </button>
          </>
        ) : (
          // IF LOGGED OUT
          <>
            <Link to="/auth/login" style={{ 
                textDecoration: 'none', 
                color: '#1a1a1a', 
                fontWeight: '700', 
                padding: '10px 20px'
            }}>Login</Link>
            
            <Link to="/auth/signup" style={{ 
                textDecoration: 'none', 
                background: 'var(--primary-color)', 
                color: '#fff', 
                padding: '10px 24px', 
                borderRadius: '30px', 
                fontWeight: '700',
                boxShadow: '0 4px 14px rgba(118, 176, 65, 0.4)' 
            }}>Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;