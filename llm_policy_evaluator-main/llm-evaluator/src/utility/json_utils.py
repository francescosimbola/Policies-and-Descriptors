def sanitize(reply: str) -> str:
    return reply.replace("```json", "").replace("```", "").strip()