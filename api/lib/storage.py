import os
from src.storage import SupabaseStorageClient

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

storage_client = SupabaseStorageClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None

USER_UPLOADS_BUCKET = "user-uploads"
CLASS_FILES_BUCKET = "class-files"
