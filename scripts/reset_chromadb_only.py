#!/usr/bin/env python3
"""
Clean up ChromaDB collections only (keep database intact).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.rag.vectorstore import get_chroma_client

def confirm_cleanup():
    """Ask for user confirmation."""
    print("=" * 80)
    print("⚠️  CHROMADB CLEANUP")
    print("=" * 80)
    print("\nThis will DELETE:")
    print("  ❌ All ChromaDB collections")
    print("  ❌ All vector embeddings")
    print("\nThis will PRESERVE:")
    print("  ✅ Database (users, classes, files)")
    print("  ✅ Supabase Storage files")
    print("\n⚠️  THIS CANNOT BE UNDONE!")
    print("=" * 80)
    
    response = input("\nType 'DELETE CHROMADB' to confirm: ")
    return response.strip() == "DELETE CHROMADB"

def cleanup_chromadb():
    """Delete all ChromaDB collections."""
    print("\n🚀 Starting ChromaDB cleanup...\n")
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            print("✓ No collections to delete (already clean)")
            return True
        
        print(f"Found {len(collections)} collection(s) to delete:\n")
        
        deleted = 0
        failed = 0
        
        for col in collections:
            try:
                count = col.count()
                print(f"Deleting: {col.name} ({count} documents)...")
                client.delete_collection(name=col.name)
                print(f"  ✓ Deleted")
                deleted += 1
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                failed += 1
        
        print("\n" + "=" * 80)
        print("CLEANUP SUMMARY")
        print("=" * 80)
        print(f"✓ Deleted: {deleted} collections")
        if failed > 0:
            print(f"❌ Failed: {failed} collections")
        print()
        
        return failed == 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def verify_cleanup():
    """Verify cleanup was successful."""
    print("Verifying cleanup...")
    
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if len(collections) == 0:
            print("✓ ChromaDB is clean (0 collections)")
            return True
        else:
            print(f"⚠️  Still have {len(collections)} collection(s)")
            return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    print("\n🗑️  ChromaDB Cleanup Script\n")
    
    # Confirm
    if not confirm_cleanup():
        print("\n❌ Cleanup cancelled by user")
        return
    
    # Cleanup
    success = cleanup_chromadb()
    
    # Verify
    if success:
        verify_cleanup()
        print("\n🎉 ChromaDB cleanup completed!")
        print("\nNext steps:")
        print("1. Upload new files via UI")
        print("2. Files will be indexed into fresh collections")
        print("3. Test chatbot with new files")
    else:
        print("\n⚠️  Some collections failed to delete")
        print("Check the errors above")
    
    print()

if __name__ == "__main__":
    main()
