import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from pydantic import BaseModel
from src.base_agent import create_agent, run_agent_loop
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize the OpenAI client for the agent
try:
    client = create_agent()
except Exception as e:
    logger.error(f"Failed to create agent client: {e}")
    client = None

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default_web_user"
    session_id: str = "web_session"

@app.post("/api/chat")
def chat(request: ChatRequest):
    if not client:
        return {"reply": "Server Error: OpenAI API key is not configured."}
        
    try:
        response = run_agent_loop(
            client, 
            request.message, 
            user_id=request.user_id,
            session_id=request.session_id,
            max_turns=5 # Giới hạn số turn để tránh Vercel timeout (10-15s max for hobby)
        )
        return {"reply": response}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": f"Agent encountered an error: {str(e)}"}

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Python backend is running!"}
