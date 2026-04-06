/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import MarkdownContent from '../shared/MarkdownContent';
import './Stage2.css';

/* ─── Constants ──────────────────────────────────────────────────────────── */

const LEADERBOARD_ITEM_VARIANTS = {
  initial: { opacity: 0, x: -16 },
  animate: (i) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.07, duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] },
  }),
};

/* ─── Helpers ────────────────────────────────────────────────────────────── */

/**
 * Replace anonymous response labels ("Response A") with bolded model short-names
 * for display in the review text. Original evaluation used anonymous labels.
 *
 * @param {string} text - Raw evaluation text
 * @param {Object|null} labelToModel - Map of "Response X" → model identifier
 * @returns {string} Text with labels replaced by **modelShortName**
 */
function deAnonymizeText(text, labelToModel) {
  if (!labelToModel) return text;

  let result = text;
  Object.entries(labelToModel).forEach(([label, model]) => {
    const modelShortName = model.split('/')[1] || model;
    result = result.replace(new RegExp(label, 'g'), `**${modelShortName}**`);
  });
  return result;
}

/* ─── Component ──────────────────────────────────────────────────────────── */

/**
 * Displays Stage 2 peer rankings: a leaderboard of consensus scores and
 * a tabbed panel of detailed critiques from each reviewer.
 *
 * @param {Object} props
 * @param {Array} props.rankings - Stage 2 results, each with { model, ranking, parsed_ranking }
 * @param {Object} props.labelToModel - Map of "Response X" → model identifier
 * @param {Array} props.aggregateRankings - Pre-sorted aggregate ranking objects
 */
export default function Stage2({ rankings, labelToModel, aggregateRankings }) {
  const [activeReviewerIndex, setActiveReviewerIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);

  if (!rankings || rankings.length === 0) return null;

  // aggregateRankings arrives pre-sorted (lowest avg rank = best); use directly
  const sortedAggregate = aggregateRankings || [];

  return (
    <motion.div
      className="stage stage2"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <h3 className="stage-title">Stage 2: Peer Review &amp; Ranking</h3>

      {/* Leaderboard */}
      {sortedAggregate.length > 0 && (
        <motion.div
          className="leaderboard"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <div className="leaderboard-header">
            <span className="leaderboard-title">Consensus Ranking (Lower is Better)</span>
          </div>
          <div className="leaderboard-list">
            {sortedAggregate.map((agg, idx) => {
              const modelName = agg.model.split('/')[1] || agg.model;
              const rank = idx + 1;
              return (
                <motion.div
                  key={idx}
                  className="leaderboard-item"
                  custom={idx}
                  variants={LEADERBOARD_ITEM_VARIANTS}
                  initial="initial"
                  animate="animate"
                >
                  <div className={`rank-badge top-${rank}`}>{rank}</div>
                  <div className="model-info">
                    <span className="model-name">{modelName}</span>
                  </div>
                  <div className="score-value">Avg: {agg.average_rank.toFixed(1)}</div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Detailed Critiques */}
      <h4 className="stage2-subtitle">Detailed Critiques</h4>
      <div className={`reviews-section ${isExpanded ? 'expanded' : ''}`}>
        <div className="reviews-sidebar">
          {rankings.map((rank, index) => (
            <motion.button
              key={index}
              className={`review-tab-btn ${activeReviewerIndex === index ? 'active' : ''}`}
              onClick={() => setActiveReviewerIndex(index)}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.06 + 0.2, duration: 0.28 }}
              whileHover={{ x: 2 }}
              whileTap={{ scale: 0.97 }}
            >
              Reviewer: {rank.model.split('/')[1] || rank.model}
            </motion.button>
          ))}
        </div>

        <div className="review-content-panel">
          <div
            className="reviewer-header"
            onClick={() => setIsExpanded(!isExpanded)}
            style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <span>Perspective: {rankings[activeReviewerIndex].model.split('/')[1]}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {isExpanded ? 'Collapse' : 'Expand'}
            </span>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeReviewerIndex}
              className="review-scroll-container"
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
            >
              {rankings[activeReviewerIndex].parsed_ranking?.length > 0 && (
                <div className="parsed-ranking">
                  <strong>Extracted Ranking:</strong>
                  <ol>
                    {rankings[activeReviewerIndex].parsed_ranking.map((label, i) => (
                      <li key={i}>
                        {labelToModel?.[label]
                          ? (labelToModel[label].split('/')[1] || labelToModel[label])
                          : label}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <MarkdownContent className="ranking-content markdown-content">
                {deAnonymizeText(rankings[activeReviewerIndex].ranking, labelToModel)}
              </MarkdownContent>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
