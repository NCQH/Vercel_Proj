import sys
import os
import re
import uuid
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from src.base_agent import run_agent
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str = "web_session"


@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        response = run_agent(
            request.message,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        return {"reply": response}
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail=f"Agent encountered an error: {str(e)}")


def _safe_user_id(raw: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", (raw or "").strip())
    return safe[:80] or "unknown_user"


def _safe_filename(raw: str) -> str:
    name = Path(raw or "upload.bin").name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:180] or "upload.bin"


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")

    safe_user = _safe_user_id(user_id)
    safe_name = _safe_filename(file.filename or "upload.bin")
    file_id = str(uuid.uuid4())

    user_dir = Path("data/uploads") / safe_user
    user_dir.mkdir(parents=True, exist_ok=True)

    target_path = user_dir / f"{file_id}_{safe_name}"
    content = await file.read()

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    target_path.write_bytes(content)

    return {
        "ok": True,
        "file_id": file_id,
        "user_id": safe_user,
        "filename": safe_name,
        "size": len(content),
        "path": str(target_path),
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "LangGraph agent is running!"}
