/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import MarkdownContent from '../shared/MarkdownContent';
import CopyButton from '../shared/CopyButton';
import './Stage3.css';

/* ─── Component ──────────────────────────────────────────────────────────── */

/**
 * Displays the Stage 3 chairman's final response.
 *
 * Supports two layouts:
 *  - New format: separate `review` (Gemini) + `synthesis` (custom model) fields
 *  - Legacy format: single `response` field (backward compat with stored conversations)
 *
 * @param {Object} props
 * @param {Object} props.finalResponse - Stage 3 result object
 */
export default function Stage3({ finalResponse }) {
  // All hooks at the top — no conditional hook calls
  const [reviewExpanded, setReviewExpanded] = useState(false);
  const [legacyExpanded, setLegacyExpanded] = useState(false);

  if (!finalResponse) return null;

  const hasNewFormat = finalResponse.review && finalResponse.synthesis;

  if (hasNewFormat) {
    const reviewModelName =
      (finalResponse.review_model || '').split('/')[1] || finalResponse.review_model || 'Gemini';
    const synthesisModelName =
      (finalResponse.synthesis_model || 'arsh1030/polyllm-chairman').split('/').pop();

    return (
      <motion.div
        className="stage stage3"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
        <h3 className="stage-title">The Council&apos;s Verdict</h3>

        {/* ── Stage 3A: Council Review (Gemini) — collapsible ── */}
        <div className="chairman-panel review-panel">
          <button
            className="panel-header"
            onClick={() => setReviewExpanded(prev => !prev)}
          >
            <span className="panel-badge review-badge">Council Review</span>
            <span className="panel-model">{reviewModelName}</span>
            <span className="panel-chevron">{reviewExpanded ? '▼' : '▶'}</span>
          </button>

          <AnimatePresence>
            {reviewExpanded && (
              <motion.div
                className="panel-body"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.28, ease: 'easeInOut' }}
                style={{ overflow: 'hidden' }}
              >
                <MarkdownContent className="panel-content markdown-content">{finalResponse.review}</MarkdownContent>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* ── Stage 3B: Chairman's Verdict (Custom Model) — always shown ── */}
        <div className="chairman-panel verdict-panel">
          <div className="panel-header" style={{ cursor: 'default' }}>
            <span className="panel-badge verdict-badge">Chairman&apos;s Verdict</span>
            <span className="panel-model">{synthesisModelName}</span>
            <CopyButton text={finalResponse.synthesis} className="card-copy-btn" size={13} />
          </div>

          <motion.div
            className="panel-body"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.35 }}
          >
            <MarkdownContent className="panel-content markdown-content">{finalResponse.synthesis}</MarkdownContent>
          </motion.div>
        </div>
      </motion.div>
    );
  }

  /* ── Legacy format fallback (stored conversations before the split) ── */
  const modelName = (finalResponse.model || '').split('/')[1] || finalResponse.model;

  return (
    <motion.div
      className={`stage stage3 ${legacyExpanded ? 'expanded' : ''}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <h3 className="stage-title">The Council&apos;s Verdict</h3>

      <div className="final-response">
        <motion.div
          className="chairman-label"
          onClick={() => setLegacyExpanded(!legacyExpanded)}
          style={{ cursor: 'pointer' }}
          title={legacyExpanded ? 'Click to collapse' : 'Click to expand'}
          whileHover={{ opacity: 0.85 }}
          whileTap={{ scale: 0.98 }}
        >
          Speaker: {modelName} {legacyExpanded ? '▼' : '▶'}
          <CopyButton text={finalResponse.response} className="card-copy-btn" size={13} stopPropagation />
        </motion.div>

        <motion.div
          className="final-content-wrapper"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.4 }}
        >
          <MarkdownContent className="final-text markdown-content">{finalResponse.response}</MarkdownContent>
        </motion.div>
      </div>
    </motion.div>
  );
}
