import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!finalResponse) {
    return null;
  }

  const modelName = finalResponse.model.split('/')[1] || finalResponse.model;

  return (
    <div className={`stage stage3 ${isExpanded ? 'expanded' : ''}`}>
      <h3 className="stage-title">The Council's Verdict</h3>

      <div className="final-response">
        <div
          className="chairman-label"
          onClick={() => setIsExpanded(!isExpanded)}
          style={{ cursor: 'pointer' }}
          title={isExpanded ? "Click to collapse" : "Click to expand"}
        >
          Speaker: {modelName} {isExpanded ? '▼' : '▶'}
        </div>

        <div className="final-content-wrapper">
          <div className="final-text markdown-content">
            <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
