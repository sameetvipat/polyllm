"""FastAPI backend for LLM Council."""

# ─── Imports ─────────────────────────────────────────────────────────────────

import uuid
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import storage
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
)
from .services import groq, openrouter


# ─── App Setup ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for client_attr in ('_client',):
        client = getattr(groq, client_attr, None)
        if client is not None:
            await client.aclose()
        client = getattr(openrouter, client_attr, None)
        if client is not None:
            await client.aclose()
    chairman_client = getattr(council, '_chairman_client', None)
    if chairman_client is not None:
        await chairman_client.aclose()


app = FastAPI(title='LLM Council API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'Accept', 'X-Requested-With'],
)


# ─── Request / Response Models ────────────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class RenameConversationRequest(BaseModel):
    """Request to rename a conversation."""
    title: str


class ConfigRequest(BaseModel):
    """Request to update app configuration."""
    council_models: List[str]


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int
    first_message: Optional[str] = None


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


# ─── Helpers ─────────────────────────────────────────────────────────────────

MAX_HISTORY_TURNS = 6  # Number of prior user/assistant turns to include

def build_history(conversation: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert stored conversation messages into the OpenAI message format
    for passing as context to council models.
    Uses the chairman synthesis as the 'assistant' turn.
    Limits to the last MAX_HISTORY_TURNS turns to avoid token bloat.
    """
    history = []
    for msg in conversation.get('messages', []):
        if msg.get('role') == 'user':
            history.append({'role': 'user', 'content': msg['content']})
        elif msg.get('role') == 'assistant':
            stage3 = msg.get('stage3') or {}
            content = stage3.get('synthesis') or stage3.get('response', '')
            if content:
                history.append({'role': 'assistant', 'content': content})

    # Keep only the last N turns (each turn = 1 user + 1 assistant message)
    max_messages = MAX_HISTORY_TURNS * 2
    return history[-max_messages:] if len(history) > max_messages else history


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get('/')
async def root():
    """Health check endpoint."""
    return {'status': 'ok', 'service': 'LLM Council API'}


@app.get('/api/conversations', response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post('/api/conversations', response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new empty conversation."""
    conversation_id = str(uuid.uuid4())
    return storage.create_conversation(conversation_id)


@app.get('/api/conversations/{conversation_id}', response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')
    return conversation


@app.patch('/api/conversations/{conversation_id}/title')
async def rename_conversation(conversation_id: str, request: RenameConversationRequest):
    """Rename a conversation."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')

    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail='Title cannot be empty')

    storage.update_conversation_title(conversation_id, title)
    return {'status': 'updated', 'id': conversation_id, 'title': title}


@app.get('/api/config')
async def get_config():
    """Get current council configuration."""
    return storage.get_settings()


@app.put('/api/config')
async def update_config(request: ConfigRequest):
    """Update council configuration."""
    if not request.council_models:
        raise HTTPException(status_code=400, detail='At least one council model required')

    storage.save_settings({
        'council_models': request.council_models,
    })
    return {'status': 'updated'}


@app.delete('/api/conversations/{conversation_id}')
async def delete_conversation(conversation_id: str):
    """Delete a specific conversation."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')

    storage.delete_conversation(conversation_id)
    return {'status': 'deleted', 'id': conversation_id}


@app.post('/api/conversations/{conversation_id}/message')
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the full 3-stage council process.
    Returns the complete response with all stages.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')

    is_first_message = len(conversation['messages']) == 0

    storage.add_user_message(conversation_id, request.content)

    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    history = build_history(conversation)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content, history
    )

    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata
    )

    return {
        'stage1': stage1_results,
        'stage2': stage2_results,
        'stage3': stage3_result,
        'metadata': metadata
    }


@app.post('/api/conversations/{conversation_id}/message/stream')
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process via Server-Sent Events.
    Each stage emits start/complete events as it finishes.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail='Conversation not found')

    is_first_message = len(conversation['messages']) == 0

    history = build_history(conversation)

    async def event_generator():
        try:
            storage.add_user_message(conversation_id, request.content)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content, history)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(
                request.content, stage1_results
            )
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                request.content, stage1_results, stage2_results, aggregate_rankings
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}
            )

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
