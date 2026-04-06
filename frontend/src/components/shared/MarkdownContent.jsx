import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

const REMARK_PLUGINS = [remarkGfm];
const REHYPE_PLUGINS = [rehypeHighlight];

/**
 * ReactMarkdown pre-configured with GFM tables/strikethrough and syntax highlighting.
 */
export default function MarkdownContent({ children, className }) {
  return (
    <div className={className ?? 'markdown-content'}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
