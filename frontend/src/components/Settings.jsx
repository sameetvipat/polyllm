import { useState, useEffect } from 'react';
import './Settings.css';

export default function Settings({ isOpen, onClose, firstName, lastName, email, onSetAccountDetails, theme, toggleTheme, onSignOut }) {
  const [activeSection, setActiveSection] = useState('profile');
  const [firstNameInput, setFirstNameInput] = useState(firstName);
  const [lastNameInput, setLastNameInput] = useState(lastName);
  const [emailInput, setEmailInput] = useState(email);
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      setFirstNameInput(firstName);
      setLastNameInput(lastName);
      setEmailInput(email);
    }
  }, [isOpen, firstName, lastName, email]);

  const handleSave = () => {
    onSetAccountDetails({ firstName: firstNameInput, lastName: lastNameInput, email: emailInput });
    setSaveMsg('Saved!');
    setTimeout(() => setSaveMsg(''), 2000);
  };

  if (!isOpen) return null;

  const displayInitial = (firstNameInput.trim() || firstName).charAt(0).toUpperCase();
  const displayName = [firstNameInput.trim(), lastNameInput.trim()].filter(Boolean).join(' ') || 'User';

  const sections = [
    { id: 'profile', label: 'Profile' },
    { id: 'appearance', label: 'Appearance' },
  ];

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={e => e.stopPropagation()}>
        <div className="settings-header">
          <span className="settings-title">Settings</span>
          <button className="settings-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <div className="settings-body">
          <nav className="settings-nav">
            {sections.map(s => (
              <button
                key={s.id}
                className={`settings-nav-item ${activeSection === s.id ? 'active' : ''}`}
                onClick={() => setActiveSection(s.id)}
              >
                {s.label}
              </button>
            ))}
          </nav>

          <div className="settings-content">
            {activeSection === 'profile' && (
              <div className="settings-section">
                <h3 className="settings-section-title">Account Details</h3>

                <div className="profile-avatar-row">
                  <div className="profile-avatar-preview">{displayInitial}</div>
                  <div className="profile-avatar-meta">
                    <div className="profile-avatar-name">{displayName}</div>
                    {emailInput.trim() && (
                      <div className="profile-avatar-email">{emailInput.trim()}</div>
                    )}
                  </div>
                </div>

                <div className="settings-fields-row">
                  <div className="settings-field">
                    <label className="settings-label">First Name</label>
                    <input
                      className="settings-input"
                      value={firstNameInput}
                      onChange={e => setFirstNameInput(e.target.value)}
                      placeholder="First name"
                    />
                  </div>
                  <div className="settings-field">
                    <label className="settings-label">Last Name</label>
                    <input
                      className="settings-input"
                      value={lastNameInput}
                      onChange={e => setLastNameInput(e.target.value)}
                      placeholder="Last name"
                    />
                  </div>
                </div>

                <div className="settings-field">
                  <label className="settings-label">Email</label>
                  <input
                    className="settings-input"
                    type="email"
                    value={emailInput}
                    onChange={e => setEmailInput(e.target.value)}
                    placeholder="you@example.com"
                  />
                </div>

                <div className="settings-signout-row">
                  <button className="settings-signout-btn" onClick={onSignOut}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="15" height="15" strokeWidth="2">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                      <polyline points="16 17 21 12 16 7"/>
                      <line x1="21" y1="12" x2="9" y2="12"/>
                    </svg>
                    Sign Out
                  </button>
                </div>
              </div>
            )}

            {activeSection === 'appearance' && (
              <div className="settings-section">
                <h3 className="settings-section-title">Appearance</h3>
                <div className="settings-field settings-row">
                  <div>
                    <div className="settings-label">Theme</div>
                    <div className="settings-hint">Switch between dark and light mode</div>
                  </div>
                  <button className="settings-theme-toggle" onClick={toggleTheme}>
                    {theme === 'dark' ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                      </svg>
                    )}
                    {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="settings-footer">
          {saveMsg && <span className="settings-save-msg">{saveMsg}</span>}
          <button className="settings-cancel-btn" onClick={onClose}>Cancel</button>
          <button className="settings-save-btn" onClick={handleSave}>Save Changes</button>
        </div>
      </div>
    </div>
  );
}
