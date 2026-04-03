import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import './ChatInterface.css';

// Reconstruct label_to_model from stage1 results (labels are assigned A, B, C... in order)
function reconstructLabelToModel(stage1) {
  if (!stage1) return null;
  const map = {};
  stage1.forEach((result, i) => {
    map[`Response ${String.fromCharCode(65 + i)}`] = result.model;
  });
  return map;
}

// Reconstruct aggregate_rankings from stage2 parsed_rankings and label_to_model
function reconstructAggregateRankings(stage2, labelToModel) {
  if (!stage2 || !labelToModel) return [];
  const positions = {};
  stage2.forEach(ranking => {
    (ranking.parsed_ranking || []).forEach((label, index) => {
      const model = labelToModel[label];
      if (model) {
        if (!positions[model]) positions[model] = [];
        positions[model].push(index + 1);
      }
    });
  });
  return Object.entries(positions)
    .map(([model, pos]) => ({
      model,
      average_rank: pos.reduce((a, b) => a + b, 0) / pos.length,
      rankings_count: pos.length,
    }))
    .sort((a, b) => a.average_rank - b.average_rank);
}

function formatTime(ts) {
  if (!ts) return null;
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

const messageVariants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] } },
};

const stageLoadingVariants = {
  initial: { opacity: 0, x: -8 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.25 } },
  exit: { opacity: 0, x: 8, transition: { duration: 0.2 } },
};

export default function ChatInterface({
  conversation,
  onSendMessage,
  onStartConversation,
  onCloseChat,
  isLoading,
  userInitial = 'U',
  firstName = 'there',
  isNewUser = false,
  onStopGeneration,
}) {
  const [input, setInput] = useState('');
  const [homeInput, setHomeInput] = useState('');
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    const container = containerRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    setShowScrollBtn(false);
    const handleScroll = () => {
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      setShowScrollBtn(distanceFromBottom > 200);
    };
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  // Re-attach when conversation switches (containerRef may point to a new element)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation?.id]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleHomeSubmit = (e) => {
    e.preventDefault();
    if (homeInput.trim() && !isLoading) {
      onStartConversation?.(homeInput.trim());
      setHomeInput('');
    }
  };

  const handleHomeKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleHomeSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <motion.div
          className="home-state"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        >
          <h2 className="home-greeting">
            {isNewUser ? 'Welcome, ' : 'Welcome back, '}
            <span className="home-name">{firstName}!</span>
          </h2>
          <p className="home-subtitle">
            {isNewUser ? 'Your council is ready. Ask anything.' : 'Ask anything. The council deliberates.'}
          </p>
          <form className="home-input-form" onSubmit={handleHomeSubmit}>
            <div className="home-input-wrapper">
              <textarea
                className="home-input"
                placeholder="Ask the council..."
                value={homeInput}
                onChange={(e) => setHomeInput(e.target.value)}
                onKeyDown={handleHomeKeyDown}
                rows={1}
                autoFocus
              />
              <motion.button
                type="submit"
                className="send-button"
                disabled={!homeInput.trim() || isLoading}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <svg viewBox="0 0 24 24" className="send-icon">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </motion.button>
            </div>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <motion.button
        className="close-chat-btn"
        onClick={onCloseChat}
        aria-label="Close chat"
        title="Back to home"
        initial={{ opacity: 0, x: 8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.25, delay: 0.1 }}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.93 }}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      </motion.button>

      <AnimatePresence>
        {showScrollBtn && (
          <motion.button
            className="scroll-to-bottom-btn"
            onClick={scrollToBottom}
            aria-label="Scroll to bottom"
            initial={{ opacity: 0, y: 12, scale: 0.85 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.85 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            whileHover={{ scale: 1.1, y: -2 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>
            </svg>
          </motion.button>
        )}
      </AnimatePresence>

      <div className="messages-container" ref={containerRef}>
        {conversation.messages.length === 0 ? (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          >
            <h2>Start a Conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </motion.div>
        ) : (
          conversation.messages.map((msg, index) => (
            <motion.div
              key={msg.timestamp ? `${msg.role}-${msg.timestamp}` : `${msg.role}-${index}`}
              className="message-group"
              variants={messageVariants}
              initial="initial"
              animate="animate"
            >
              {msg.role === 'user' ? (
                <div className="user-message">
                  <div className="user-message-row">
                    <div className="user-bubble-col">
                      <div className="message-content">
                        <div className="markdown-content">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      </div>
                      {formatTime(msg.timestamp) && (
                        <div className="message-timestamp">{formatTime(msg.timestamp)}</div>
                      )}
                    </div>
                    <div className="user-avatar">{userInitial}</div>
                  </div>
                </div>
              ) : (
                <div className="assistant-message">
                  <div className="message-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <img src="/Logo.png" alt="" style={{ height: '48px', width: 'auto' }} />
                    PolyLLM Council
                    {formatTime(msg.timestamp) && (
                      <span className="message-timestamp" style={{ marginLeft: 'auto', paddingRight: '1rem' }}>
                        {formatTime(msg.timestamp)}
                      </span>
                    )}
                  </div>

                  {/* Stage 1 */}
                  <AnimatePresence>
                    {msg.loading?.stage1 && (
                      <motion.div
                        className="stage-loading"
                        variants={stageLoadingVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                      >
                        <div className="spinner"></div>
                        <span>Stage 1: Collecting individual responses...</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  <AnimatePresence>
                    {msg.loading?.stage2 && (
                      <motion.div
                        className="stage-loading"
                        variants={stageLoadingVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                      >
                        <div className="spinner"></div>
                        <span>Stage 2: Peer rankings...</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  {msg.stage2 && (() => {
                    const labelToModel = msg.metadata?.label_to_model
                      ?? reconstructLabelToModel(msg.stage1);
                    const aggregateRankings = msg.metadata?.aggregate_rankings
                      ?? reconstructAggregateRankings(msg.stage2, labelToModel);
                    return (
                      <Stage2
                        rankings={msg.stage2}
                        labelToModel={labelToModel}
                        aggregateRankings={aggregateRankings}
                      />
                    );
                  })()}

                  {/* Stage 3 */}
                  <AnimatePresence>
                    {msg.loading?.stage3 && (
                      <motion.div
                        className="stage-loading"
                        variants={stageLoadingVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                      >
                        <div className="spinner"></div>
                        <span>Stage 3: Final synthesis...</span>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </motion.div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            {/* Can add extra spinner here if needed independent of stage */}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <motion.form
        className="input-form"
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1, ease: 'easeOut' }}
      >
        <div className="input-wrapper">
          <textarea
            className="message-input"
            placeholder="Ask the council..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          <AnimatePresence mode="wait">
            {isLoading ? (
              <motion.button
                key="stop"
                type="button"
                className="stop-button"
                onClick={() => onStopGeneration?.(conversation?.id)}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.15 }}
              >
                <svg viewBox="0 0 24 24" className="send-icon">
                  <rect x="6" y="6" width="12" height="12" />
                </svg>
              </motion.button>
            ) : (
              <motion.button
                key="send"
                type="submit"
                className="send-button"
                disabled={!input.trim()}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.15 }}
              >
                <svg viewBox="0 0 24 24" className="send-icon">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                </svg>
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </motion.form>
    </div>
  );
}
