import os
import uuid
import logging
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response
from api.lib.supabase import (
    _supabase_headers,
    _encode_eq,
    _safe_user_id,
    SUPABASE_URL
)
from api.lib.storage import storage_client, CLASS_FILES_BUCKET
import re
from datetime import datetime, timezone

router = APIRouter(prefix="/api/classes")
logger = logging.getLogger(__name__)

# Helper functions for classes
def _create_class(lecturer_id: str, name: str, description: str = "") -> dict:
    code = uuid.uuid4().hex[:8].upper()
    payload = {"lecturer_id": lecturer_id, "name": name.strip(), "description": description.strip(), "code": code}
    headers = _supabase_headers()
    headers["Prefer"] = "return=representation"
    with httpx.Client(timeout=15.0) as client:
        response = client.post(f"{SUPABASE_URL}/rest/v1/classes", headers=headers, json=payload)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to create class: {response.text}")
    rows = response.json()
    return rows[0] if rows else payload

def _list_classes_for_lecturer(lecturer_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/classes?lecturer_id=eq.{_encode_eq(lecturer_id)}&select=id,name,code,description,is_active,created_at&order=created_at.desc"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list lecturer classes: {response.text}")
    return response.json()

def _list_classes_for_student(student_id: str) -> list[dict]:
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_members?student_id=eq.{_encode_eq(student_id)}&select=id,status,requested_at,approved_at,class_id,classes(id,name,code,description,is_active,lecturer_id)&order=requested_at.desc"
    with httpx.Client(timeout=15.0) as client:
        response = client.get(url, headers=headers)
    if response.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list student classes: {response.text}")
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
        raise HTTPException(status_code=500, detail=f"Failed to list public classes: {response.text}")
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
    """List all members (pending, approved, rejected) for a specific class."""
    _ensure_lecturer_class_owner(lecturer_id, class_id)
    headers = _supabase_headers()
    url = f"{SUPABASE_URL}/rest/v1/class_members?class_id=eq.{_encode_eq(class_id)}&select=id,class_id,student_id,status,requested_at,approved_at&order=requested_at.desc"
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
    if resp.status_code >= 300:
        raise HTTPException(status_code=500, detail=f"Failed to list class members: {resp.text}")
    return resp.json()

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
        raise HTTPException(status_code=500, detail=f"Failed to request join: {join_resp.text}")
    
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
    return resp.json()

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
    return {"ok": True, "item": item}

@router.post("/join")
def join_class(user_id: str = Form(""), code: str = Form("")):
    if not user_id: raise HTTPException(status_code=401, detail="Missing user_id")
    safe_user = _safe_user_id(user_id)
    item = _request_to_join_class(safe_user, code)
    return {"ok": True, "item": item}

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
    
    content = await file.read()
    file_id = str(uuid.uuid4())
    storage_path = f"classes/{class_id}/{file_id}_{file.filename}"
    storage_client.upload_file(bucket=CLASS_FILES_BUCKET, path=storage_path, file_data=content)
    
    item = _save_class_file_metadata(safe_user, class_id, file_id, file.filename, storage_path, len(content))
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
    
    content = storage_client.download_file(bucket=CLASS_FILES_BUCKET, path=item.get("stored_path"))
    return Response(content=content, media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{item.get("original_filename") or "download.bin"}"'})
