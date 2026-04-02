import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with the actual model name
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  // Select the first reviewer by default
  const [activeReviewerIndex, setActiveReviewerIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  const sortedAggregate = [...(aggregateRankings || [])].sort((a, b) => a.average_rank - b.average_rank);
  const maxScore = sortedAggregate.length > 0 ? Math.max(...sortedAggregate.map(a => a.average_rank)) : 10;
  // Invert score for visual bar (lower rank is better, so 1 should be full bar)
  // Let's just show rank number clearly instead of a bar for simplicity in this version, or minimal bar.

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Review & Ranking</h3>

      {/* 1. Leaderboard Section */}
      {sortedAggregate.length > 0 && (
        <div className="leaderboard">
          <div className="leaderboard-header">
            <span className="leaderboard-title">Consensus Ranking (Lower is Better)</span>
          </div>
          <div className="leaderboard-list">
            {sortedAggregate.map((agg, idx) => {
              const modelName = agg.model.split('/')[1] || agg.model;
              const rank = idx + 1;
              return (
                <div key={idx} className="leaderboard-item">
                  <div className={`rank-badge top-${rank}`}>
                    {rank}
                  </div>
                  <div className="model-info">
                    <span className="model-name">{modelName}</span>
                  </div>
                  <div className="score-value">
                    Avg: {agg.average_rank.toFixed(1)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 2. Detailed Reviews Section */}
      <h4 className="stage2-subtitle">Detailed Critiques</h4>
      <div className={`reviews-section ${isExpanded ? 'expanded' : ''}`}>
        {/* Sidebar for selecting reviewer */}
        <div className="reviews-sidebar">
          {rankings.map((rank, index) => (
            <button
              key={index}
              className={`review-tab-btn ${activeReviewerIndex === index ? 'active' : ''}`}
              onClick={() => setActiveReviewerIndex(index)}
            >
              Reviewer: {rank.model.split('/')[1] || rank.model}
            </button>
          ))}
        </div>

        {/* Content Panel */}
        <div className="review-content-panel">
          <div className="reviewer-header" onClick={() => setIsExpanded(!isExpanded)} style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Perspective: {rankings[activeReviewerIndex].model.split('/')[1]}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {isExpanded ? 'Collapse' : 'Expand'}
            </span>
          </div>

          <div className="review-scroll-container">
            {/* Parsed Ranking Display (if available) */}
            {rankings[activeReviewerIndex].parsed_ranking &&
              rankings[activeReviewerIndex].parsed_ranking.length > 0 && (
                <div className="parsed-ranking">
                  <strong>Extracted Ranking:</strong>
                  <ol>
                    {rankings[activeReviewerIndex].parsed_ranking.map((label, i) => (
                      <li key={i}>
                        {labelToModel && labelToModel[label]
                          ? labelToModel[label].split('/')[1] || labelToModel[label]
                          : label}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

            <div className="ranking-content markdown-content">
              <ReactMarkdown>
                {deAnonymizeText(rankings[activeReviewerIndex].ranking, labelToModel)}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    </div >
  );
}
