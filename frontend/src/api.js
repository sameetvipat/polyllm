/**
 * API client for the LLM Council backend.
 */

/* ─── Config ─────────────────────────────────────────────────────────────── */

const API_BASE = 'http://localhost:8001';

/* ─── Client ─────────────────────────────────────────────────────────────── */

export const api = {
  /**
   * List all conversations (metadata only).
   *
   * @returns {Promise<Array>} Array of conversation metadata objects
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) throw new Error('Failed to list conversations');
    return response.json();
  },

  /**
   * Create a new empty conversation.
   *
   * @returns {Promise<Object>} Newly created conversation object
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error('Failed to create conversation');
    return response.json();
  },

  /**
   * Get a specific conversation with all its messages.
   *
   * @param {string} conversationId - The conversation UUID
   * @returns {Promise<Object>} Full conversation object
   */
  async getConversation(conversationId) {
    const response = await fetch(`${API_BASE}/api/conversations/${conversationId}`);
    if (!response.ok) throw new Error('Failed to get conversation');
    return response.json();
  },

  /**
   * Delete a conversation permanently.
   *
   * @param {string} conversationId - The conversation UUID
   * @returns {Promise<Object>} Deletion confirmation object
   */
  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      { method: 'DELETE' }
    );
    if (!response.ok) throw new Error('Failed to delete conversation');
    return response.json();
  },

  /**
   * Rename a conversation.
   *
   * @param {string} conversationId - The conversation UUID
   * @param {string} title - New title string
   * @returns {Promise<Object>} Update confirmation object
   */
  async renameConversation(conversationId, title) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/title`,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      }
    );
    if (!response.ok) throw new Error('Failed to rename conversation');
    return response.json();
  },

  /**
   * Get the current council configuration (models, chairman).
   *
   * @returns {Promise<Object>} Config object with council_models and chairman_model
   */
  async getConfig() {
    const response = await fetch(`${API_BASE}/api/config`);
    if (!response.ok) throw new Error('Failed to get config');
    return response.json();
  },

  /**
   * Save updated council configuration.
   *
   * @param {Object} config - Config object with council_models and chairman_model
   * @returns {Promise<Object>} Update confirmation object
   */
  async saveConfig(config) {
    const response = await fetch(`${API_BASE}/api/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error('Failed to save config');
    return response.json();
  },

  /**
   * Send a message and receive streaming Server-Sent Events as each stage completes.
   *
   * @param {string} conversationId - The conversation UUID
   * @param {string} content - The message text
   * @param {Function} onEvent - Callback invoked for each SSE event: (eventType, eventData) => void
   * @param {AbortSignal} [signal] - Optional AbortSignal to cancel the stream
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent, signal) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
        signal,
      }
    );

    if (!response.ok) throw new Error('Failed to send message');

    if (!response.body) throw new Error('Streaming response body missing');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const processEventBlock = (block) => {
      const dataLines = block
        .split('\n')
        .filter(line => line.startsWith('data: '))
        .map(line => line.slice(6));

      if (dataLines.length === 0) return;

      try {
        const event = JSON.parse(dataLines.join('\n'));
        onEvent(event.type, event);
      } catch {
        // Ignore malformed event blocks silently
      }
    };

    const abortHandler = () => {
      reader.cancel().catch(() => {});
    };

    if (signal) {
      signal.addEventListener('abort', abortHandler);
    }

    try {
      while (true) {
        if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');

        const { done, value } = await reader.read();

        if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by a blank line.
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          processEventBlock(block);
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) {
        processEventBlock(buffer);
      }
    } catch (e) {
      if (e.name === 'AbortError' || signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError');
      }
      throw e;
    } finally {
      if (signal) signal.removeEventListener('abort', abortHandler);
      try { reader.releaseLock(); } catch { /* already released */ }
    }
  },
};
