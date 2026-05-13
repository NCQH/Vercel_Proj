import os
import uuid
import logging
import time
import httpx
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from langchain_text_splitters import RecursiveCharacterTextSplitter
from api.lib.document_ingest import SUPPORTED_DOCUMENT_EXTENSIONS, extract_documents_from_file
from api.lib.supabase import (
    _supabase_headers,
    _encode_eq,
    _safe_user_id,
    SUPABASE_URL
)
from api.lib.storage import storage_client, CLASS_FILES_BUCKET
from api.lib.internal_auth import verify_internal_request
import re
from datetime import datetime, timezone

router = APIRouter(prefix="/api/classes", dependencies=[Depends(verify_internal_request)])
logger = logging.getLogger(__name__)

# Lightweight in-memory cache for hot endpoint /api/classes/files/user
USER_CLASS_FILES_CACHE_TTL_SECONDS = 20
MAX_CLASS_FILE_BYTES = 20 * 1024 * 1024
ALLOWED_CLASS_FILE_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS
_user_class_files_cache: dict[str, dict] = {}

def _safe_filename(raw: str) -> str:
    name = Path(raw or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name[:120] or "document"

def _get_cached_user_class_files(user_id: str):
    cached = _user_class_files_cache.get(user_id)
    if not cached:
        return None
    if cached.get("expires_at", 0) <= time.time():
        _user_class_files_cache.pop(user_id, None)
        return None
    return cached.get("items")

def _set_cached_user_class_files(user_id: str, items: list[dict]):
    _user_class_files_cache[user_id] = {
        "expires_at": time.time() + USER_CLASS_FILES_CACHE_TTL_SECONDS,
        "items": items,
    }

# Helper functions for classes
def _create_class(lecturer_id: str, name: str, description: str = "") -> dict:
    code = uuid.uuid4().hex[:8].upper()
    payload = {"lecturer_id": lecturer_id, "name": name.strip(), "description": description.strip(), "code": code}
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/classes", headers=headers, json=payload)
    if response.status_code >= 300:
        logger.error("Failed to create class: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(status_code=500, detail="Failed to create class")
    rows = response.json()
    return rows[0] if rows else payload

def _list_classes_for_lecturer(lecturer_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/classes?lecturer_id=eq.{_encode_eq(lecturer_id)}&select=id,name,code,description,is_active,created_at&order=created_at.desc"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        logger.error("Failed to list lecturer classes: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(status_code=500, detail="Failed to list lecturer classes")
    return response.json()

def _list_classes_for_student(student_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_members?student_id=eq.{_encode_eq(student_id)}&select=id,status,requested_at,approved_at,class_id,classes(id,name,code,description,is_active,lecturer_id)&order=requested_at.desc"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        logger.error("Failed to list student classes: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(status_code=500, detail="Failed to list student classes")
    rows = response.json()
    out = []
    for row in rows:
        cls = (row.get("classes") or {})
        out.append({"membership_id": row.get("id"), "status": row.get("status"), "requested_at": row.get("requested_at"), "approved_at": row.get("approved_at"), "class": cls})
    return out

def _list_public_classes() -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/classes?is_active=eq.true&select=id,name,code,description,lecturer_id,created_at&order=created_at.desc"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        logger.error("Failed to list public classes: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(status_code=500, detail="Failed to list public classes")
    return response.json()

def _list_pending_requests_for_lecturer(lecturer_id: str, class_id: str = "") -> list[dict]:
    classes = _list_classes_for_lecturer(lecturer_id)
    owned_ids = {c.get("id") for c in classes}
    if class_id:
        if class_id not in owned_ids:
            raise HTTPException(status_code=403, detail="You are not owner of this class")
        owned_ids = {class_id}
    if not owned_ids: return []
    headers = _supabase_headers()
    out = []
    with httpx.Client(timeout=15.0) as client:
        for cid in owned_ids:
            url = f"{SUPABASE_URL}/rest/v1/class_members?class_id=eq.{_encode_eq(str(cid))}&status=eq.pending&select=id,class_id,student_id,status,requested_at&order=requested_at.asc"
            resp = client.get(url, headers=headers)
            if resp.status_code < 300: out.extend(resp.json())
    return out

def _list_all_members_for_class(lecturer_id: str, class_id: str) -> list[dict]:
    """List all members (pending, approved, rejected) for a specific class with student details."""
    _ensure_lecturer_class_owner(lecturer_id, class_id)
    headers = _supabase_headers()
    
    # Get class members
    url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?class_id=eq.{_encode_eq(class_id)}"
        f"&select=id,class_id,student_id,status,requested_at,approved_at"
        f"&order=requested_at.desc"
    )
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    if resp.status_code >= 300:
        logger.error("Failed to list class members: status=%s body=%s", resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail="Failed to list class members")
    
    members = resp.json()
    if not members:
        return []
    
    # Get unique student IDs and convert underscore to @ for users table lookup
    # student_id format: "huy181103_gmail.com" -> users.id format: "huy181103@gmail.com"
    student_ids_raw = list(set(m.get("student_id") for m in members if m.get("student_id")))
    student_ids_normalized = [sid.replace("_", "@") for sid in student_ids_raw]
    
    # Create mapping: normalized_id -> original_id
    id_mapping = {sid.replace("_", "@"): sid for sid in student_ids_raw}
    
    # Fetch user details for all students
    users_map = {}
    if student_ids_normalized:
        # Build OR query for multiple student IDs
        or_conditions = ",".join([f"id.eq.{_encode_eq(sid)}" for sid in student_ids_normalized])
        users_url = f"{SUPABASE_URL}/rest/v1/users?or=({or_conditions})&select=id,full_name,email"
        
        with httpx.Client(timeout=15.0) as client:
            users_resp = client.get(users_url, headers=headers)
        
        if users_resp.status_code < 300:
            users = users_resp.json()
            # Map back to original student_id format (with underscore)
            for user in users:
                user_id = user.get("id")
                original_id = id_mapping.get(user_id, user_id)
                users_map[original_id] = user
    
    # Merge member data with user data
    result = []
    for member in members:
        student_id = member.get("student_id")
        user_data = users_map.get(student_id, {})
        result.append({
            "id": member.get("id"),
            "class_id": member.get("class_id"),
            "student_id": student_id,
            "status": member.get("status"),
            "requested_at": member.get("requested_at"),
            "approved_at": member.get("approved_at"),
            "full_name": user_data.get("full_name"),
            "student_email": user_data.get("email"),
        })
    
    return result

def _approve_membership(lecturer_id: str, membership_id: str, approve: bool) -> dict:
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    lookup_url = f"{SUPABASE_URL}/rest/v1/class_members?id=eq.{_encode_eq(membership_id)}&select=id,class_id"
    with httpx.Client(timeout=15.0) as client:
        lookup_resp = client.get(lookup_url, headers=headers)
    if lookup_resp.status_code >= 300: raise HTTPException(status_code=500, detail="Membership lookup failed")
    rows = lookup_resp.json()
    if not rows: raise HTTPException(status_code=404, detail="Membership not found")
    class_id = rows[0].get("class_id")
    _ensure_lecturer_class_owner(lecturer_id, class_id)
    
    status = "approved" if approve else "rejected"
    payload = {"status": status, "approved_at": datetime.now(timezone.utc).isoformat() if approve else None}
    patch_url = f"{SUPABASE_URL}/rest/v1/class_members?id=eq.{_encode_eq(membership_id)}"
    with httpx.Client(timeout=15.0) as client:
        patch_resp = client.patch(patch_url, headers=headers, json=payload)
    if patch_resp.status_code >= 300: raise HTTPException(status_code=500, detail="Failed to update membership")
    return patch_resp.json()[0]

def _request_to_join_class(student_id: str, code: str) -> dict:
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    cls_url = f"{SUPABASE_URL}/rest/v1/classes?code=eq.{_encode_eq(code.strip().upper())}&select=id,is_active&limit=1"
    with httpx.Client(timeout=15.0) as client:
        cls_resp = client.get(cls_url, headers=headers)
    
    if cls_resp.status_code >= 300:
        logger.error(f"Class lookup failed: status={cls_resp.status_code} body={cls_resp.text}")
        raise HTTPException(status_code=500, detail="Class lookup failed")
    
    cls_rows = cls_resp.json()
    if not cls_rows:
        logger.warning(f"Class not found with code: {code}")
        raise HTTPException(status_code=404, detail="Class not found with this code")
    
    class_id = cls_rows[0].get("id")
    
    # Check if student already has a membership (pending, approved, or rejected)
    check_url = f"{SUPABASE_URL}/rest/v1/class_members?student_id=eq.{_encode_eq(student_id)}&class_id=eq.{_encode_eq(class_id)}&select=id,status&limit=1"
    with httpx.Client(timeout=15.0) as client:
        check_resp = client.get(check_url, headers=headers)
    
    if check_resp.status_code < 300 and check_resp.json():
        existing = check_resp.json()[0]
        existing_status = existing.get("status")
        logger.info(f"Student {student_id} already has membership in class {class_id} with status {existing_status}")
        if existing_status == "pending":
            raise HTTPException(status_code=400, detail="You already have a pending request for this class")
        elif existing_status == "approved":
            raise HTTPException(status_code=400, detail="You are already a member of this class")
        elif existing_status == "rejected":
            raise HTTPException(status_code=400, detail="Your previous request was rejected. Please contact the instructor.")
    
    payload = {"class_id": class_id, "student_id": student_id, "status": "pending"}
    with httpx.Client(timeout=15.0) as client:
        join_resp = client.post(f"{SUPABASE_URL}/rest/v1/class_members", headers=headers, json=payload)
    
    if join_resp.status_code >= 300:
        logger.error(f"Failed to request join: status={join_resp.status_code} body={join_resp.text}")
        raise HTTPException(status_code=500, detail="Failed to request join")
    
    result = join_resp.json()
    if not result:
        logger.error("Join request returned empty response")
        raise HTTPException(status_code=500, detail="Join request returned empty response")
    
    return result[0]

def _is_student_approved_in_class(student_id: str, class_id: str) -> bool:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_members?student_id=eq.{_encode_eq(student_id)}&class_id=eq.{_encode_eq(class_id)}&status=eq.approved&select=id&limit=1"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    return resp.status_code < 300 and len(resp.json()) > 0

def _ensure_lecturer_class_owner(lecturer_id: str, class_id: str):
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/classes?id=eq.{_encode_eq(class_id)}&lecturer_id=eq.{_encode_eq(lecturer_id)}&select=id&limit=1"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    if resp.status_code >= 300 or not resp.json():
        raise HTTPException(status_code=403, detail="You do not own this class")

def _save_class_file_metadata(uploader_id: str, class_id: str, file_id: str, original_filename: str, stored_path: str, size_bytes: int) -> dict:
    payload = {"class_id": class_id, "file_id": file_id, "uploader_id": uploader_id, "original_filename": original_filename, "stored_path": stored_path, "size_bytes": size_bytes}
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(f"{SUPABASE_URL}/rest/v1/class_files", headers=headers, json=payload)
    if resp.status_code >= 300: raise HTTPException(status_code=500, detail="Failed to save class file metadata")
    return resp.json()[0]

def _list_class_files(class_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_files?class_id=eq.{_encode_eq(class_id)}&select=file_id,original_filename,size_bytes,uploaded_at&order=uploaded_at.desc"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    if resp.status_code >= 300: raise HTTPException(status_code=500, detail="Failed to list class files")
    items = resp.json()
    for item in items:
        item.setdefault("ingest_status", "ready")
    return items

# Routes
@router.get("")
def list_classes(user_id: str = "", role: str = "student"):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    if role == "lecturer": items = _list_classes_for_lecturer(safe_user)
    elif role == "student": items = _list_classes_for_student(safe_user)
    else: items = _list_public_classes()
    return {"ok": True, "items": items}

@router.post("")
def create_class(user_id: str = Form(""), name: str = Form(""), description: str = Form("")):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    item = _create_class(safe_user, name, description)
    return {"ok": True, "item": item}

@router.get("/pending")
def list_pending_requests(user_id: str = "", class_id: str = ""):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    items = _list_pending_requests_for_lecturer(safe_user, class_id)
    return {"ok": True, "items": items}

@router.get("/members")
def list_class_members(user_id: str = "", class_id: str = ""):
    """List all members (pending, approved, rejected) for a specific class."""
    if not user_id or not class_id:
        raise HTTPException(status_code=400, detail="Missing user_id or class_id")
    safe_user = _safe_user_id(user_id)
    items = _list_all_members_for_class(safe_user, class_id)
    return {"ok": True, "items": items}

@router.post("/members/{membership_id}/approve")
def approve_request(membership_id: str, user_id: str = Form(""), approve: str = Form("true")):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    is_approve = approve.lower() == "true"
    item = _approve_membership(safe_user, membership_id, is_approve)
    
    # Invalidate cache for student so they can access class files immediately
    if is_approve and item.get("student_id"):
        try:
            from api.lib.cache_manager import CacheManager
            student_id = item.get("student_id")
            CacheManager.invalidate_allowed_sources(student_id)
            logger.info(f"Invalidated cache for student {student_id} after approval")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
    
    return {"ok": True, "item": item}

@router.post("/join")
def join_class(user_id: str = Form(""), code: str = Form(""), class_code: str = Form("")):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    # Accept both 'code' and 'class_code' for backward compatibility
    final_code = code or class_code
    if not final_code or not final_code.strip():
        raise HTTPException(status_code=400, detail="Class code is required")
    item = _request_to_join_class(safe_user, final_code)
    return {"ok": True, "item": item}

@router.get("/files/user")
def get_user_class_files(user_id: str = ""):
    """Get all class files for user's approved classes (optimized - 1 query instead of N)."""
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
    
    safe_user = _safe_user_id(user_id)

    cached_items = _get_cached_user_class_files(safe_user)
    if cached_items is not None:
        return {"ok": True, "items": cached_items, "cached": True}

    headers = _supabase_headers()
    
    # Get user's approved class memberships
    memberships_url = (
        f"{SUPABASE_URL}/rest/v1/class_members"
        f"?student_id=eq.{_encode_eq(safe_user)}"
        f"&status=eq.approved"
        f"&select=class_id,classes(id,name)"
    )
    
    with httpx.Client(timeout=15.0) as client:
        mem_resp = client.get(memberships_url, headers=headers)
    
    if mem_resp.status_code >= 300:
        return {"ok": True, "items": []}
    
    memberships = mem_resp.json()
    if not memberships:
        _set_cached_user_class_files(safe_user, [])
        return {"ok": True, "items": []}
    
    # Build class_id -> class_name mapping
    class_map = {}
    class_ids = []
    for m in memberships:
        class_id = m.get("class_id")
        class_data = m.get("classes") or {}
        class_name = class_data.get("name", "Unknown")
        if class_id:
            class_ids.append(class_id)
            class_map[class_id] = class_name
    
    if not class_ids:
        _set_cached_user_class_files(safe_user, [])
        return {"ok": True, "items": []}
    
    # Get all files for these classes in ONE query using OR
    or_conditions = ",".join([f"class_id.eq.{_encode_eq(cid)}" for cid in class_ids])
    files_url = (
        f"{SUPABASE_URL}/rest/v1/class_files"
        f"?or=({or_conditions})"
        f"&select=file_id,class_id,original_filename,size_bytes,uploaded_at"
        f"&order=uploaded_at.desc"
    )
    
    with httpx.Client(timeout=15.0) as client:
        files_resp = client.get(files_url, headers=headers)
    
    if files_resp.status_code >= 300:
        return {"ok": True, "items": []}
    
    files = files_resp.json()
    
    # Add class_name to each file
    items = []
    for f in files:
        class_id = f.get("class_id")
        items.append({
            "file_id": f.get("file_id"),
            "class_id": class_id,
            "class_name": class_map.get(class_id, "Unknown"),
            "original_filename": f.get("original_filename"),
            "size_bytes": f.get("size_bytes"),
            "uploaded_at": f.get("uploaded_at"),
            "ingest_status": "ready",
        })

    _set_cached_user_class_files(safe_user, items)
    return {"ok": True, "items": items, "cached": False}

@router.get("/files/list")
def list_files(user_id: str = "", class_id: str = ""):
    if not user_id or not class_id: raise HTTPException(status_code=400, detail="Missing parameters")
    safe_user = _safe_user_id(user_id)
    can_access = False
    try:
        _ensure_lecturer_class_owner(safe_user, class_id)
        can_access = True
    except HTTPException:
        can_access = _is_student_approved_in_class(safe_user, class_id)
    
    if not can_access: raise HTTPException(status_code=403, detail="Access denied")
    items = _list_class_files(class_id)
    return {"ok": True, "items": items}

@router.post("/files/upload")
async def upload_class_file(file: UploadFile = File(...), user_id: str = Form(""), class_id: str = Form("")):
    if not user_id or not class_id: raise HTTPException(status_code=401, detail="Missing parameters")
    if not storage_client: raise HTTPException(status_code=500, detail="Storage client not initialized")
    
    safe_user = _safe_user_id(user_id)
    _ensure_lecturer_class_owner(safe_user, class_id)
    
    safe_name = _safe_filename(file.filename or "document")
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_CLASS_FILE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    content = await file.read(MAX_CLASS_FILE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_CLASS_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    file_id = str(uuid.uuid4())
    storage_path = f"classes/{class_id}/{file_id}_{safe_name}"
    try:
        storage_client.upload_file(bucket=CLASS_FILES_BUCKET, path=storage_path, file_data=content)
    except Exception:
        logger.exception("Failed to upload class file to storage")
        raise HTTPException(status_code=500, detail="Failed to upload file")
    
    item = _save_class_file_metadata(safe_user, class_id, file_id, safe_name, storage_path, len(content))
    
    # Ingest file into ChromaDB for RAG
    try:
        docs = []
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            docs = extract_documents_from_file(
                tmp_path,
                safe_name,
                {"class_id": class_id, "stored_path": storage_path, "file_id": file_id},
            )
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass
        
        if docs:
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
            chunks = splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata = {
                    **(chunk.metadata or {}),
                    "class_id": class_id,
                    "source": safe_name,
                    "stored_path": storage_path,
                    "file_id": file_id
                }
            
            from src.rag.vectorstore import get_vectorstore, add_documents
            add_documents(get_vectorstore(user_id=f"class_{class_id}"), chunks)
            logger.info(f"Ingested {len(chunks)} chunks for class file {file_id} in class {class_id}")
    except Exception as e:
        logger.exception("RAG ingest failed for class file")
        # Don't fail the upload, just log the error
    
    # Invalidate cache for all approved class members
    try:
        from api.lib.cache_manager import CacheManager
        members = _list_all_members_for_class(safe_user, class_id)
        approved_members = [m.get("student_id") for m in members if m.get("status") == "approved"]
        if approved_members:
            count = CacheManager.invalidate_class_members(class_id, approved_members)
            logger.info(f"Invalidated cache for {count} class members after file upload")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for class members: {e}")
    
    item["ingest_status"] = "ready"
    return {"ok": True, "item": item}

@router.get("/public")
def list_public_classes(user_id: str = ""):
    """List all active public classes available for students to join."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    items = _list_public_classes()
    return {"ok": True, "items": items}

@router.get("/files/download_file")
def download_class_file_route(file_id: str = "", user_id: str = ""):
    if not user_id or not file_id: raise HTTPException(status_code=400, detail="Missing parameters")
    if not storage_client: raise HTTPException(status_code=500, detail="Storage client not initialized")
    
    safe_user = _safe_user_id(user_id)
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_files?file_id=eq.{_encode_eq(file_id)}&select=file_id,class_id,original_filename,stored_path,uploader_id&limit=1"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    rows = resp.json()
    if not rows: raise HTTPException(status_code=404, detail="File not found")
    
    item = rows[0]
    class_id = item.get("class_id")
    can_access = False
    try:
        _ensure_lecturer_class_owner(safe_user, class_id)
        can_access = True
    except HTTPException:
        can_access = _is_student_approved_in_class(safe_user, class_id)
    
    if not can_access: raise HTTPException(status_code=403, detail="Access denied")
    
    download_name = _safe_filename(item.get("original_filename") or "download.bin")
    content = storage_client.download_file(bucket=CLASS_FILES_BUCKET, path=item.get("stored_path"))
    return Response(content=content, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{download_name}"'})

@router.delete("/{class_id}")
def delete_class(class_id: str, user_id: str = ""):
    """Delete a class (lecturer only). Cascades to members and files."""
    if not user_id or not class_id:
        raise HTTPException(status_code=400, detail="Missing user_id or class_id")
    
    safe_user = _safe_user_id(user_id)
    _ensure_lecturer_class_owner(safe_user, class_id)
    
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/classes?id=eq.{_encode_eq(class_id)}"
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.delete(url, headers=headers)
    
    if resp.status_code >= 300:
        logger.error("Failed to delete class: status=%s body=%s", resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail="Failed to delete class")
    
    logger.info(f"Deleted class {class_id} by lecturer {safe_user}")
    return {"ok": True, "class_id": class_id, "message": "Class deleted successfully"}

@router.patch("/{class_id}")
def update_class(
    class_id: str,
    user_id: str = Form(""),
    name: str = Form(None),
    description: str = Form(None),
    is_active: bool = Form(None)
):
    """Update class details (lecturer only)."""
    if not user_id or not class_id:
        raise HTTPException(status_code=400, detail="Missing user_id or class_id")
    
    safe_user = _safe_user_id(user_id)
    _ensure_lecturer_class_owner(safe_user, class_id)
    
    payload = {}
    if name is not None and name.strip():
        payload["name"] = name.strip()
    if description is not None:
        payload["description"] = description.strip()
    if is_active is not None:
        payload["is_active"] = is_active
    
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    url = f"{SUPABASE_URL}/rest/v1/classes?id=eq.{_encode_eq(class_id)}"
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.patch(url, headers=headers, json=payload)
    
    if resp.status_code >= 300:
        logger.error("Failed to update class: status=%s body=%s", resp.status_code, resp.text)
        raise HTTPException(status_code=500, detail="Failed to update class")
    
    rows = resp.json()
    logger.info(f"Updated class {class_id} by lecturer {safe_user}: {payload}")
    return {"ok": True, "item": rows[0] if rows else {}}

@router.delete("/files/{file_id}")
def delete_class_file(file_id: str, user_id: str = ""):
    """Delete a class file (lecturer only). Removes from storage, database, and vectorstore."""
    if not user_id or not file_id:
        raise HTTPException(status_code=400, detail="Missing user_id or file_id")
    
    safe_user = _safe_user_id(user_id)
    
    # Lookup file metadata
    headers = _supabase_headers()
    lookup_url = (
        f"{SUPABASE_URL}/rest/v1/class_files"
        f"?file_id=eq.{_encode_eq(file_id)}"
        f"&select=file_id,class_id,stored_path,original_filename"
        f"&limit=1"
    )
    
    with httpx.Client(timeout=15.0) as client:
        lookup_resp = client.get(lookup_url, headers=headers)
    
    if lookup_resp.status_code >= 300 or not lookup_resp.json():
        raise HTTPException(status_code=404, detail="File not found")
    
    file_data = lookup_resp.json()[0]
    class_id = file_data.get("class_id")
    stored_path = file_data.get("stored_path")
    original_filename = file_data.get("original_filename")
    
    # Check ownership
    _ensure_lecturer_class_owner(safe_user, class_id)
    
    # Delete from database
    delete_url = f"{SUPABASE_URL}/rest/v1/class_files?file_id=eq.{_encode_eq(file_id)}"
    with httpx.Client(timeout=15.0) as client:
        del_resp = client.delete(delete_url, headers=headers)
    
    if del_resp.status_code >= 300:
        raise HTTPException(status_code=500, detail="Failed to delete file metadata")
    
    # Delete from storage
    file_deleted = False
    if storage_client and stored_path:
        try:
            storage_client.delete_file(bucket=CLASS_FILES_BUCKET, path=stored_path)
            file_deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")
    
    # Delete from vectorstore
    vector_deleted = False
    if original_filename:
        try:
            from src.rag.vectorstore import get_vectorstore
            vectorstore = get_vectorstore(user_id=f"class_{class_id}")
            collection = getattr(vectorstore, "_collection", None)
            if collection:
                collection.delete(where={"source": original_filename})
                vector_deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete from vectorstore: {e}")
    
    logger.info(f"Deleted class file {file_id} from class {class_id} by lecturer {safe_user}")
    return {
        "ok": True,
        "file_id": file_id,
        "file_deleted": file_deleted,
        "vector_deleted": vector_deleted,
        "message": "File deleted successfully"
    }
