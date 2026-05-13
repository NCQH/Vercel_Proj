#!/usr/bin/env python3
"""
Script to check ChromaDB status and compare with database records.
This will help identify missing vectors for uploaded files.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from src.rag.vectorstore import get_chroma_client
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

def check_chromadb_collections():
    """List all ChromaDB collections and their document counts."""
    print("=" * 80)
    print("CHROMADB COLLECTIONS STATUS")
    print("=" * 80)
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            print("⚠️  No collections found in ChromaDB!")
            return {}
        
        collection_stats = {}
        for col in collections:
            count = col.count()
            collection_stats[col.name] = count
            print(f"✓ Collection: {col.name}")
            print(f"  Documents: {count}")
            print()
        
        return collection_stats
    except Exception as e:
        print(f"❌ Error accessing ChromaDB: {e}")
        return {}

def check_database_files():
    """Check files in Supabase database."""
    print("=" * 80)
    print("DATABASE FILES STATUS")
    print("=" * 80)
    
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Check user uploads
        with httpx.Client(timeout=15.0) as client:
            uploads_resp = client.get(
                f"{SUPABASE_URL}/rest/v1/uploads?select=file_id,user_id,original_filename,uploaded_at",
                headers=headers
            )
        
        if uploads_resp.status_code < 300:
            uploads = uploads_resp.json()
            print(f"📁 User Uploads: {len(uploads)} files")
            for upload in uploads[:5]:  # Show first 5
                print(f"   - {upload.get('original_filename')} (user: {upload.get('user_id')})")
            if len(uploads) > 5:
                print(f"   ... and {len(uploads) - 5} more")
        else:
            print(f"❌ Failed to fetch uploads: {uploads_resp.status_code}")
            uploads = []
        
        print()
        
        # Check class files
        with httpx.Client(timeout=15.0) as client:
            class_files_resp = client.get(
                f"{SUPABASE_URL}/rest/v1/class_files?select=file_id,class_id,original_filename,uploaded_at",
                headers=headers
            )
        
        if class_files_resp.status_code < 300:
            class_files = class_files_resp.json()
            print(f"📚 Class Files: {len(class_files)} files")
            for cf in class_files[:5]:  # Show first 5
                print(f"   - {cf.get('original_filename')} (class: {cf.get('class_id')})")
            if len(class_files) > 5:
                print(f"   ... and {len(class_files) - 5} more")
        else:
            print(f"❌ Failed to fetch class files: {class_files_resp.status_code}")
            class_files = []
        
        print()
        return {"uploads": uploads, "class_files": class_files}
    
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return {"uploads": [], "class_files": []}

def analyze_discrepancies(collection_stats, db_files):
    """Analyze discrepancies between ChromaDB and database."""
    print("=" * 80)
    print("DISCREPANCY ANALYSIS")
    print("=" * 80)
    
    uploads_count = len(db_files.get("uploads", []))
    class_files_count = len(db_files.get("class_files", []))
    
    print(f"Database Records:")
    print(f"  - User uploads: {uploads_count}")
    print(f"  - Class files: {class_files_count}")
    print(f"  - Total: {uploads_count + class_files_count}")
    print()
    
    print(f"ChromaDB Collections:")
    total_vectors = sum(collection_stats.values())
    for name, count in collection_stats.items():
        print(f"  - {name}: {count} documents")
    print(f"  - Total: {total_vectors} documents")
    print()
    
    # Check for class collections
    class_collections = [name for name in collection_stats.keys() if name.startswith("rag_docs_class_")]
    
    if class_files_count > 0 and not class_collections:
        print("🚨 CRITICAL ISSUE DETECTED:")
        print(f"   - {class_files_count} class files in database")
        print(f"   - 0 class collections in ChromaDB")
        print(f"   - This confirms class files are NOT being ingested!")
        print()
    elif class_files_count > 0 and class_collections:
        print("⚠️  POTENTIAL ISSUE:")
        print(f"   - {class_files_count} class files in database")
        print(f"   - {len(class_collections)} class collections in ChromaDB")
        print(f"   - Need to verify if all files are properly indexed")
        print()
    
    if uploads_count > 0:
        user_collections = [name for name in collection_stats.keys() if not name.startswith("rag_docs_class_")]
        if user_collections:
            print("✓ User uploads appear to be working correctly")
        else:
            print("⚠️  User uploads may also have issues")
    
    print()

def main():
    print("\n🔍 ChromaDB Status Check\n")
    
    # Check ChromaDB
    collection_stats = check_chromadb_collections()
    
    # Check Database
    db_files = check_database_files()
    
    # Analyze
    analyze_discrepancies(collection_stats, db_files)
    
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("1. Fix the upload_class_file() function to ingest into ChromaDB")
    print("2. Run backfill script to ingest existing class files")
    print("3. Add monitoring to prevent this from happening again")
    print()

if __name__ == "__main__":
    main()
