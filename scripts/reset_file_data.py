#!/usr/bin/env python3
"""
Reset file data only - keeps users and classes intact.

This script will:
1. Delete all records from 'uploads' table (personal files)
2. Delete all records from 'class_files' table (class files)
3. Delete all files from Supabase Storage buckets
4. Delete all ChromaDB collections (vectors)

PRESERVES:
- users table
- classes table
- class_members table
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Using SERVICE_ROLE_KEY from .env

# Import after env is loaded
try:
    from src.rag.vectorstore import get_chroma_client
    CHROMA_AVAILABLE = True
except:
    CHROMA_AVAILABLE = False

try:
    from api.lib.storage import storage_client, USER_UPLOADS_BUCKET, CLASS_FILES_BUCKET
    STORAGE_AVAILABLE = storage_client is not None
except:
    STORAGE_AVAILABLE = False
    USER_UPLOADS_BUCKET = "user-uploads"
    CLASS_FILES_BUCKET = "class-files"

def confirm_reset():
    """Ask for user confirmation."""
    print("=" * 80)
    print("⚠️  FILE DATA RESET")
    print("=" * 80)
    print("\nThis will DELETE:")
    print("  ❌ All records in 'uploads' table")
    print("  ❌ All records in 'class_files' table")
    print("  ❌ All files in Supabase Storage")
    print("  ❌ All ChromaDB collections (vectors)")
    print("\nThis will PRESERVE:")
    print("  ✅ users table")
    print("  ✅ classes table")
    print("  ✅ class_members table")
    print("\n⚠️  THIS CANNOT BE UNDONE!")
    print("=" * 80)
    
    response = input("\nType 'DELETE FILES' to confirm: ")
    return response.strip() == "DELETE FILES"

def delete_uploads_table():
    """Delete all records from uploads table."""
    print("\n[1/5] Deleting uploads table records...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get count first
        with httpx.Client(timeout=30.0) as client:
            count_resp = client.get(
                f"{SUPABASE_URL}/rest/v1/uploads?select=count",
                headers={**headers, "Prefer": "count=exact"}
            )
        
        if count_resp.status_code < 300:
            count = count_resp.headers.get("Content-Range", "0").split("/")[-1]
            print(f"  Found {count} records")
        
        # Delete all - using file_id column instead of id
        with httpx.Client(timeout=30.0) as client:
            delete_resp = client.delete(
                f"{SUPABASE_URL}/rest/v1/uploads?file_id=neq.00000000-0000-0000-0000-000000000000",
                headers=headers
            )
        
        if delete_resp.status_code < 300:
            print(f"  ✓ Deleted all uploads records")
            return True
        else:
            print(f"  ❌ Failed: {delete_resp.text}")
            return False
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def delete_class_files_table():
    """Delete all records from class_files table."""
    print("\n[2/5] Deleting class_files table records...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get count first
        with httpx.Client(timeout=30.0) as client:
            count_resp = client.get(
                f"{SUPABASE_URL}/rest/v1/class_files?select=count",
                headers={**headers, "Prefer": "count=exact"}
            )
        
        if count_resp.status_code < 300:
            count = count_resp.headers.get("Content-Range", "0").split("/")[-1]
            print(f"  Found {count} records")
        
        # Delete all
        with httpx.Client(timeout=30.0) as client:
            delete_resp = client.delete(
                f"{SUPABASE_URL}/rest/v1/class_files?file_id=neq.00000000-0000-0000-0000-000000000000",
                headers=headers
            )
        
        if delete_resp.status_code < 300:
            print(f"  ✓ Deleted all class_files records")
            return True
        else:
            print(f"  ❌ Failed: {delete_resp.text}")
            return False
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def delete_storage_files():
    """Delete all files from Supabase Storage buckets."""
    print("\n[3/5] Deleting files from Supabase Storage...")
    
    if not STORAGE_AVAILABLE:
        print("  ⚠️  Storage client not initialized, skipping")
        return True
    
    try:
        # Delete user uploads bucket
        print(f"  Deleting bucket: {USER_UPLOADS_BUCKET}")
        try:
            # List and delete all files
            files = storage_client.list_files(bucket=USER_UPLOADS_BUCKET, path="")
            if files:
                for file in files:
                    try:
                        storage_client.delete_file(bucket=USER_UPLOADS_BUCKET, path=file.get("name", ""))
                    except:
                        pass
                print(f"    ✓ Deleted {len(files)} files")
            else:
                print(f"    ✓ No files to delete")
        except Exception as e:
            print(f"    ⚠️  {e}")
        
        # Delete class files bucket
        print(f"  Deleting bucket: {CLASS_FILES_BUCKET}")
        try:
            files = storage_client.list_files(bucket=CLASS_FILES_BUCKET, path="")
            if files:
                for file in files:
                    try:
                        storage_client.delete_file(bucket=CLASS_FILES_BUCKET, path=file.get("name", ""))
                    except:
                        pass
                print(f"    ✓ Deleted {len(files)} files")
            else:
                print(f"    ✓ No files to delete")
        except Exception as e:
            print(f"    ⚠️  {e}")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def delete_chromadb_collections():
    """Delete all ChromaDB collections."""
    print("\n[4/5] Deleting ChromaDB collections...")
    
    if not CHROMA_AVAILABLE:
        print("  ⚠️  ChromaDB not available, skipping")
        return True
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            print("  ✓ No collections to delete")
            return True
        
        print(f"  Found {len(collections)} collection(s)")
        
        for col in collections:
            try:
                client.delete_collection(name=col.name)
                print(f"    ✓ Deleted: {col.name}")
            except Exception as e:
                print(f"    ❌ Failed to delete {col.name}: {e}")
        
        print(f"  ✓ Deleted all collections")
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def verify_reset():
    """Verify that reset was successful."""
    print("\n[5/5] Verifying reset...")
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    all_good = True
    
    # Check uploads
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{SUPABASE_URL}/rest/v1/uploads?select=count", headers={**headers, "Prefer": "count=exact"})
        count = resp.headers.get("Content-Range", "0/0").split("/")[-1]
        if count == "0":
            print(f"  ✓ uploads table: {count} records")
        else:
            print(f"  ⚠️  uploads table: {count} records (expected 0)")
            all_good = False
    except Exception as e:
        print(f"  ❌ uploads check failed: {e}")
        all_good = False
    
    # Check class_files
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{SUPABASE_URL}/rest/v1/class_files?select=count", headers={**headers, "Prefer": "count=exact"})
        count = resp.headers.get("Content-Range", "0/0").split("/")[-1]
        if count == "0":
            print(f"  ✓ class_files table: {count} records")
        else:
            print(f"  ⚠️  class_files table: {count} records (expected 0)")
            all_good = False
    except Exception as e:
        print(f"  ❌ class_files check failed: {e}")
        all_good = False
    
    # Check ChromaDB
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        if len(collections) == 0:
            print(f"  ✓ ChromaDB: {len(collections)} collections")
        else:
            print(f"  ⚠️  ChromaDB: {len(collections)} collections (expected 0)")
            all_good = False
    except Exception as e:
        print(f"  ❌ ChromaDB check failed: {e}")
        all_good = False
    
    # Check preserved tables
    print("\n  Checking preserved tables:")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{SUPABASE_URL}/rest/v1/users?select=count", headers={**headers, "Prefer": "count=exact"})
        count = resp.headers.get("Content-Range", "0/0").split("/")[-1]
        print(f"    ✓ users table: {count} records (preserved)")
    except:
        pass
    
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{SUPABASE_URL}/rest/v1/classes?select=count", headers={**headers, "Prefer": "count=exact"})
        count = resp.headers.get("Content-Range", "0/0").split("/")[-1]
        print(f"    ✓ classes table: {count} records (preserved)")
    except:
        pass
    
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{SUPABASE_URL}/rest/v1/class_members?select=count", headers={**headers, "Prefer": "count=exact"})
        count = resp.headers.get("Content-Range", "0/0").split("/")[-1]
        print(f"    ✓ class_members table: {count} records (preserved)")
    except:
        pass
    
    return all_good

def main():
    print("\n🗑️  File Data Reset Script\n")
    
    # Confirm
    if not confirm_reset():
        print("\n❌ Reset cancelled by user")
        return
    
    print("\n🚀 Starting reset...\n")
    
    # Execute reset steps
    results = []
    results.append(("Delete uploads table", delete_uploads_table()))
    results.append(("Delete class_files table", delete_class_files_table()))
    results.append(("Delete storage files", delete_storage_files()))
    results.append(("Delete ChromaDB collections", delete_chromadb_collections()))
    results.append(("Verify reset", verify_reset()))
    
    # Summary
    print("\n" + "=" * 80)
    print("RESET SUMMARY")
    print("=" * 80)
    
    for step_name, success in results:
        status = "✓ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {step_name}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        print("\n🎉 File data reset completed successfully!")
        print("\nNext steps:")
        print("1. Users and classes are preserved")
        print("2. You can now upload new files")
        print("3. Files will be properly indexed in ChromaDB")
    else:
        print("\n⚠️  Some steps failed. Please check the errors above.")
    
    print()

if __name__ == "__main__":
    main()
