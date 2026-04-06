"""JSON-based storage for conversations and app settings."""

# ─── Imports ─────────────────────────────────────────────────────────────────

import json
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from .config import DATA_DIR


# ─── Constants ────────────────────────────────────────────────────────────────

SETTINGS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'settings.json'
FIRST_MESSAGE_PREVIEW_LENGTH = 60
_SETTINGS_TTL = 30.0

_settings_cache: Optional[Dict[str, Any]] = None
_settings_cache_time: float = 0.0


# ─── Helpers ─────────────────────────────────────────────────────────────────

def ensure_data_dir():
    """Ensure the conversations data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Return the file path for a given conversation ID."""
    return os.path.join(DATA_DIR, f'{conversation_id}.json')


# ─── Conversation CRUD ────────────────────────────────────────────────────────

def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create and persist a new empty conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        'id': conversation_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'title': 'New Conversation',
        'messages': []
    }

    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict, or None if not found
    """
    path = get_conversation_path(conversation_id)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_conversation(conversation: Dict[str, Any]):
    """
    Persist a conversation dict to its JSON file.

    Args:
        conversation: Conversation dict to save (must contain 'id')
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations as lightweight metadata (no message bodies).

    Returns:
        List of conversation metadata dicts, sorted newest first
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if not filename.endswith('.json'):
            continue

        path = os.path.join(DATA_DIR, filename)
        with open(path, 'r') as f:
            data = json.load(f)

        first_message = ''
        for msg in data.get('messages', []):
            if msg.get('role') == 'user':
                raw = msg.get('content', '')
                first_message = raw if len(raw) <= FIRST_MESSAGE_PREVIEW_LENGTH else raw[:57] + '...'
                break

        conversations.append({
            'id': data['id'],
            'created_at': data['created_at'],
            'title': data.get('title', 'New Conversation'),
            'message_count': len(data['messages']),
            'first_message': first_message
        })

    conversations.sort(key=lambda x: x['created_at'], reverse=True)
    return conversations


def add_user_message(conversation_id: str, content: str):
    """
    Append a user message to an existing conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message text
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f'Conversation {conversation_id} not found')

    conversation['messages'].append({
        'role': 'user',
        'content': content,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Append a multi-stage assistant message to an existing conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
        metadata: label_to_model mapping and aggregate_rankings
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f'Conversation {conversation_id} not found')

    conversation['messages'].append({
        'role': 'assistant',
        'stage1': stage1,
        'stage2': stage2,
        'stage3': stage3,
        'metadata': metadata,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the display title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title string
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f'Conversation {conversation_id} not found')

    conversation['title'] = title
    save_conversation(conversation)


def delete_conversation(conversation_id: str):
    """
    Delete a conversation's JSON file from storage.

    Args:
        conversation_id: Conversation identifier
    """
    path = get_conversation_path(conversation_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# ─── Settings ─────────────────────────────────────────────────────────────────

def get_settings() -> Dict[str, Any]:
    """
    Load app settings from disk, falling back to config defaults.

    Returns:
        Settings dict with 'council_models', 'fallback_model', and 'chairman_model'
    """
    global _settings_cache, _settings_cache_time
    if _settings_cache is not None and (time.time() - _settings_cache_time) < _SETTINGS_TTL:
        return _settings_cache

    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r') as f:
            result = json.load(f)
    else:
        from .config import COUNCIL_MODELS, FALLBACK_MODEL
        result = {
            'council_models': COUNCIL_MODELS,
            'fallback_model': FALLBACK_MODEL,
        }

    _settings_cache = result
    _settings_cache_time = time.time()
    return result


def save_settings(settings: Dict[str, Any]):
    """
    Persist app settings to disk.

    Args:
        settings: Settings dict to save
    """
    global _settings_cache, _settings_cache_time
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)
    _settings_cache = settings
    _settings_cache_time = time.time()
