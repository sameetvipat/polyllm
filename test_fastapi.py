import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
import json

app = FastAPI()

@app.post("/stream")
async def stream(request: Request):
    async def generator():
        try:
            for i in range(5):
                print(f"Server generating {i}...")
                await asyncio.sleep(2)
                print(f"Server yielding {i}...")
                yield f"data: {json.dumps({'i': i})}\n\n"
        except asyncio.CancelledError:
            print("Cancelled by client disconnect!")
            raise
        except Exception as e:
            print(f"Generator Exception: {e}")
            raise
    return StreamingResponse(generator(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, port=8888)
