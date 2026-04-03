import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import Settings from './components/Settings';
import AuthPage from './components/AuthPage';
import LandingPage from './components/LandingPage';
import { api } from './api';
import './App.css';

const pageFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.35, ease: 'easeOut' } },
  exit: { opacity: 0, transition: { duration: 0.25, ease: 'easeIn' } },
};

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  // Map of id -> full conversation data (keyed so background streams update the right one)
  const [conversationsMap, setConversationsMap] = useState({});
  // Set of conversation IDs currently being generated
  const [loadingIds, setLoadingIds] = useState(new Set());
  const abortControllersRef = useRef({});
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [toast, setToast] = useState(null); // { conversationId, title }

  const currentConversation = conversationsMap[currentConversationId] || null;
  const isLoading = loadingIds.has(currentConversationId);

  const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  const [authUser, setAuthUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('polyllm_auth')); } catch { return null; }
  });
  const [showAuth, setShowAuth] = useState(false);
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
  };
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Warm up theme-transitioning styles so first toggle isn't laggy
  useEffect(() => {
    document.documentElement.classList.add('theme-transitioning');
    requestAnimationFrame(() => {
      document.documentElement.classList.remove('theme-transitioning');
    });
  }, []);
  const toggleTheme = () => {
    document.documentElement.classList.add('theme-transitioning');
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
    setTimeout(() => document.documentElement.classList.remove('theme-transitioning'), 400);
  };

  const triggerToast = (conversationId) => {
    const conv = conversations.find(c => c.id === conversationId);
    const title = conv?.title && conv.title !== 'New Conversation' ? conv.title : 'a chat';
    setToast({ conversationId, title });
    setTimeout(() => setToast(null), 10000);
  };

  // Helper: update a specific conversation in the map by ID
  const updateConvById = (id, updater) => {
    setConversationsMap(prev => {
      const conv = prev[id];
      if (!conv) return prev;
      return { ...prev, [id]: updater(conv) };
    });
  };

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
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setConversationsMap(prev => ({ ...prev, [id]: conv }));
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setConversations(prev => [
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...prev,
      ]);
      setConversationsMap(prev => ({ ...prev, [newConv.id]: newConv }));
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await api.renameConversation(id, newTitle);
      setConversations(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
    } catch (error) {
      console.error('Failed to rename conversation:', error);
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
      if (id === currentConversationId) {
        setCurrentConversationId(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // Create a new conversation and immediately send the first message (used from empty state)
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
      // Send immediately using convId directly — don't wait for state to settle
      await handleSendMessage(content, convId);
    } catch (error) {
      console.error('Failed to start conversation:', error);
    }
  };

  const handleSendMessage = async (content, conversationIdOverride = null) => {
    const resolvedId = conversationIdOverride ?? currentConversationId;
    if (!resolvedId) return;

    // Capture ID at the time of sending — stays correct even if user switches chat
    const conversationId = resolvedId;

    const abortController = new AbortController();
    abortControllersRef.current[conversationId] = abortController;
    setLoadingIds(prev => new Set(prev).add(conversationId));

    try {
      // Optimistically add user message
      const userMessage = { role: 'user', content, timestamp: new Date().toISOString() };
      updateConvById(conversationId, conv => ({
        ...conv,
        messages: [...conv.messages, userMessage],
      }));

      setConversations(prev => prev.map(c => {
        if (c.id === conversationId && !c.first_message && (!c.message_count || c.message_count === 0)) {
          return { ...c, first_message: content, message_count: 1 };
        }
        return c;
      }));

      // Add partial assistant message
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

      await api.sendMessageStream(conversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1 ? { ...m, loading: { ...m.loading, stage1: true } } : m
              );
              return { ...conv, messages };
            });
            break;

          case 'stage1_complete':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1 ? { ...m, stage1: event.data, loading: { ...m.loading, stage1: false } } : m
              );
              return { ...conv, messages };
            });
            break;

          case 'stage2_start':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1 ? { ...m, loading: { ...m.loading, stage2: true } } : m
              );
              return { ...conv, messages };
            });
            break;

          case 'stage2_complete':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1
                  ? { ...m, stage2: event.data, metadata: event.metadata, loading: { ...m.loading, stage2: false } }
                  : m
              );
              return { ...conv, messages };
            });
            break;

          case 'stage3_start':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1 ? { ...m, loading: { ...m.loading, stage3: true } } : m
              );
              return { ...conv, messages };
            });
            break;

          case 'stage3_complete':
            updateConvById(conversationId, conv => {
              const messages = conv.messages.map((m, i) =>
                i === conv.messages.length - 1
                  ? { ...m, stage3: event.data, loading: { ...m.loading, stage3: false }, timestamp: new Date().toISOString() }
                  : m
              );
              return { ...conv, messages };
            });
            break;

          case 'title_complete':
            loadConversations();
            break;

          case 'complete':
            loadConversations();
            setLoadingIds(prev => { const next = new Set(prev); next.delete(conversationId); return next; });
            triggerToast(conversationId);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setLoadingIds(prev => { const next = new Set(prev); next.delete(conversationId); return next; });
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      }, abortController.signal);
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Failed to send message:', error);
        updateConvById(conversationId, conv => ({
          ...conv,
          messages: conv.messages.slice(0, -2),
        }));
      } else {
        // Explicitly clear all loading spinners and indicate stopped
        updateConvById(conversationId, conv => ({
          ...conv,
          messages: conv.messages.map((m, i) =>
            i === conv.messages.length - 1
              ? {
                  ...m,
                  loading: { stage1: false, stage2: false, stage3: false },
                  stage3: m.stage3 ? m.stage3 : {
                    model: "system",
                    response: (m.stage2 || m.stage1 ? "*Generation stopped by user*" : "*Generation stopped before receiving response*")
                  }
                }
              : m
          ),
        }));
      }
      setLoadingIds(prev => { const next = new Set(prev); next.delete(conversationId); return next; });
    } finally {
      delete abortControllersRef.current[conversationId];
    }
  };

  const handleStopGeneration = (conversationId) => {
    abortControllersRef.current[conversationId]?.abort();
  };

  // Determine current page key for AnimatePresence
  const pageKey = !authUser && !showAuth ? 'landing' : !authUser ? 'auth' : 'app';

  return (
    <AnimatePresence mode="wait">
      {pageKey === 'landing' && (
        <motion.div key="landing" {...pageFade} style={{ width: '100vw', height: '100vh' }}>
          <LandingPage onGetStarted={() => setShowAuth(true)} theme={theme} toggleTheme={toggleTheme} />
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
          <AuthPage onAuth={handleAuth} onBack={() => setShowAuth(false)} />
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
                  className="toast"
                  initial={{ opacity: 0, y: 16, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 16, scale: 0.95 }}
                  transition={{ duration: 0.28, ease: 'easeOut' }}
                >
                  <img src="/Logo.png" alt="" className="toast-icon" />
                  <span>Response ready{toast.conversationId !== currentConversationId ? ` in "${toast.title}"` : ''}</span>
                  {toast.conversationId !== currentConversationId && (
                    <button
                      className="toast-link"
                      onClick={() => { handleSelectConversation(toast.conversationId); setToast(null); }}
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
                isLoading={isLoading}
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

export default App;
