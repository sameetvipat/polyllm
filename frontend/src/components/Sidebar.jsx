import { useState, useEffect, useRef } from 'react';
import './Sidebar.css';

function parseDate(dateStr) {
  if (!dateStr) return new Date();

  // Handle naive UTC strings from legacy backend which are interpreted as local time by default
  // If string has no 'Z' and no timezone offset (e.g. +00:00), treat as UTC
  if (typeof dateStr === 'string' &&
    !dateStr.endsWith('Z') &&
    !dateStr.includes('+') &&
    /^\d{4}-\d{2}-\d{2}T/.test(dateStr)) {
    return new Date(dateStr + 'Z');
  }

  return new Date(dateStr);
}

function getRelativeTime(dateStr) {
  const now = new Date();
  const date = parseDate(dateStr);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncateText(text, maxLen = 40) {
  if (!text) return '';
  if (text.length <= maxLen) return text;
  return text.substring(0, maxLen).trim() + '…';
}

function ConversationItem({ conv, isActive, isGenerating, onSelect, onDelete, onRename }) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const startRename = (e) => {
    e.stopPropagation();
    setRenameValue(conv.title && conv.title !== 'New Conversation' ? conv.title : '');
    setIsRenaming(true);
  };

  const submitRename = () => {
    if (renameValue.trim()) onRename(conv.id, renameValue.trim());
    setIsRenaming(false);
  };

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const handleRenameKeyDown = (e) => {
    if (e.key === 'Enter') submitRename();
    if (e.key === 'Escape') setIsRenaming(false);
  };

  return (
    <div className={`conversation-item ${isActive ? 'active' : ''} ${menuOpen ? 'menu-open' : ''}`}>
      {isRenaming ? (
        <input
          className="rename-input"
          autoFocus
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={handleRenameKeyDown}
          onBlur={submitRename}
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <div className="conversation-content" onClick={() => onSelect(conv.id)}>
          <div className="conversation-title">
            {conv.title && conv.title !== 'New Conversation'
              ? conv.title
              : (conv.first_message ? truncateText(conv.first_message) : 'New Conversation')}
          </div>
          <div className="conversation-meta">
            {isGenerating
              ? <span style={{ color: 'var(--accent)', opacity: 0.7 }}>Generating...</span>
              : <span>{parseDate(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            }
          </div>
        </div>
      )}
      <div className="conversation-menu" ref={menuRef}>
        <button
          className={`menu-btn ${menuOpen ? 'active' : ''}`}
          aria-label="Conversation options"
          onClick={(e) => { e.stopPropagation(); setMenuOpen(prev => !prev); }}
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="12" cy="19" r="2" />
          </svg>
        </button>
        {menuOpen && (
          <div className="menu-dropdown menu-dropdown-open">
            <button className="menu-item" onClick={(e) => { e.stopPropagation(); setMenuOpen(false); startRename(e); }}>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
              </svg>
              Rename
            </button>
            <button
              className="menu-item delete-item"
              onClick={(e) => { e.stopPropagation(); setMenuOpen(false); onDelete(conv.id); }}
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function SidebarUserPanel({ userName, onOpenSettings }) {
  return (
    <div className="sidebar-user-panel">
      <div className="sidebar-user-info">
        <div className="sidebar-avatar">{userName.trim().charAt(0).toUpperCase()}</div>
        <div className="sidebar-user-details">
          <span className="sidebar-username">{userName}</span>
        </div>
      </div>
      <button className="sidebar-settings-btn" onClick={onOpenSettings} title="Settings">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" width="16" height="16" strokeWidth="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
    </div>
  );
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
  isOpen,
  toggleSidebar,
  loadingIds = new Set(),
  userName,
  onOpenSettings,
  onGoHome,
}) {
  const todayConversations = conversations.filter(conv => {
    const date = parseDate(conv.created_at);
    const now = new Date();
    return date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate();
  });

  const pastConversations = conversations.filter(conv => {
    const date = parseDate(conv.created_at);
    const now = new Date();
    return !(date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate());
  });

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <div className="logo-toggle-area" style={{ marginBottom: '1rem' }}>
          <div
            className="logo"
            style={{ marginBottom: 0 }}
            onClick={isOpen ? onGoHome : toggleSidebar}
          >
            <div className="logo-icon-wrap">
              <img src="/Logo.png" alt="PolyLLM Council" className="logo-image" />
              <svg className="logo-expand-arrow" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z" />
              </svg>
            </div>
            <span>PolyLLM Council</span>
          </div>
          {isOpen && (
            <svg
              className="logo-collapse-arrow"
              viewBox="0 0 24 24"
              fill="currentColor"
              width="18"
              height="18"
              onClick={toggleSidebar}
              style={{ cursor: 'pointer', flexShrink: 0 }}
            >
              <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" />
            </svg>
          )}
        </div>
        <button className="new-btn" onClick={onNewConversation}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
          </svg>
          <span>New Chat</span>
        </button>
      </div>

      <div className="conversation-list" style={{ flex: 1 }}>
        {conversations.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No history yet
          </div>
        ) : (
          <>
            {todayConversations.length > 0 && (
              <div>
                <div className="time-group-label">Today</div>
                {todayConversations.map(conv => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={conv.id === currentConversationId}
                    isGenerating={loadingIds.has(conv.id)}
                    onSelect={onSelectConversation}
                    onDelete={onDeleteConversation}
                    onRename={onRenameConversation}
                  />
                ))}
              </div>
            )}
            {pastConversations.length > 0 && (
              <div>
                <div className="time-group-label">Past Conversations</div>
                {pastConversations.map(conv => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={conv.id === currentConversationId}
                    isGenerating={loadingIds.has(conv.id)}
                    onSelect={onSelectConversation}
                    onDelete={onDeleteConversation}
                    onRename={onRenameConversation}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <div className="sidebar-footer">
        <SidebarUserPanel userName={userName} onOpenSettings={onOpenSettings} />
      </div>
    </div>
  );
}
