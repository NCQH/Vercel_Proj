#!/usr/bin/env python3
"""
Preview what will be deleted before running reset_file_data.py
This is a safe read-only script.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Note: using SERVICE_ROLE_KEY from .env

def preview_data():
    """Show what data exists before reset."""
    print("=" * 80)
    print("FILE DATA PREVIEW (Read-Only)")
    print("=" * 80)
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    print("\n📊 DATA TO BE DELETED:")
    print("-" * 80)
    
    # Uploads
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/uploads?select=file_id,user_id,original_filename,size_bytes,uploaded_at",
                headers=headers
            )
        
        if resp.status_code < 300:
            uploads = resp.json()
            print(f"\n❌ uploads table: {len(uploads)} records")
            if uploads:
                total_size = sum(u.get("size_bytes", 0) for u in uploads)
                print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
                print(f"   Sample files:")
                for u in uploads[:5]:
                    print(f"     - {u.get('original_filename')} ({u.get('size_bytes', 0) / 1024:.1f} KB)")
                if len(uploads) > 5:
                    print(f"     ... and {len(uploads) - 5} more")
    except Exception as e:
        print(f"\n❌ uploads table: Error - {e}")
    
    # Class files
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/class_files?select=file_id,class_id,original_filename,size_bytes,uploaded_at",
                headers=headers
            )
        
        if resp.status_code < 300:
            class_files = resp.json()
            print(f"\n❌ class_files table: {len(class_files)} records")
            if class_files:
                total_size = sum(cf.get("size_bytes", 0) for cf in class_files)
                print(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
                print(f"   Sample files:")
                for cf in class_files[:5]:
                    print(f"     - {cf.get('original_filename')} (class: {cf.get('class_id')}, {cf.get('size_bytes', 0) / 1024:.1f} KB)")
                if len(class_files) > 5:
                    print(f"     ... and {len(class_files) - 5} more")
    except Exception as e:
        print(f"\n❌ class_files table: Error - {e}")
    
    # ChromaDB
    print(f"\n❌ ChromaDB: All collections will be deleted")
    print(f"   (Run check_chromadb_status.py to see details)")
    
    print("\n" + "-" * 80)
    print("\n✅ DATA TO BE PRESERVED:")
    print("-" * 80)
    
    # Users
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/users?select=id,email,full_name",
                headers=headers
            )
        
        if resp.status_code < 300:
            users = resp.json()
            print(f"\n✅ users table: {len(users)} records (PRESERVED)")
            if users:
                print(f"   Sample users:")
                for u in users[:5]:
                    print(f"     - {u.get('full_name', 'N/A')} ({u.get('email', 'N/A')})")
                if len(users) > 5:
                    print(f"     ... and {len(users) - 5} more")
    except Exception as e:
        print(f"\n✅ users table: Error - {e}")
    
    # Classes
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/classes?select=id,name,code,lecturer_id",
                headers=headers
            )
        
        if resp.status_code < 300:
            classes = resp.json()
            print(f"\n✅ classes table: {len(classes)} records (PRESERVED)")
            if classes:
                print(f"   Sample classes:")
                for c in classes[:5]:
                    print(f"     - {c.get('name', 'N/A')} (code: {c.get('code', 'N/A')})")
                if len(classes) > 5:
                    print(f"     ... and {len(classes) - 5} more")
    except Exception as e:
        print(f"\n✅ classes table: Error - {e}")
    
    # Class members
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/class_members?select=id,class_id,student_id,status",
                headers=headers
            )
        
        if resp.status_code < 300:
            members = resp.json()
            print(f"\n✅ class_members table: {len(members)} records (PRESERVED)")
            if members:
                approved = sum(1 for m in members if m.get("status") == "approved")
                pending = sum(1 for m in members if m.get("status") == "pending")
                print(f"     - Approved: {approved}")
                print(f"     - Pending: {pending}")
    except Exception as e:
        print(f"\n✅ class_members table: Error - {e}")
    
    print("\n" + "=" * 80)
    print("\n⚠️  To proceed with reset, run:")
    print("   python3 scripts/reset_file_data.py")
    print()

if __name__ == "__main__":
    preview_data()
