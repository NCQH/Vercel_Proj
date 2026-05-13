#!/usr/bin/env python3
"""
Quick test to verify the ChromaDB fix is working.
This simulates the upload process without actually uploading files.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    """Test that all required imports are available."""
    print("Testing imports...")
    try:
        from api.routes.classes import (
            tempfile, Path, RecursiveCharacterTextSplitter,
            PyMuPDFLoader, TextLoader, Docx2txtLoader
        )
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_vectorstore_connection():
    """Test ChromaDB connection."""
    print("\nTesting ChromaDB connection...")
    try:
        from src.rag.vectorstore import get_chroma_client, get_vectorstore
        
        client = get_chroma_client()
        print(f"✓ ChromaDB client initialized: {type(client).__name__}")
        
        # Test getting a vectorstore
        test_store = get_vectorstore(user_id="test_class_123")
        print(f"✓ Vectorstore created: {test_store.collection_name}")
        
        return True
    except Exception as e:
        print(f"❌ ChromaDB connection failed: {e}")
        return False

def test_document_loaders():
    """Test that document loaders are working."""
    print("\nTesting document loaders...")
    try:
        from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader
        print("✓ PyMuPDFLoader available")
        print("✓ TextLoader available")
        print("✓ Docx2txtLoader available")
        return True
    except ImportError as e:
        print(f"❌ Document loader import failed: {e}")
        return False

def test_text_splitter():
    """Test text splitter."""
    print("\nTesting text splitter...")
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        
        # Test with sample text
        from langchain.schema import Document
        test_doc = Document(page_content="This is a test document. " * 100, metadata={"source": "test.txt"})
        chunks = splitter.split_documents([test_doc])
        
        print(f"✓ Text splitter working: created {len(chunks)} chunks from test document")
        return True
    except Exception as e:
        print(f"❌ Text splitter failed: {e}")
        return False

def check_existing_collections():
    """Check what collections currently exist."""
    print("\nChecking existing ChromaDB collections...")
    try:
        from src.rag.vectorstore import get_chroma_client
        
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            print("⚠️  No collections found (this is normal if no files have been uploaded yet)")
        else:
            print(f"Found {len(collections)} collection(s):")
            for col in collections:
                count = col.count()
                print(f"  - {col.name}: {count} documents")
                if col.name.startswith("rag_docs_class_"):
                    print(f"    ✓ This is a class collection")
        
        return True
    except Exception as e:
        print(f"❌ Failed to check collections: {e}")
        return False

def main():
    print("=" * 80)
    print("CHROMADB FIX VERIFICATION TEST")
    print("=" * 80)
    print()
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("ChromaDB Connection", test_vectorstore_connection()))
    results.append(("Document Loaders", test_document_loaders()))
    results.append(("Text Splitter", test_text_splitter()))
    results.append(("Existing Collections", check_existing_collections()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The fix is ready to use.")
        print("\nNext steps:")
        print("1. Run: python3 scripts/backfill_class_files.py")
        print("2. Test uploading a new class file")
        print("3. Verify the file is searchable via chatbot")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    print()

if __name__ == "__main__":
    main()
