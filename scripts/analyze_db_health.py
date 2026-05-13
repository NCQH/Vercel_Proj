#!/usr/bin/env python3
"""
Analyze ChromaDB collections - check dates, status, and health.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import httpx
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Try to import ChromaDB
try:
    from src.rag.vectorstore import get_chroma_client
    CHROMA_AVAILABLE = True
except:
    CHROMA_AVAILABLE = False

def analyze_chromadb_collections():
    """Analyze all ChromaDB collections."""
    print("=" * 80)
    print("CHROMADB COLLECTIONS ANALYSIS")
    print("=" * 80)
    
    if not CHROMA_AVAILABLE:
        print("\n❌ ChromaDB not available (module import failed)")
        print("   This is expected if langchain_chroma is not installed")
        return []
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            print("\n✓ No collections found (clean state)")
            return []
        
        print(f"\nFound {len(collections)} collection(s):\n")
        
        collection_info = []
        for col in collections:
            try:
                count = col.count()
                
                # Get sample documents to check metadata
                sample = None
                if count > 0:
                    try:
                        sample = col.get(limit=1, include=["metadatas"])
                    except:
                        pass
                
                info = {
                    "name": col.name,
                    "count": count,
                    "sample_metadata": sample.get("metadatas", [None])[0] if sample else None,
                    "status": "active" if count > 0 else "empty"
                }
                collection_info.append(info)
                
                # Print collection info
                print(f"📦 Collection: {col.name}")
                print(f"   Documents: {count}")
                
                if count > 0:
                    print(f"   Status: ✅ Active")
                    if info["sample_metadata"]:
                        print(f"   Sample metadata:")
                        for key, value in info["sample_metadata"].items():
                            print(f"     - {key}: {value}")
                else:
                    print(f"   Status: ⚠️  Empty (no documents)")
                
                print()
                
            except Exception as e:
                print(f"❌ Collection: {col.name}")
                print(f"   Error: {e}")
                print()
                collection_info.append({
                    "name": col.name,
                    "count": 0,
                    "status": "error",
                    "error": str(e)
                })
        
        return collection_info
    
    except Exception as e:
        print(f"\n❌ Failed to access ChromaDB: {e}")
        return []

def analyze_database_tables():
    """Analyze Supabase database tables."""
    print("=" * 80)
    print("DATABASE TABLES ANALYSIS")
    print("=" * 80)
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    tables = {
        "uploads": "Personal file uploads",
        "class_files": "Class file uploads",
        "users": "User accounts",
        "classes": "Classes",
        "class_members": "Class memberships"
    }
    
    table_info = {}
    
    for table_name, description in tables.items():
        print(f"\n📊 Table: {table_name} ({description})")
        
        try:
            # Get count
            with httpx.Client(timeout=15.0) as client:
                count_resp = client.get(
                    f"{SUPABASE_URL}/rest/v1/{table_name}?select=count",
                    headers={**headers, "Prefer": "count=exact"}
                )
            
            if count_resp.status_code < 300:
                count = count_resp.headers.get("Content-Range", "0/0").split("/")[-1]
                print(f"   Records: {count}")
                
                # Get recent records
                with httpx.Client(timeout=15.0) as client:
                    recent_resp = client.get(
                        f"{SUPABASE_URL}/rest/v1/{table_name}?select=*&limit=5&order=created_at.desc",
                        headers=headers
                    )
                
                if recent_resp.status_code < 300:
                    records = recent_resp.json()
                    
                    if records:
                        # Check for date fields
                        first_record = records[0]
                        date_fields = [k for k in first_record.keys() if 'at' in k.lower() or 'date' in k.lower()]
                        
                        if date_fields:
                            print(f"   Latest record dates:")
                            for field in date_fields:
                                if first_record.get(field):
                                    print(f"     - {field}: {first_record[field]}")
                        
                        print(f"   Status: ✅ Active")
                    else:
                        print(f"   Status: ⚠️  Empty")
                else:
                    print(f"   Status: ⚠️  Could not fetch records")
                
                table_info[table_name] = {
                    "count": int(count),
                    "status": "active" if int(count) > 0 else "empty"
                }
            else:
                print(f"   Status: ❌ Error - {count_resp.text}")
                table_info[table_name] = {
                    "count": 0,
                    "status": "error"
                }
        
        except Exception as e:
            print(f"   Status: ❌ Error - {e}")
            table_info[table_name] = {
                "count": 0,
                "status": "error",
                "error": str(e)
            }
    
    return table_info

def check_sync_status(chromadb_info, db_info):
    """Check if ChromaDB is in sync with database."""
    print("\n" + "=" * 80)
    print("SYNC STATUS ANALYSIS")
    print("=" * 80)
    
    # Check uploads sync
    uploads_count = db_info.get("uploads", {}).get("count", 0)
    class_files_count = db_info.get("class_files", {}).get("count", 0)
    
    print(f"\n📁 File Records in Database:")
    print(f"   - Personal uploads: {uploads_count}")
    print(f"   - Class files: {class_files_count}")
    print(f"   - Total: {uploads_count + class_files_count}")
    
    if chromadb_info:
        total_docs = sum(c.get("count", 0) for c in chromadb_info)
        print(f"\n🔍 Documents in ChromaDB:")
        print(f"   - Total: {total_docs}")
        
        if uploads_count + class_files_count == 0 and total_docs == 0:
            print(f"\n✅ Status: IN SYNC (both empty - clean state)")
        elif uploads_count + class_files_count > 0 and total_docs == 0:
            print(f"\n⚠️  Status: OUT OF SYNC")
            print(f"   - Database has {uploads_count + class_files_count} files")
            print(f"   - ChromaDB has 0 documents")
            print(f"   - Action: Run backfill_class_files.py")
        elif uploads_count + class_files_count == 0 and total_docs > 0:
            print(f"\n⚠️  Status: ORPHANED DATA")
            print(f"   - Database has 0 files")
            print(f"   - ChromaDB has {total_docs} documents")
            print(f"   - Action: Clean up ChromaDB collections")
        else:
            print(f"\n✓ Status: HAS DATA")
            print(f"   - Database: {uploads_count + class_files_count} files")
            print(f"   - ChromaDB: {total_docs} documents")
            print(f"   - Note: Document count may differ from file count (chunking)")
    else:
        print(f"\n⚠️  ChromaDB: Not available for sync check")

def main():
    print("\n🔍 Database Collections Health Check\n")
    
    # Analyze ChromaDB
    chromadb_info = analyze_chromadb_collections()
    
    # Analyze Database
    db_info = analyze_database_tables()
    
    # Check sync
    check_sync_status(chromadb_info, db_info)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if chromadb_info:
        active_collections = sum(1 for c in chromadb_info if c.get("status") == "active")
        empty_collections = sum(1 for c in chromadb_info if c.get("status") == "empty")
        error_collections = sum(1 for c in chromadb_info if c.get("status") == "error")
        
        print(f"\nChromaDB Collections:")
        print(f"  ✅ Active: {active_collections}")
        print(f"  ⚠️  Empty: {empty_collections}")
        print(f"  ❌ Error: {error_collections}")
    else:
        print(f"\nChromaDB: Not available")
    
    active_tables = sum(1 for t in db_info.values() if t.get("status") == "active")
    empty_tables = sum(1 for t in db_info.values() if t.get("status") == "empty")
    
    print(f"\nDatabase Tables:")
    print(f"  ✅ Active: {active_tables}")
    print(f"  ⚠️  Empty: {empty_tables}")
    
    print()

if __name__ == "__main__":
    main()
