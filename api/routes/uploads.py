import os
import uuid
import logging
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader

from api.lib.supabase import (
    _supabase_headers,
    _encode_eq,
    _safe_user_id,
    _save_upload_metadata,
    _list_upload_metadata,
    SUPABASE_URL
)
from src.rag.vectorstore import get_vectorstore, add_documents
from api.lib.storage import storage_client, USER_UPLOADS_BUCKET
import re
import httpx

router = APIRouter(prefix="/api/uploads")
logger = logging.getLogger(__name__)

def _safe_filename(raw: str) -> str:
    name = Path(raw or "upload.bin").name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name[:180] or "upload.bin"

def _delete_upload_metadata_and_file(user_id: str, file_id: str) -> dict:
    headers = _supabase_headers()
    lookup_url = (
        f"{SUPABASE_URL}/rest/v1/uploads"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&file_id=eq.{_encode_eq(file_id)}"
        f"&select=file_id,original_filename,stored_path"
        f"&limit=1"
    )

    with httpx.Client(timeout=15.0) as client:
        lookup_resp = client.get(lookup_url, headers=headers)
    if lookup_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to lookup upload: {lookup_resp.text}")

    rows = lookup_resp.json()
    if not rows:
        raise HTTPException(status_code=404, detail="Upload not found")

    row = rows[0]
    original_filename = str(row.get("original_filename") or "")
    storage_path = str(row.get("stored_path") or "")

    # 1) Delete metadata row
    delete_url = (
        f"{SUPABASE_URL}/rest/v1/uploads"
        f"?user_id=eq.{_encode_eq(user_id)}"
        f"&file_id=eq.{_encode_eq(file_id)}"
    )
    with httpx.Client(timeout=15.0) as client:
        delete_resp = client.delete(delete_url, headers=headers)
    if delete_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to delete upload metadata: {delete_resp.text}")

    # 2) Delete file from Supabase Storage
    file_deleted = False
    if storage_path and storage_client:
        try:
            storage_client.delete_file(bucket=USER_UPLOADS_BUCKET, path=storage_path)
            file_deleted = True
        except Exception:
            logger.warning("Failed to remove file from Supabase Storage path=%s", storage_path, exc_info=True)

    # 3) Purge chunks from vectorstore
    vector_deleted = False
    if original_filename:
        try:
            vectorstore = get_vectorstore(user_id=user_id)
            collection = getattr(vectorstore, "_collection", None)
            if collection is not None:
                collection.delete(where={"source": original_filename})
                vector_deleted = True
        except Exception:
            logger.warning("Failed to purge vector chunks user=%s source=%s", user_id, original_filename, exc_info=True)

    return {
        "file_id": file_id,
        "filename": original_filename,
        "stored_path": storage_path,
        "file_deleted": file_deleted,
        "vector_deleted": vector_deleted,
    }

@router.get("")
def list_uploads(user_id: str = ""):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    items = _list_upload_metadata(safe_user)
    return {"ok": True, "user_id": safe_user, "items": items}

@router.post("/upload") # Note: This will be /api/uploads/upload
async def upload_file_legacy(file: UploadFile = File(...), user_id: str = Form("")):
    # This matches the existing /api/upload endpoint
    return await upload_file(file, user_id)

@router.post("")
async def upload_file(file: UploadFile = File(...), user_id: str = Form("")):
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    
    if not storage_client:
        raise HTTPException(status_code=500, detail="Storage client not initialized")

    safe_user = _safe_user_id(user_id)
    safe_name = _safe_filename(file.filename or "upload.bin")
    file_id = str(uuid.uuid4())

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    storage_path = f"{safe_user}/{file_id}_{safe_name}"
    try:
        storage_client.upload_file(bucket=USER_UPLOADS_BUCKET, path=storage_path, file_data=content)
    except Exception as e:
        logger.exception("Failed to upload file to Supabase Storage")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

    _save_upload_metadata(user_id=safe_user, file_id=file_id, original_filename=safe_name, storage_path=storage_path, size_bytes=len(content))

    try:
        ext = Path(safe_name).suffix.lower()
        docs = []
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            if ext == ".pdf": docs = PyMuPDFLoader(tmp_path).load()
            elif ext == ".docx": docs = Docx2txtLoader(tmp_path).load()
            elif ext in {".txt", ".md"}: docs = TextLoader(tmp_path, encoding="utf-8").load()
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass

        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata = {**(chunk.metadata or {}), "user_id": safe_user, "source": safe_name, "stored_path": storage_path}
            add_documents(get_vectorstore(user_id=safe_user), chunks)
    except Exception as e:
        logger.exception("RAG ingest failed")
        raise HTTPException(status_code=500, detail=f"Upload saved but RAG ingest failed: {str(e)}")

    return {"ok": True, "file_id": file_id, "user_id": safe_user, "filename": safe_name, "size": len(content), "path": storage_path}

@router.get("/download")
def download_upload(file_id: str = "", user_id: str = ""):
    if not user_id or not file_id:
        raise HTTPException(status_code=400, detail="Missing user_id or file_id")
    
    if not storage_client:
        raise HTTPException(status_code=500, detail="Storage client not initialized")

    safe_user = _safe_user_id(user_id)
    items = _list_upload_metadata(safe_user)
    target = next((item for item in items if item.get("file_id") == file_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="File not found")

    storage_path = str(target.get("path") or "")
    try:
        file_content = storage_client.download_file(bucket=USER_UPLOADS_BUCKET, path=storage_path)
    except Exception as e:
        logger.exception("Failed to download file")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

    return Response(content=file_content, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{target.get("filename") or "download.bin"}"'})

@router.delete("/{file_id}")
def delete_upload(file_id: str, user_id: str = ""):
    if not user_id or not file_id:
        raise HTTPException(status_code=400, detail="Missing user_id or file_id")
    safe_user = _safe_user_id(user_id)
    result = _delete_upload_metadata_and_file(safe_user, file_id)
    return {"ok": True, "user_id": safe_user, "deleted": result}
