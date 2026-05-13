# ChromaDB Scripts

This directory contains scripts for managing and maintaining ChromaDB vector store.

## Scripts Overview

### 1. `test_chromadb_fix.py`
**Purpose**: Verify that the ChromaDB fix is working correctly

**Usage**:
```bash
python3 scripts/test_chromadb_fix.py
```

**What it tests**:
- All required imports are available
- ChromaDB connection is working
- Document loaders (PDF, DOCX, TXT) are functional
- Text splitter is working
- Lists existing collections

**When to run**: After applying the fix, before deploying to production

---

### 2. `check_chromadb_status.py`
**Purpose**: Check the current status of ChromaDB and compare with database records

**Usage**:
```bash
python3 scripts/check_chromadb_status.py
```

**What it shows**:
- All ChromaDB collections and document counts
- Database file counts (user uploads + class files)
- Discrepancies between database and ChromaDB
- Recommendations for fixing issues

**When to run**: 
- To diagnose sync issues
- After backfilling
- As part of regular health checks

---

### 3. `backfill_class_files.py`
**Purpose**: Ingest all existing class files into ChromaDB

**Usage**:
```bash
python3 scripts/backfill_class_files.py
```

**What it does**:
1. Fetches all class files from Supabase database
2. Downloads each file from Supabase Storage
3. Processes and chunks the content
4. Ingests into ChromaDB with proper metadata
5. Reports success/failure for each file

**When to run**: 
- **REQUIRED**: After applying the ChromaDB fix (one-time)
- After any data migration
- If ChromaDB data is lost or corrupted

**Important Notes**:
- Requires valid Supabase credentials in environment
- May take time depending on number of files
- Safe to run multiple times (will re-ingest files)

---

## Workflow

### Initial Setup (After Fix)

1. **Test the fix**:
   ```bash
   python3 scripts/test_chromadb_fix.py
   ```
   Ensure all tests pass before proceeding.

2. **Check current status**:
   ```bash
   python3 scripts/check_chromadb_status.py
   ```
   This will show how many files are missing from ChromaDB.

3. **Backfill existing files**:
   ```bash
   python3 scripts/backfill_class_files.py
   ```
   This will process all existing class files.

4. **Verify backfill**:
   ```bash
   python3 scripts/check_chromadb_status.py
   ```
   Confirm that ChromaDB now has all the files.

### Regular Maintenance

Run status check periodically to ensure sync:
```bash
python3 scripts/check_chromadb_status.py
```

If discrepancies are found, run backfill again.

---

## Environment Requirements

All scripts require:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `CHROMA_API_KEY` (optional) - If using Chroma Cloud
- `CHROMA_TENANT` (optional) - Chroma Cloud tenant
- `CHROMA_DATABASE` (optional) - Chroma Cloud database

---

## Troubleshooting

### "Storage client not initialized"
**Cause**: Missing Supabase credentials

**Fix**: Check your `.env` file:
```bash
cat .env | grep SUPABASE
```

### "Failed to connect to ChromaDB"
**Cause**: ChromaDB service not running or wrong credentials

**Fix**: 
- If using local ChromaDB: Ensure it's running
- If using Chroma Cloud: Check API key and credentials

### "No collections found"
**Cause**: No files have been uploaded yet, or backfill hasn't been run

**Fix**: 
- Upload a test file through the UI
- Or run the backfill script

### Backfill script hangs
**Cause**: Large files or slow network

**Fix**: 
- Check network connection
- Consider processing files in batches
- Increase timeout in httpx client

---

## Adding New Scripts

When adding new maintenance scripts:

1. Add to this README with description and usage
2. Include error handling and logging
3. Make scripts idempotent (safe to run multiple times)
4. Add to the workflow section if relevant

---

## Support

For issues or questions:
1. Check the main project documentation
2. Review logs in the application
3. Run diagnostic scripts to identify the issue
