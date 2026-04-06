/* ─── Imports ────────────────────────────────────────────────────────────── */

import { useState } from 'react';
import { motion } from 'framer-motion';
import CopyButton from '../shared/CopyButton';
import MarkdownContent from '../shared/MarkdownContent';
import './Stage1.css';

/* ─── Constants ──────────────────────────────────────────────────────────── */

const CARD_VARIANTS = {
  initial: { opacity: 0, y: 20, scale: 0.97 },
  animate: (i) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.08,
      duration: 0.4,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  }),
};

/* ─── Component ──────────────────────────────────────────────────────────── */

export default function Stage1({ responses }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!responses || responses.length === 0) return null;

  const toggleExpand = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  return (
    <motion.div
      className="stage stage1"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <h3 className="stage-title">Stage 1: Council Deliberation</h3>

      <div className="responses-grid">
        {responses.map((resp, index) => {
          const modelName = resp.model.split('/')[1] || resp.model;
          const isExpanded = expandedIndex === index;

          return (
            <motion.div
              key={index}
              className={`response-card ${isExpanded ? 'active expanded' : ''}`}
              custom={index}
              variants={CARD_VARIANTS}
              initial="initial"
              animate="animate"
              whileHover={!isExpanded ? { y: -3, transition: { duration: 0.2 } } : {}}
              layout
              layoutId={`card-${index}`}
            >
              <div className="card-header" onClick={() => toggleExpand(index)}>
                <div className="model-name">
                  <div className="model-icon">
                    {modelName.substring(0, 2).toUpperCase()}
                  </div>
                  {modelName}
                </div>
                <div className="card-header-actions">
                  <CopyButton text={resp.response} className="card-copy-btn" size={13} stopPropagation />
                  <motion.div className="expand-hint" animate={{ opacity: 1 }}>
                    {isExpanded ? 'Collapse' : 'Expand'}
                  </motion.div>
                </div>
              </div>

              <MarkdownContent className="card-content markdown-content">{resp.response}</MarkdownContent>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
