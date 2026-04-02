import { useState, useEffect } from 'react';
import './ProfileMenu.css';

export default function ProfileMenu({ theme, toggleTheme, userName, onSetUserName }) {
    const [isOpen, setIsOpen] = useState(false);
    const [editingName, setEditingName] = useState(false);
    const [nameInput, setNameInput] = useState(userName);

    const submitName = () => {
        onSetUserName(nameInput);
        setEditingName(false);
    };

    // Toggle internal state on hover is handled via CSS opacity, 
    // but accessible on click too if needed.
    // We'll rely on pure CSS for the hover dropdown for simplicity and performance.

    return (
        <div className="profile-menu-container">
            <button
                className="profile-btn"
                aria-label="User Profile"
                onClick={() => setIsOpen(!isOpen)}
                onMouseEnter={() => setIsOpen(true)}
            >
                <span className="profile-placeholder">{userName.trim().charAt(0).toUpperCase()}</span>
            </button>

            <div className={`profile-dropdown ${isOpen ? 'show' : ''}`} onMouseLeave={() => setIsOpen(false)}>
                <div className="menu-item-group">
                    <div className="profile-name-section">
                        {editingName ? (
                            <input
                                className="profile-name-input"
                                autoFocus
                                value={nameInput}
                                onChange={e => setNameInput(e.target.value)}
                                onBlur={submitName}
                                onKeyDown={e => { if (e.key === 'Enter') submitName(); if (e.key === 'Escape') setEditingName(false); }}
                            />
                        ) : (
                            <div className="profile-name-row" onClick={() => { setNameInput(userName); setEditingName(true); }}>
                                <span className="profile-name">{userName}</span>
                                <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12" style={{ opacity: 0.5 }}>
                                    <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
                                </svg>
                            </div>
                        )}
                    </div>

                    <div className="menu-divider"></div>

                    <button className="menu-item theme-toggle" onClick={toggleTheme}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            {theme === 'dark' ? (
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                                </svg>
                            ) : (
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <circle cx="12" cy="12" r="5"></circle>
                                    <line x1="12" y1="1" x2="12" y2="3"></line>
                                    <line x1="12" y1="21" x2="12" y2="23"></line>
                                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                                    <line x1="1" y1="12" x2="3" y2="12"></line>
                                    <line x1="21" y1="12" x2="23" y2="12"></line>
                                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                                </svg>
                            )}
                            <span>Theme: {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
}
