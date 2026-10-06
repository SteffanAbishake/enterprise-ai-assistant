import asyncio
import math
import re
import secrets
import time

from fastapi import HTTPException

from app.models import Document, User

PERMISSIONS = {
    "viewer": {"search"},
    "analyst": {"search", "analytics", "mcp"},
    "administrator": {"search", "analytics", "mcp", "admin"},
}
SUSPICIOUS = re.compile(
    r"ignore (?:all |previous |the )*(?:instructions|rules)|"
    r"(?:reveal|print|send|exfiltrate).{0,40}(?:secret|api.key|password|system.prompt)|"
    r"(?:os\.system|subprocess|__import__|eval\(|exec\()",
    re.IGNORECASE,
)


def authenticate(key, settings):
    for role, expected, departments in [
        ("viewer", settings.viewer_key, ["payments", "platform"]),
        ("analyst", settings.analyst_key, ["payments", "platform"]),
        ("administrator", settings.admin_key, ["payments", "platform", "hr"]),
    ]:
        if secrets.compare_digest(key, expected):
            return User(id=role, role=role, departments=departments)
    raise HTTPException(401, "Invalid credentials")


def authorize(user, tool):
    if tool not in PERMISSIONS[user.role]:
        raise HTTPException(403, "Your role cannot use this tool")


def allowed(user: User, doc: Document):
    return doc.department in user.departments and (
        doc.access_level == "internal" or user.role == "administrator"
    )


def validate_input(text):
    if not text.strip() or SUSPICIOUS.search(text):
        raise HTTPException(400, "Request rejected by input validation")


class TokenBucket:
    """Single-process token bucket. A Redis atomic script is needed for multiple workers."""

    def __init__(self, capacity, refill, clock=time.monotonic):
        self.capacity, self.refill, self.clock = capacity, refill, clock
        self.buckets = {}
        self.lock = asyncio.Lock()

    async def take(self, user_id):
        async with self.lock:
            now = self.clock()
            tokens, updated = self.buckets.get(user_id, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - updated) * self.refill)
            if tokens < 1:
                self.buckets[user_id] = (tokens, now)
                wait = math.ceil((1 - tokens) / self.refill)
                raise HTTPException(429, "Rate limit reached", headers={"Retry-After": str(wait)})
            self.buckets[user_id] = (tokens - 1, now)
