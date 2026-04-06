import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './AuthPage.css';

function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(password) {
  return password.length >= 8 && /[a-zA-Z]/.test(password) && /[0-9]/.test(password);
}

function getUsers() {
  try { return JSON.parse(localStorage.getItem('polyllm_users') || '[]'); } catch { return []; }
}

export default function AuthPage({ onAuth, onBack }) {
  const [mode, setMode] = useState('login');

  // Login
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginErrors, setLoginErrors] = useState({});
  const [loginGeneralError, setLoginGeneralError] = useState('');

  // Signup
  const [signupFirstName, setSignupFirstName] = useState('');
  const [signupLastName, setSignupLastName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [signupErrors, setSignupErrors] = useState({});

  const [showLoginPw, setShowLoginPw] = useState(false);
  const [showSignupPw, setShowSignupPw] = useState(false);
  const [showSignupConfirm, setShowSignupConfirm] = useState(false);

  const handleLogin = (e) => {
    e.preventDefault();
    const errors = {};
    if (!loginEmail.trim()) errors.email = 'Email is required';
    else if (!validateEmail(loginEmail)) errors.email = 'Enter a valid email address';
    if (!loginPassword) errors.password = 'Password is required';

    if (Object.keys(errors).length > 0) { setLoginErrors(errors); return; }

    const user = getUsers().find(
      u => u.email.toLowerCase() === loginEmail.trim().toLowerCase() && u.password === loginPassword
    );
    if (!user) { setLoginGeneralError('Incorrect email or password'); setLoginErrors({}); return; }

    const authData = { firstName: user.firstName, lastName: user.lastName, email: user.email };
    localStorage.setItem('polyllm_auth', JSON.stringify(authData));
    onAuth(authData, false);
  };

  const handleSignup = (e) => {
    e.preventDefault();
    const errors = {};
    if (!signupFirstName.trim()) errors.firstName = 'First name is required';
    if (!signupEmail.trim()) errors.email = 'Email is required';
    else if (!validateEmail(signupEmail)) errors.email = 'Enter a valid email address';
    else if (getUsers().some(u => u.email.toLowerCase() === signupEmail.trim().toLowerCase()))
      errors.email = 'An account with this email already exists';
    if (!signupPassword) errors.password = 'Password is required';
    else if (!validatePassword(signupPassword))
      errors.password = 'Minimum 8 characters with at least one letter and one number';
    if (!signupConfirm) errors.confirm = 'Please confirm your password';
    else if (signupPassword !== signupConfirm) errors.confirm = 'Passwords do not match';

    if (Object.keys(errors).length > 0) { setSignupErrors(errors); return; }

    const newUser = {
      firstName: signupFirstName.trim(),
      lastName: signupLastName.trim(),
      email: signupEmail.trim().toLowerCase(),
      password: signupPassword,
    };
    const users = getUsers();
    users.push(newUser);
    localStorage.setItem('polyllm_users', JSON.stringify(users));

    const authData = { firstName: newUser.firstName, lastName: newUser.lastName, email: newUser.email };
    localStorage.setItem('polyllm_auth', JSON.stringify(authData));
    onAuth(authData, true);
  };

  const clearLogin = () => { setLoginErrors({}); setLoginGeneralError(''); };
  const clearSignup = (field) => setSignupErrors(prev => ({ ...prev, [field]: '' }));

  const EyeIcon = ({ show }) => show ? (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );

  return (
    <div className="auth-page">
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 24, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        {onBack && (
          <button className="auth-back-btn" onClick={onBack}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="15" height="15" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back to home
          </button>
        )}
        <div className="auth-logo">
          <img src="/Logo.png" alt="PolyLLM Council" className="auth-logo-img" />
          <span className="auth-logo-text">PolyLLM Council</span>
        </div>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); clearLogin(); }}
          >
            Sign In
          </button>
          <button
            className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
            onClick={() => { setMode('signup'); setSignupErrors({}); }}
          >
            Create Account
          </button>
        </div>

        <AnimatePresence mode="wait">
        {mode === 'login' && (
          <motion.form
            key="login"
            className="auth-form"
            onSubmit={handleLogin}
            noValidate
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 16 }}
            transition={{ duration: 0.22 }}
          >
            {loginGeneralError && (
              <div className="auth-general-error">{loginGeneralError}</div>
            )}

            <div className="auth-field">
              <label className="auth-label">Email</label>
              <input
                className={`auth-input ${loginErrors.email ? 'error' : ''}`}
                type="email"
                placeholder="you@example.com"
                value={loginEmail}
                onChange={e => { setLoginEmail(e.target.value); clearLogin(); }}
                autoComplete="email"
              />
              {loginErrors.email && <span className="auth-error-msg">{loginErrors.email}</span>}
            </div>

            <div className="auth-field">
              <label className="auth-label">Password</label>
              <div className="auth-input-wrap">
                <input
                  className={`auth-input ${loginErrors.password ? 'error' : ''}`}
                  type={showLoginPw ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={loginPassword}
                  onChange={e => { setLoginPassword(e.target.value); clearLogin(); }}
                  autoComplete="current-password"
                />
                <button type="button" className="auth-eye-btn" onClick={() => setShowLoginPw(p => !p)}>
                  <EyeIcon show={showLoginPw} />
                </button>
              </div>
              {loginErrors.password && <span className="auth-error-msg">{loginErrors.password}</span>}
            </div>

            <button type="submit" className="auth-submit-btn">Sign In</button>

            <p className="auth-switch-text">
              Don't have an account?{' '}
              <button type="button" className="auth-switch-link" onClick={() => { setMode('signup'); clearLogin(); }}>
                Create one
              </button>
            </p>
          </motion.form>
        )}

        {mode === 'signup' && (
          <motion.form
            key="signup"
            className="auth-form"
            onSubmit={handleSignup}
            noValidate
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.22 }}
          >
            <div className="auth-fields-row">
              <div className="auth-field">
                <label className="auth-label">First Name</label>
                <input
                  className={`auth-input ${signupErrors.firstName ? 'error' : ''}`}
                  type="text"
                  placeholder="John"
                  value={signupFirstName}
                  onChange={e => { setSignupFirstName(e.target.value); clearSignup('firstName'); }}
                  autoComplete="given-name"
                />
                {signupErrors.firstName && <span className="auth-error-msg">{signupErrors.firstName}</span>}
              </div>
              <div className="auth-field">
                <label className="auth-label">Last Name</label>
                <input
                  className={`auth-input ${signupErrors.lastName ? 'error' : ''}`}
                  type="text"
                  placeholder="Doe"
                  value={signupLastName}
                  onChange={e => { setSignupLastName(e.target.value); clearSignup('lastName'); }}
                  autoComplete="family-name"
                />
                {signupErrors.lastName && <span className="auth-error-msg">{signupErrors.lastName}</span>}
              </div>
            </div>

            <div className="auth-field">
              <label className="auth-label">Email</label>
              <input
                className={`auth-input ${signupErrors.email ? 'error' : ''}`}
                type="email"
                placeholder="you@example.com"
                value={signupEmail}
                onChange={e => { setSignupEmail(e.target.value); clearSignup('email'); }}
                autoComplete="email"
              />
              {signupErrors.email && <span className="auth-error-msg">{signupErrors.email}</span>}
            </div>

            <div className="auth-field">
              <label className="auth-label">Password</label>
              <div className="auth-input-wrap">
                <input
                  className={`auth-input ${signupErrors.password ? 'error' : ''}`}
                  type={showSignupPw ? 'text' : 'password'}
                  placeholder="Min. 8 chars, letter & number"
                  value={signupPassword}
                  onChange={e => { setSignupPassword(e.target.value); clearSignup('password'); }}
                  autoComplete="new-password"
                />
                <button type="button" className="auth-eye-btn" onClick={() => setShowSignupPw(p => !p)}>
                  <EyeIcon show={showSignupPw} />
                </button>
              </div>
              {signupErrors.password && <span className="auth-error-msg">{signupErrors.password}</span>}
            </div>

            <div className="auth-field">
              <label className="auth-label">Confirm Password</label>
              <div className="auth-input-wrap">
                <input
                  className={`auth-input ${signupErrors.confirm ? 'error' : ''}`}
                  type={showSignupConfirm ? 'text' : 'password'}
                  placeholder="Re-enter your password"
                  value={signupConfirm}
                  onChange={e => { setSignupConfirm(e.target.value); clearSignup('confirm'); }}
                  autoComplete="new-password"
                />
                <button type="button" className="auth-eye-btn" onClick={() => setShowSignupConfirm(p => !p)}>
                  <EyeIcon show={showSignupConfirm} />
                </button>
              </div>
              {signupErrors.confirm && <span className="auth-error-msg">{signupErrors.confirm}</span>}
            </div>

            <button type="submit" className="auth-submit-btn">Create Account</button>

            <p className="auth-switch-text">
              Already have an account?{' '}
              <button type="button" className="auth-switch-link" onClick={() => { setMode('login'); setSignupErrors({}); }}>
                Sign in
              </button>
            </p>
          </motion.form>
        )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
