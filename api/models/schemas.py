from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str = "web_session"
    preferred_sources: List[str] = []

class RoadmapRefreshRequest(BaseModel):
    user_id: str

class RoadmapItemUpdateRequest(BaseModel):
    user_id: str
    status: str = "todo"
    progress: Optional[int] = None
