import asyncio
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import HTTPException


class SessionMemory:
    """Bounded, owner-scoped session memory. Restarts intentionally clear the POC memory."""
    def __init__(self):
        self.turns = {}
        self.locks = defaultdict(asyncio.Lock)

    @asynccontextmanager
    async def session(self, user_id, session_id):
        key = (user_id, str(session_id))
        if key not in self.turns and len(self.turns) >= 1000:
            raise HTTPException(503, "Session capacity reached; restart the demo server")
        async with self.locks[key]:
            history = self.turns.setdefault(key, deque(maxlen=12))
            yield history
