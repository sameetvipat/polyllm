import { useState } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!finalResponse) {
    return null;
  }

  const modelName = finalResponse.model.split('/')[1] || finalResponse.model;

  return (
    <motion.div
      className={`stage stage3 ${isExpanded ? 'expanded' : ''}`}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <h3 className="stage-title">The Council&#39;s Verdict</h3>

      <div className="final-response">
        <motion.div
          className="chairman-label"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ cursor: 'pointer' }}
          title={isExpanded ? "Click to collapse" : "Click to expand"}
          whileHover={{ opacity: 0.85 }}
          whileTap={{ scale: 0.98 }}
        >
          Speaker: {modelName} {isExpanded ? '▼' : '▶'}
        </motion.div>

        <motion.div
          className="final-content-wrapper"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15, duration: 0.4 }}
        >
          <div className="final-text markdown-content">
            <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
          </div>
        </motion.div>
      </div>
    </motion.div>
  );
}
