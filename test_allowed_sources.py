import sys
import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.index import _get_allowed_sources_and_collections, _safe_user_id

# Let's find the user's ID by looking at the uploads table directly or just testing a known ID.
# Since we don't know the exact user ID, let's query supabase directly to list recent uploads
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

resp = httpx.get(f"{SUPABASE_URL}/rest/v1/uploads?select=user_id,original_filename,uploaded_at&order=uploaded_at.desc&limit=5", headers=headers)
print("Recent uploads:", json.dumps(resp.json(), indent=2))

resp_classes = httpx.get(f"{SUPABASE_URL}/rest/v1/class_files?select=class_id,original_filename,uploaded_at&order=uploaded_at.desc&limit=5", headers=headers)
print("Recent class files:", json.dumps(resp_classes.json(), indent=2))
