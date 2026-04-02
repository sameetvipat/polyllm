import { useState, useEffect, useRef } from 'react';
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

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  userInitial = 'U',
}) {
  const [input, setInput] = useState('');
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const handleScroll = () => {
      const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
      setShowScrollBtn(distanceFromBottom > 200);
    };
    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

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

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to PolyLLM Council</h2>
          <p>Create a new conversation to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      {showScrollBtn && (
        <button className="scroll-to-bottom-btn" onClick={scrollToBottom} aria-label="Scroll to bottom">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/>
          </svg>
        </button>
      )}
      <div className="messages-container" ref={containerRef}>
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Start a Conversation</h2>
            <p>Ask a question to consult the LLM Council</p>
          </div>
        ) : (
          conversation.messages.map((msg, index) => (
            <div key={index} className="message-group">
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
                  {msg.loading?.stage1 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 1: Collecting individual responses...</span>
                    </div>
                  )}
                  {msg.stage1 && <Stage1 responses={msg.stage1} />}

                  {/* Stage 2 */}
                  {msg.loading?.stage2 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 2: Peer rankings...</span>
                    </div>
                  )}
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
                  {msg.loading?.stage3 && (
                    <div className="stage-loading">
                      <div className="spinner"></div>
                      <span>Stage 3: Final synthesis...</span>
                    </div>
                  )}
                  {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}
                </div>
              )}
            </div>
          ))
        )}

        {isLoading && (
          <div className="loading-indicator">
            {/* Can add extra spinner here if needed independent of stage */}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
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
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            <svg viewBox="0 0 24 24" className="send-icon">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </form>
    </div>
  );
}
