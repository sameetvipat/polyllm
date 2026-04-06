/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import Stage3 from './Stage3';
import CopyButton from '../shared/CopyButton';
import MarkdownContent from '../shared/MarkdownContent';
import './ChatInterface.css';

/* ─── Constants ──────────────────────────────────────────────────────────── */

const SCROLL_THRESHOLD_PX = 200;

const EXAMPLE_PROMPTS = [
  'Explain quantum entanglement simply',
  'What are the best practices for REST API design?',
  'Compare React, Vue, and Svelte',
  'How does the attention mechanism in transformers work?',
];

const MESSAGE_VARIANTS = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] } },
};

const STAGE_LOADING_VARIANTS = {
  initial: { opacity: 0, x: -8 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.25 } },
  exit: { opacity: 0, x: 8, transition: { duration: 0.2 } },
};

/* ─── Helpers ────────────────────────────────────────────────────────────── */

/**
 * Reconstruct the label→model mapping from Stage 1 results.
 * Labels are assigned alphabetically (A, B, C…) in the order models responded.
 *
 * @param {Array|null} stage1 - Stage 1 results array
 * @returns {Object|null} Map of "Response X" → model identifier
 */
function reconstructLabelToModel(stage1) {
  if (!stage1) return null;
  return Object.fromEntries(
    stage1.map((result, i) => [`Response ${String.fromCharCode(65 + i)}`, result.model])
  );
}

/**
 * Reconstruct aggregate rankings from Stage 2 parsed rankings and the label→model map.
 * Used when metadata is not available in persisted messages.
 *
 * @param {Array|null} stage2 - Stage 2 results array
 * @param {Object|null} labelToModel - Map of "Response X" → model identifier
 * @returns {Array} Sorted aggregate ranking objects
 */
function reconstructAggregateRankings(stage2, labelToModel) {
  if (!stage2 || !labelToModel) return [];

  const positions = {};
  stage2.forEach(ranking => {
    (ranking.parsed_ranking || []).forEach((label, index) => {
      const model = labelToModel[label];
      if (!model) return;
      if (!positions[model]) positions[model] = [];
      positions[model].push(index + 1);
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

/**
 * Format a timestamp string as a short HH:MM time string.
 *
 * @param {string|null} ts - ISO timestamp string
 * @returns {string|null} Formatted time, or null if timestamp is falsy
 */
function formatTime(ts) {
  if (!ts) return null;
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* ─── Component ──────────────────────────────────────────────────────────── */

/**
 * Main chat interface. Displays conversation messages with progressive stage
 * rendering, scroll controls, and a send/stop input form.
 *
 * @param {Object} props
 * @param {Object|null} props.conversation - Active conversation data
 * @param {Function} props.onSendMessage - Called with (content) to send a message
 * @param {Function} props.onStartConversation - Called with (content) to begin a new conversation from home
 * @param {Function} props.onCloseChat - Called to dismiss the active conversation
 * @param {boolean} props.isLoading - Whether the current conversation is generating
 * @param {string} props.userInitial - Single character for the user avatar
 * @param {string} props.firstName - User's first name for the greeting
 * @param {boolean} props.isNewUser - Whether to show new-user welcome copy
 * @param {Function} props.onStopGeneration - Called with (conversationId) to abort generation
 */
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
  const [isScrollBtnVisible, setIsScrollBtnVisible] = useState(false);

  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  /* ── Scroll Behaviour ────────────────────────────────────────────────── */

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

    setIsScrollBtnVisible(false);

    const handleScroll = () => {
      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight;
      setIsScrollBtnVisible(distanceFromBottom > SCROLL_THRESHOLD_PX);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
    // Re-attach when conversation switches so the listener targets the correct DOM node
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation?.id]);

  /* ── Form Handlers ───────────────────────────────────────────────────── */

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
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

  /* ── Home Screen (no active conversation) ────────────────────────────── */

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

  /* ── Conversation View ───────────────────────────────────────────────── */

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
        {isScrollBtnVisible && (
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
            <div className="example-prompts">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  className="example-prompt-chip"
                  onClick={() => setInput(prompt)}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </motion.div>
        ) : (
          conversation.messages.map((msg, index) => {
            const messageKey = msg.timestamp
              ? `${msg.role}-${msg.timestamp}`
              : `${msg.role}-${index}`;

            return (
              <motion.div
                key={messageKey}
                className="message-group"
                variants={MESSAGE_VARIANTS}
                initial="initial"
                animate="animate"
              >
                {msg.role === 'user' ? (
                  <UserMessage msg={msg} userInitial={userInitial} />
                ) : (
                  <AssistantMessage msg={msg} />
                )}
              </motion.div>
            );
          })
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

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function UserMessage({ msg, userInitial }) {
  const formattedTime = formatTime(msg.timestamp);

  return (
    <div className="user-message">
      <div className="user-message-row">
        <div className="user-bubble-col">
          <div className="message-content">
            <CopyButton text={msg.content} />
            <MarkdownContent>{msg.content}</MarkdownContent>
          </div>
          {formattedTime && (
            <div className="message-timestamp">{formattedTime}</div>
          )}
        </div>
        <div className="user-avatar">{userInitial}</div>
      </div>
    </div>
  );
}

/**
 * Renders a full 3-stage assistant message with loading indicators.
 *
 * @param {Object} props
 * @param {Object} props.msg - Message object with stage1, stage2, stage3, loading, metadata
 */
function AssistantMessage({ msg }) {
  const labelToModel = msg.metadata?.label_to_model ?? reconstructLabelToModel(msg.stage1);
  const aggregateRankings =
    msg.metadata?.aggregate_rankings ?? reconstructAggregateRankings(msg.stage2, labelToModel);

  return (
    <div className="assistant-message">
      <div className="message-label" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <img src="/Logo.png" alt="" style={{ height: '48px', width: 'auto' }} />
        PolyLLM Council
      </div>

      <AnimatePresence>
        {msg.loading?.stage1 && (
          <StageLoadingIndicator label="Stage 1: Collecting individual responses..." />
        )}
      </AnimatePresence>
      {msg.stage1 && <Stage1 responses={msg.stage1} />}

      <AnimatePresence>
        {msg.loading?.stage2 && (
          <StageLoadingIndicator label="Stage 2: Peer rankings..." />
        )}
      </AnimatePresence>
      {msg.stage2 && (
        <Stage2
          rankings={msg.stage2}
          labelToModel={labelToModel}
          aggregateRankings={aggregateRankings}
        />
      )}

      <AnimatePresence>
        {msg.loading?.stage3 && (
          <StageLoadingIndicator label="Stage 3: Final synthesis..." />
        )}
      </AnimatePresence>
      {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
    </div>
  );
}

/**
 * Animated loading indicator shown while a stage is in progress.
 *
 * @param {Object} props
 * @param {string} props.label - Text describing the stage being processed
 */
function StageLoadingIndicator({ label }) {
  return (
    <motion.div
      className="stage-loading"
      variants={STAGE_LOADING_VARIANTS}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <div className="spinner"></div>
      <span>{label}</span>
    </motion.div>
  );
}
