import json
from typing import AsyncIterator
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain.callbacks.tracers.log_stream import RunLogPatch

from chatbot import Bot
from chatbot import MemoryTypes, ModelTypes
from chatbot.common.objects import ChatRequest

bot = Bot(memory=MemoryTypes.CUSTOM_MEMORY, model=ModelTypes.VERTEX)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


async def transform_stream_for_client(
        stream: AsyncIterator[RunLogPatch],
) -> AsyncIterator[str]:
    async for chunk in stream:
        yield f"event: data\ndata: {json.dumps(jsonable_encoder(chunk))}\n\n"
    yield "event: end\n\n"


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    sentence = request.message
    chat_history = request.history
    if chat_history:
        bot.chain.add_message_to_memory(
            human_message=chat_history[-1]["human"],
            ai_message=chat_history[-1]["ai"],
            conversation_id=request.conversation_id
        )

    chain_stream = bot.chain.chain_stream(
        input=sentence,
        conversation_id=request.conversation_id
    )
    return StreamingResponse(
        transform_stream_for_client(chain_stream),
        headers={"Content-Type": "text/event-stream"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)