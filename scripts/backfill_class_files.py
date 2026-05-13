#!/usr/bin/env python3
"""
Backfill script to ingest existing class files into ChromaDB.
This will process all class files that are in the database but not in ChromaDB.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
import tempfile
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader

from src.rag.vectorstore import get_vectorstore, add_documents
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY
from api.lib.storage import storage_client, CLASS_FILES_BUCKET

def get_all_class_files():
    """Fetch all class files from database."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{SUPABASE_URL}/rest/v1/class_files?select=file_id,class_id,original_filename,stored_path",
            headers=headers
        )
    
    if resp.status_code >= 300:
        raise Exception(f"Failed to fetch class files: {resp.text}")
    
    return resp.json()

def ingest_file(file_data: dict) -> bool:
    """
    Ingest a single file into ChromaDB.
    
    Returns: True if successful, False otherwise
    """
    file_id = file_data.get("file_id")
    class_id = file_data.get("class_id")
    filename = file_data.get("original_filename")
    stored_path = file_data.get("stored_path")
    
    print(f"Processing: {filename} (class: {class_id})")
    
    try:
        # Download file from storage
        content = storage_client.download_file(bucket=CLASS_FILES_BUCKET, path=stored_path)
        
        # Load document
        ext = Path(filename).suffix.lower()
        docs = []
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            if ext == ".pdf":
                docs = PyMuPDFLoader(tmp_path).load()
            elif ext == ".docx":
                docs = Docx2txtLoader(tmp_path).load()
            elif ext in {".txt", ".md"}:
                docs = TextLoader(tmp_path, encoding="utf-8").load()
            else:
                print(f"  ⚠️  Unsupported file type: {ext}")
                return False
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        
        if not docs:
            print(f"  ⚠️  No content extracted")
            return False
        
        # Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        chunks = splitter.split_documents(docs)
        
        # Add metadata
        for chunk in chunks:
            chunk.metadata = {
                **(chunk.metadata or {}),
                "class_id": class_id,
                "source": filename,
                "stored_path": stored_path,
                "file_id": file_id
            }
        
        # Ingest into ChromaDB
        vectorstore = get_vectorstore(user_id=f"class_{class_id}")
        add_documents(vectorstore, chunks)
        
        print(f"  ✓ Ingested {len(chunks)} chunks")
        return True
    
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("\n🔄 Backfilling Class Files into ChromaDB\n")
    print("=" * 80)
    
    if not storage_client:
        print("❌ Storage client not initialized. Check your environment variables.")
        return
    
    # Fetch all class files
    print("Fetching class files from database...")
    try:
        files = get_all_class_files()
        print(f"Found {len(files)} class files\n")
    except Exception as e:
        print(f"❌ Failed to fetch files: {e}")
        return
    
    if not files:
        print("No files to process.")
        return
    
    # Process each file
    success_count = 0
    fail_count = 0
    
    for i, file_data in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}]")
        if ingest_file(file_data):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("BACKFILL SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(files)}")
    print(f"✓ Success: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print()

if __name__ == "__main__":
    main()
