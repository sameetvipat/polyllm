import { useState, useEffect } from 'react';

function legacyCopy(text, onSuccess) {
  const el = document.createElement('textarea');
  el.value = text;
  el.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
  document.body.appendChild(el);
  el.focus();
  el.select();
  try {
    document.execCommand('copy');
    onSuccess();
  } catch {}
  document.body.removeChild(el);
}

/**
 * Clipboard copy button. Shows a checkmark for 2s after copying.
 *
 * @param {Object} props
 * @param {string} props.text - Text to copy
 * @param {string} [props.className='copy-btn'] - CSS class for the button
 * @param {number} [props.size=14] - SVG icon size in pixels
 * @param {boolean} [props.stopPropagation=false] - Stop click event propagation
 */
export default function CopyButton({ text, className = 'copy-btn', size = 14, stopPropagation = false }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const id = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(id);
  }, [copied]);

  const handleCopy = (e) => {
    if (stopPropagation) e.stopPropagation();

    const finish = () => setCopied(true);

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(finish).catch(() => legacyCopy(text, finish));
    } else {
      legacyCopy(text, finish);
    }
  };

  return (
    <button className={className} onClick={handleCopy} title={copied ? 'Copied!' : 'Copy'}>
      {copied ? (
        <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size}>
          <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" width={size} height={size}>
          <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
        </svg>
      )}
    </button>
  );
}
