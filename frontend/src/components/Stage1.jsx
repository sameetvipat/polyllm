import { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

const cardVariants = {
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

export default function Stage1({ responses }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!responses || responses.length === 0) {
    return null;
  }

  const toggleExpand = (index) => {
    if (expandedIndex === index) {
      setExpandedIndex(null);
    } else {
      setExpandedIndex(index);
    }
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
              variants={cardVariants}
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
                <motion.div
                  className="expand-hint"
                  animate={{ opacity: 1 }}
                >
                  {isExpanded ? 'Collapse' : 'Expand'}
                </motion.div>
              </div>

              <div className="card-content markdown-content">
                <ReactMarkdown>{resp.response}</ReactMarkdown>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
