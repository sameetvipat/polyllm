import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

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
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Council Deliberation</h3>

      <div className="responses-grid">
        {responses.map((resp, index) => {
          const modelName = resp.model.split('/')[1] || resp.model;
          const isExpanded = expandedIndex === index;

          return (
            <div
              key={index}
              className={`response-card ${isExpanded ? 'active expanded' : ''}`}
            >
              <div className="card-header" onClick={() => toggleExpand(index)}>
                <div className="model-name">
                  <div className="model-icon">
                    {modelName.substring(0, 2).toUpperCase()}
                  </div>
                  {modelName}
                </div>
                <div className="expand-hint">
                  {isExpanded ? 'Collapse' : 'Expand'}
                </div>
              </div>

              <div className="card-content markdown-content">
                <ReactMarkdown>{resp.response}</ReactMarkdown>
              </div>
            </div>
          );
        })}
      </div>
    </div >
  );
}
