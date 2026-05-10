import json
from typing import AsyncGenerator

async def stream_reasoning_steps(steps: list) -> AsyncGenerator[str, None]:
    """
    Yields reasoning steps as SSE events.
    """
    for step in steps:
        data = json.dumps({"step": step})
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"
