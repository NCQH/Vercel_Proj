# File Data Reset Scripts

## Overview

These scripts help you safely reset file data while preserving users and classes.

## Scripts

### 1. `preview_reset.py` (Safe - Read Only)
**Purpose**: Preview what will be deleted before running reset

**Usage**:
```bash
python3 scripts/preview_reset.py
```

**What it shows**:
- ❌ Data to be deleted (uploads, class_files, ChromaDB)
- ✅ Data to be preserved (users, classes, class_members)
- File counts and sizes

**Run this first** to see what you're about to delete.

---

### 2. `reset_file_data.py` (Destructive)
**Purpose**: Delete all file data while preserving users and classes

**Usage**:
```bash
python3 scripts/reset_file_data.py
```

**What it does**:
1. Asks for confirmation (type "DELETE FILES")
2. Deletes all records from `uploads` table
3. Deletes all records from `class_files` table
4. Deletes all files from Supabase Storage
5. Deletes all ChromaDB collections
6. Verifies the reset

**What it preserves**:
- ✅ `users` table
- ✅ `classes` table
- ✅ `class_members` table

---

## Workflow

### Step 1: Preview
```bash
python3 scripts/preview_reset.py
```
Review what will be deleted.

### Step 2: Reset
```bash
python3 scripts/reset_file_data.py
```
Type "DELETE FILES" when prompted.

### Step 3: Verify
The script will automatically verify the reset.

---

## Use Cases

### When to use:
- 🔄 Testing the ChromaDB fix with clean data
- 🧪 Development/testing environment cleanup
- 🐛 Fixing data corruption issues
- 🔧 Resetting after major changes

### When NOT to use:
- ❌ In production without backup
- ❌ If you need to keep uploaded files
- ❌ If you're unsure about the impact

---

## Safety Features

1. **Confirmation required**: Must type "DELETE FILES" exactly
2. **Preview available**: See what will be deleted first
3. **Selective deletion**: Only deletes file data
4. **Verification**: Checks that reset was successful
5. **Preserves core data**: Users and classes remain intact

---

## After Reset

After running the reset:

1. **Upload new files**: Test the ChromaDB fix with fresh uploads
2. **Verify indexing**: Check logs for "Ingested X chunks..."
3. **Test chatbot**: Ensure files are searchable

---

## Troubleshooting

### "Storage client not initialized"
**Fix**: Check `.env` for Supabase credentials

### "Failed to delete"
**Fix**: Check Supabase permissions and API key

### "ChromaDB connection failed"
**Fix**: Verify ChromaDB credentials in `.env`

---

## Recovery

If you need to restore data after reset:

1. **Users & Classes**: Already preserved, no action needed
2. **Files**: Must re-upload manually or from backup
3. **ChromaDB**: Will be rebuilt automatically on new uploads

---

## Related Scripts

- `backfill_class_files.py` - Re-index existing files
- `check_chromadb_status.py` - Check sync status
- `test_chromadb_fix.py` - Verify ChromaDB fix

---

## Important Notes

⚠️ **This is a destructive operation**
- Cannot be undone
- All uploaded files will be lost
- ChromaDB vectors will be deleted

✅ **Safe for development**
- Users remain intact
- Classes remain intact
- Class memberships remain intact

🔒 **Production use**
- Create backup first
- Test in staging environment
- Have rollback plan ready
