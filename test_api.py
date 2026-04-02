"""Test OpenRouter API and get available models."""
import httpx
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

async def test_model(model_name: str):
    """Test if a model works."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "Say 'Hello'"}],
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                print(f"✓ {model_name} - WORKS")
                return True
            else:
                print(f"✗ {model_name} - Error {response.status_code}: {response.text[:200]}")
                return False
    except Exception as e:
        print(f"✗ {model_name} - Exception: {str(e)[:200]}")
        return False

async def get_available_models():
    """Fetch list of available models from OpenRouter."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            )
            if response.status_code == 200:
                models = response.json()
                print("\n=== Available Models (sample) ===")
                for model in models['data'][:20]:  # Show first 20
                    print(f"  {model['id']}")
                return models['data']
            else:
                print(f"Error fetching models: {response.status_code}")
                return []
    except Exception as e:
        print(f"Error: {e}")
        return []

async def main():
    print("Testing current configured models...")
    print("=" * 60)
    
    current_models = [
        "openai/gpt-5.1",
        "google/gemini-3-pro-preview", 
        "anthropic/claude-sonnet-4.5",
        "x-ai/grok-4",
    ]
    
    for model in current_models:
        await test_model(model)
    
    print("\n" + "=" * 60)
    print("Testing with real model names...")
    print("=" * 60)
    
    real_models = [
        "openai/gpt-4o",
        "google/gemini-2.0-flash-exp:free",
        "anthropic/claude-3.5-sonnet",
        "x-ai/grok-beta",
    ]
    
    for model in real_models:
        await test_model(model)
    
    await get_available_models()

if __name__ == "__main__":
    asyncio.run(main())
