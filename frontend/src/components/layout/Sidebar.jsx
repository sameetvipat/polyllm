/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import './Sidebar.css';

const SKELETON_KEYS = [1, 2, 3, 4];

/* ─── Helpers ────────────────────────────────────────────────────────────── */

/**
 * Parse a date string, treating naive UTC strings (no timezone suffix) as UTC.
 * Prevents legacy backend timestamps from being misinterpreted as local time.
 *
 * @param {string} dateStr - ISO date string from the backend
 * @returns {Date}
 */
function parseDate(dateStr) {
  if (!dateStr) return new Date();

  if (
    typeof dateStr === 'string' &&
    !dateStr.endsWith('Z') &&
    !dateStr.includes('+') &&
    /^\d{4}-\d{2}-\d{2}T/.test(dateStr)
  ) {
    return new Date(dateStr + 'Z');
  }

  return new Date(dateStr);
}

/**
 * Truncate text to a maximum length, appending an ellipsis if needed.
 *
 * @param {string} text - Input string
 * @param {number} [maxLen=40] - Maximum character count
 * @returns {string}
 */
function truncateText(text, maxLen = 40) {
  if (!text) return '';
  if (text.length <= maxLen) return text;
  return text.substring(0, maxLen).trim() + '…';
}

/* ─── Sub-components ─────────────────────────────────────────────────────── */

/**
 * A single conversation row with inline rename and a context menu for
 * rename/delete actions.
 *
 * @param {Object} props
 * @param {Object} props.conv - Conversation metadata object
 * @param {boolean} props.isActive - Whether this is the currently selected conversation
 * @param {boolean} props.isGenerating - Whether this conversation is streaming a response
 * @param {Function} props.onSelect - Called with (id) when the row is clicked
 * @param {Function} props.onDelete - Called with (id) to delete the conversation
 * @param {Function} props.onRename - Called with (id, newTitle) to rename
 * @param {number} props.index - Position in the list (used for staggered entrance animation)
 */
function ConversationItem({ conv, isActive, isGenerating, onSelect, onDelete, onRename, index }) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
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

  const handleRenameKeyDown = (e) => {
    if (e.key === 'Enter') submitRename();
    if (e.key === 'Escape') setIsRenaming(false);
  };

  useEffect(() => {
    if (!isMenuOpen) return;

    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setIsMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isMenuOpen]);

  return (
    <motion.div
      className={`conversation-item ${isActive ? 'active' : ''} ${isMenuOpen ? 'menu-open' : ''}`}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.28, ease: 'easeOut' }}
      layout
    >
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
          className={`menu-btn ${isMenuOpen ? 'active' : ''}`}
          aria-label="Conversation options"
          onClick={(e) => { e.stopPropagation(); setIsMenuOpen(prev => !prev); }}
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="12" cy="19" r="2" />
          </svg>
        </button>

        <AnimatePresence>
          {isMenuOpen && (
            <motion.div
              className="menu-dropdown menu-dropdown-open"
              initial={{ opacity: 0, scale: 0.92, y: -4 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: -4 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
            >
              <button
                className="menu-item"
                onClick={(e) => { e.stopPropagation(); setIsMenuOpen(false); startRename(e); }}
              >
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
                </svg>
                Rename
              </button>
              <button
                className="menu-item delete-item"
                onClick={(e) => { e.stopPropagation(); setIsMenuOpen(false); onDelete(conv.id); }}
              >
                <svg viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                </svg>
                Delete
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

/**
 * Bottom panel showing the logged-in user's avatar, name, and a settings button.
 *
 * @param {Object} props
 * @param {string} props.userName - Full display name
 * @param {Function} props.onOpenSettings - Called when the settings button is clicked
 */
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

/* ─── Component ──────────────────────────────────────────────────────────── */

/**
 * Collapsible conversation history sidebar. Groups conversations by Today / Past.
 *
 * @param {Object} props
 * @param {Array} props.conversations - List of conversation metadata objects
 * @param {string|null} props.currentConversationId - ID of the active conversation
 * @param {Function} props.onSelectConversation - Called with (id) to switch conversation
 * @param {Function} props.onNewConversation - Called to create a new conversation
 * @param {Function} props.onDeleteConversation - Called with (id) to delete
 * @param {Function} props.onRenameConversation - Called with (id, title) to rename
 * @param {boolean} props.isOpen - Whether the sidebar is in expanded state
 * @param {Function} props.toggleSidebar - Called to toggle open/closed
 * @param {Set} props.loadingIds - Set of conversation IDs currently generating
 * @param {string} props.userName - Logged-in user's display name
 * @param {Function} props.onOpenSettings - Called to open the settings modal
 * @param {Function} props.onGoHome - Called to deselect the active conversation
 */
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
  isLoading = false,
  userName,
  onOpenSettings,
  onGoHome,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const now = new Date();

  const isToday = (dateStr) => {
    const date = parseDate(dateStr);
    return (
      date.getFullYear() === now.getFullYear() &&
      date.getMonth() === now.getMonth() &&
      date.getDate() === now.getDate()
    );
  };

  const { todayConversations, pastConversations } = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const filtered = query
      ? conversations.filter(conv =>
          (conv.title || '').toLowerCase().includes(query) ||
          (conv.first_message || '').toLowerCase().includes(query)
        )
      : conversations;
    return {
      todayConversations: filtered.filter(conv => isToday(conv.created_at)),
      pastConversations: filtered.filter(conv => !isToday(conv.created_at)),
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversations, searchQuery]);

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

        <motion.button
          className="new-btn"
          onClick={onNewConversation}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
          </svg>
          <span>New Chat</span>
        </motion.button>
      </div>

      {isOpen && (
        <div className="sidebar-search">
          <input
            className="sidebar-search-input"
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      )}

      <div className="conversation-list" style={{ flex: 1 }}>
        {isLoading ? (
          <div className="skeleton-list">
            {SKELETON_KEYS.map(i => (
              <div key={i} className="skeleton-item">
                <div className="skeleton-line skeleton-title" />
                <div className="skeleton-line skeleton-meta" />
              </div>
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <motion.div
            style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            No history yet
          </motion.div>
        ) : todayConversations.length === 0 && pastConversations.length === 0 ? (
          <motion.div
            style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            No matches
          </motion.div>
        ) : (
          <>
            {todayConversations.length > 0 && (
              <div>
                <div className="time-group-label">Today</div>
                {todayConversations.map((conv, i) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={conv.id === currentConversationId}
                    isGenerating={loadingIds.has(conv.id)}
                    onSelect={onSelectConversation}
                    onDelete={onDeleteConversation}
                    onRename={onRenameConversation}
                    index={i}
                  />
                ))}
              </div>
            )}
            {pastConversations.length > 0 && (
              <div>
                <div className="time-group-label">Past Conversations</div>
                {pastConversations.map((conv, i) => (
                  <ConversationItem
                    key={conv.id}
                    conv={conv}
                    isActive={conv.id === currentConversationId}
                    isGenerating={loadingIds.has(conv.id)}
                    onSelect={onSelectConversation}
                    onDelete={onDeleteConversation}
                    onRename={onRenameConversation}
                    index={todayConversations.length + i}
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
