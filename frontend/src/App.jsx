/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import Sidebar from './components/layout/Sidebar';
import ChatInterface from './components/chat/ChatInterface';
import Settings from './components/settings/Settings';
import AuthPage from './components/auth/AuthPage';
import LandingPage from './components/auth/LandingPage';
import { api } from './api';
import './App.css';

/* ─── Constants ──────────────────────────────────────────────────────────── */

const PAGE_FADE = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.35, ease: 'easeOut' } },
  exit: { opacity: 0, transition: { duration: 0.25, ease: 'easeIn' } },
};

const TOAST_DURATION_MS = 10000;
const THEME_TRANSITION_DURATION_MS = 400;

/* ─── Component ──────────────────────────────────────────────────────────── */

/**
 * Root application component. Manages auth flow, conversation state,
 * streaming message handling, and theme.
 */
function App() {
  /* ── Conversations ─────────────────────────────────────────────────────── */

  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversationsMap, setConversationsMap] = useState({});
  const [loadingIds, setLoadingIds] = useState(new Set());
  const [isConversationsLoading, setIsConversationsLoading] = useState(true);
  const abortControllersRef = useRef({});

  const currentConversation = conversationsMap[currentConversationId] || null;
  const isCurrentConvLoading = loadingIds.has(currentConversationId);

  /* ── UI State ──────────────────────────────────────────────────────────── */

  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [toast, setToast] = useState(null); // shape: { conversationId, title }

  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

  /* ── Auth ──────────────────────────────────────────────────────────────── */

  const [authUser, setAuthUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('polyllm_auth'));
    } catch {
      return null;
    }
  });

  const [isShowingAuth, setIsShowingAuth] = useState(false);
  const [isNewUser, setIsNewUser] = useState(false);
  const [firstName, setFirstName] = useState(() => authUser?.firstName || 'User');
  const [lastName, setLastName] = useState(() => authUser?.lastName || '');
  const [email, setEmail] = useState(() => authUser?.email || '');

  const userName = firstName + (lastName.trim() ? ' ' + lastName.trim() : '');

  const handleAuth = (authData, isNew = false) => {
    setAuthUser(authData);
    setIsNewUser(isNew);
    setFirstName(authData.firstName);
    setLastName(authData.lastName || '');
    setEmail(authData.email);
  };

  const handleLogout = () => {
    localStorage.removeItem('polyllm_auth');
    setAuthUser(null);
  };

  const handleSetAccountDetails = ({ firstName: fn, lastName: ln, email: em }) => {
    const trimFn = fn.trim() || 'User';
    const trimLn = ln.trim();
    const trimEm = em.trim();
    setFirstName(trimFn);
    setLastName(trimLn);
    setEmail(trimEm);
    const updated = { firstName: trimFn, lastName: trimLn, email: trimEm };
    setAuthUser(updated);
    localStorage.setItem('polyllm_auth', JSON.stringify(updated));

    // Keep polyllm_users in sync so the updated name persists across sign-outs
    try {
      const users = JSON.parse(localStorage.getItem('polyllm_users') || '[]');
      const idx = users.findIndex(u => u.email.toLowerCase() === email.toLowerCase());
      if (idx !== -1) {
        users[idx] = { ...users[idx], firstName: trimFn, lastName: trimLn, email: trimEm };
        localStorage.setItem('polyllm_users', JSON.stringify(users));
      }
    } catch {
      // polyllm_users missing or malformed — polyllm_auth update above is sufficient
    }
  };

  /* ── Theme ─────────────────────────────────────────────────────────────── */

  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    // Warm up theme-transition styles so the first toggle isn't laggy
    document.documentElement.classList.add('theme-transitioning');
    requestAnimationFrame(() => {
      document.documentElement.classList.remove('theme-transitioning');
    });
  }, []);

  const toggleTheme = () => {
    document.documentElement.classList.add('theme-transitioning');
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));
    setTimeout(
      () => document.documentElement.classList.remove('theme-transitioning'),
      THEME_TRANSITION_DURATION_MS
    );
  };

  /* ── Toast ─────────────────────────────────────────────────────────────── */

  const triggerToast = (conversationId) => {
    const conv = conversations.find(c => c.id === conversationId);
    const title = conv?.title && conv.title !== 'New Conversation' ? conv.title : 'a chat';
    setToast({ type: 'success', conversationId, title });
    setTimeout(() => setToast(null), TOAST_DURATION_MS);
  };

  const triggerErrorToast = (message) => {
    setToast({ type: 'error', message });
    setTimeout(() => setToast(null), TOAST_DURATION_MS);
  };

  /* ── Conversation Helpers ──────────────────────────────────────────────── */

  const updateConvById = (id, updater) => {
    setConversationsMap(prev => {
      const conv = prev[id] || {
        id,
        created_at: new Date().toISOString(),
        title: 'New Conversation',
        messages: [],
      };
      return { ...prev, [id]: updater(conv) };
    });
  };

  /* ── Data Loading ──────────────────────────────────────────────────────── */

  useEffect(() => { loadConversations(); }, []);

  useEffect(() => {
    if (currentConversationId && !conversationsMap[currentConversationId]) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
    } catch {
      // silently ignore — UI shows empty state
    } finally {
      setIsConversationsLoading(false);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setConversationsMap(prev => ({ ...prev, [id]: conv }));
    } catch {
      // silently ignore — conversation stays in cache
    }
  };

  /* ── Conversation Actions ──────────────────────────────────────────────── */

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations(prev => [
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...prev,
      ]);
      setConversationsMap(prev => ({ ...prev, [newConv.id]: newConv }));
      setCurrentConversationId(newConv.id);
    } catch {
      // silently ignore
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await api.renameConversation(id, newTitle);
      setConversations(prev =>
        prev.map(c => (c.id === id ? { ...c, title: newTitle } : c))
      );
    } catch {
      // silently ignore
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations(prev => prev.filter(c => c.id !== id));
      setConversationsMap(prev => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      if (id === currentConversationId) setCurrentConversationId(null);
    } catch {
      // silently ignore
    }
  };

  // Create a new conversation and immediately send the first message (home screen shortcut)
  const handleStartConversation = async (content) => {
    try {
      const newConv = await api.createConversation();
      const convId = newConv.id;
      setConversations(prev => [
        { id: convId, created_at: newConv.created_at, message_count: 0 },
        ...prev,
      ]);
      setConversationsMap(prev => ({ ...prev, [convId]: newConv }));
      setCurrentConversationId(convId);
      // Use convId directly — don't wait for state to settle
      await handleSendMessage(content, convId);
    } catch {
      // silently ignore
    }
  };

  /* ── Message Streaming ─────────────────────────────────────────────────── */

  const handleSendMessage = async (content, conversationIdOverride = null) => {
    const conversationId = conversationIdOverride ?? currentConversationId;
    if (!conversationId) return;

    const abortController = new AbortController();
    abortControllersRef.current[conversationId] = abortController;
    setLoadingIds(prev => new Set(prev).add(conversationId));

    // Optimistically add user message
    const userMessage = { role: 'user', content, timestamp: new Date().toISOString() };
    updateConvById(conversationId, conv => ({
      ...conv,
      messages: [...conv.messages, userMessage],
    }));

    setConversations(prev =>
      prev.map(c => {
        if (c.id === conversationId && !c.first_message && (!c.message_count || c.message_count === 0)) {
          return { ...c, first_message: content, message_count: 1 };
        }
        return c;
      })
    );

    // Add placeholder assistant message with loading flags
    const assistantMessage = {
      role: 'assistant',
      stage1: null,
      stage2: null,
      stage3: null,
      metadata: null,
      loading: { stage1: false, stage2: false, stage3: false },
    };
    updateConvById(conversationId, conv => ({
      ...conv,
      messages: [...conv.messages, assistantMessage],
    }));

    const markLoading = (stage) =>
      updateConvById(conversationId, conv => ({
        ...conv,
        messages: conv.messages.map((m, i) =>
          i === conv.messages.length - 1
            ? { ...m, loading: { ...m.loading, [stage]: true } }
            : m
        ),
      }));

    const removeLoadingIds = () => {
      setLoadingIds(prev => {
        const next = new Set(prev);
        next.delete(conversationId);
        return next;
      });
    };

    try {
      await api.sendMessageStream(conversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            markLoading('stage1');
            break;

          case 'stage1_complete':
            updateConvById(conversationId, conv => ({
              ...conv,
              messages: conv.messages.map((m, i) =>
                i === conv.messages.length - 1
                  ? { ...m, stage1: event.data, loading: { ...m.loading, stage1: false } }
                  : m
              ),
            }));
            break;

          case 'stage2_start':
            markLoading('stage2');
            break;

          case 'stage2_complete':
            updateConvById(conversationId, conv => ({
              ...conv,
              messages: conv.messages.map((m, i) =>
                i === conv.messages.length - 1
                  ? { ...m, stage2: event.data, metadata: event.metadata, loading: { ...m.loading, stage2: false } }
                  : m
              ),
            }));
            break;

          case 'stage3_start':
            markLoading('stage3');
            break;

          case 'stage3_complete':
            updateConvById(conversationId, conv => ({
              ...conv,
              messages: conv.messages.map((m, i) =>
                i === conv.messages.length - 1
                  ? { ...m, stage3: event.data, loading: { ...m.loading, stage3: false }, timestamp: new Date().toISOString() }
                  : m
              ),
            }));
            break;

          case 'title_complete':
            loadConversations();
            break;

          case 'complete':
            loadConversations();
            removeLoadingIds();
            triggerToast(conversationId);
            break;

          case 'error':
            removeLoadingIds();
            triggerErrorToast(event.message || 'Something went wrong. Please try again.');
            break;
        }
      }, abortController.signal);
    } catch (error) {
      if (error.name !== 'AbortError') {
        triggerErrorToast('Failed to reach the council. Please check your connection.');
        // Roll back the optimistic messages on hard failure
        updateConvById(conversationId, conv => ({
          ...conv,
          messages: conv.messages.slice(0, -2),
        }));
      } else {
        // Clear spinners and show stopped state
        updateConvById(conversationId, conv => ({
          ...conv,
          messages: conv.messages.map((m, i) => {
            if (i !== conv.messages.length - 1) return m;
            return {
              ...m,
              loading: { stage1: false, stage2: false, stage3: false },
              stage3: m.stage3 ? m.stage3 : {
                model: 'system',
                response: (m.stage2 || m.stage1)
                  ? '*Generation stopped by user*'
                  : '*Generation stopped before receiving response*',
              },
            };
          }),
        }));
      }
      removeLoadingIds();
    } finally {
      delete abortControllersRef.current[conversationId];
    }
  };

  const handleStopGeneration = (conversationId) => {
    abortControllersRef.current[conversationId]?.abort();
  };

  /* ── Render ────────────────────────────────────────────────────────────── */

  const pageKey = !authUser && !isShowingAuth ? 'landing' : !authUser ? 'auth' : 'app';

  return (
    <AnimatePresence mode="wait">
      {pageKey === 'landing' && (
        <motion.div key="landing" {...PAGE_FADE} style={{ width: '100vw', height: '100vh' }}>
          <LandingPage onGetStarted={() => setIsShowingAuth(true)} theme={theme} toggleTheme={toggleTheme} />
        </motion.div>
      )}

      {pageKey === 'auth' && (
        <motion.div
          key="auth"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } }}
          exit={{ opacity: 0, y: -20, transition: { duration: 0.25, ease: 'easeIn' } }}
          style={{ width: '100vw', height: '100vh' }}
        >
          <AuthPage onAuth={handleAuth} onBack={() => setIsShowingAuth(false)} />
        </motion.div>
      )}

      {pageKey === 'app' && (
        <motion.div
          key="app"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1, transition: { duration: 0.3, ease: 'easeOut' } }}
          exit={{ opacity: 0, transition: { duration: 0.2 } }}
          style={{ width: '100vw', height: '100vh' }}
        >
          <div className={`app ${isSidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
            <AnimatePresence>
              {toast && (
                <motion.div
                  className={`toast ${toast.type === 'error' ? 'toast-error' : ''}`}
                  initial={{ opacity: 0, y: 16, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 16, scale: 0.95 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                >
                  {toast.type === 'error' ? (
                    <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18" style={{ flexShrink: 0, color: '#ff6b6b' }}>
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                  ) : (
                    <img src="/Logo.png" alt="" className="toast-icon" />
                  )}
                  <span>
                    {toast.type === 'error'
                      ? toast.message
                      : <>Response ready{toast.conversationId !== currentConversationId ? ` in "${toast.title}"` : ''}</>
                    }
                  </span>
                  {toast.type !== 'error' && toast.conversationId !== currentConversationId && (
                    <button
                      className="toast-link"
                      onClick={() => {
                        handleSelectConversation(toast.conversationId);
                        setToast(null);
                      }}
                    >
                      View →
                    </button>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            <Settings
              isOpen={isSettingsOpen}
              onClose={() => setIsSettingsOpen(false)}
              firstName={firstName}
              lastName={lastName}
              email={email}
              onSetAccountDetails={handleSetAccountDetails}
              theme={theme}
              toggleTheme={toggleTheme}
              onSignOut={handleLogout}
            />

            <Sidebar
              conversations={conversations}
              currentConversationId={currentConversationId}
              onSelectConversation={handleSelectConversation}
              onNewConversation={handleNewConversation}
              onDeleteConversation={handleDeleteConversation}
              onRenameConversation={handleRenameConversation}
              isOpen={isSidebarOpen}
              toggleSidebar={toggleSidebar}
              loadingIds={loadingIds}
              isLoading={isConversationsLoading}
              userName={userName}
              onOpenSettings={() => setIsSettingsOpen(true)}
              onGoHome={() => setCurrentConversationId(null)}
            />

            <div className="main-content">
              <ChatInterface
                conversation={currentConversation}
                onSendMessage={handleSendMessage}
                onStartConversation={handleStartConversation}
                onCloseChat={() => setCurrentConversationId(null)}
                isLoading={isCurrentConvLoading}
                userInitial={userName.trim().charAt(0).toUpperCase()}
                firstName={firstName}
                isNewUser={isNewUser}
                onStopGeneration={handleStopGeneration}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ─── Exports ────────────────────────────────────────────────────────────── */

export default App;
