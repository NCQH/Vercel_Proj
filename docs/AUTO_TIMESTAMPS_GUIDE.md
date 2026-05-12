# Auto Update Timestamps - Implementation Guide

## 📋 Overview

Tự động cập nhật cột `updated_at` khi có bất kỳ thay đổi nào trên các bảng quan trọng.

**Benefit:** Không cần manually set `updated_at` trong code nữa.

---

## 🚀 Quick Start

### Step 1: Backup Database (IMPORTANT!)

```bash
# Replace with your actual Supabase credentials
pg_dump -h your-supabase-host.supabase.co \
        -U postgres \
        -d postgres \
        > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Apply SQL Script

**Option A: Via Supabase Dashboard**
1. Go to Supabase Dashboard → SQL Editor
2. Copy content from `docs/auto_update_timestamps.sql`
3. Click "Run"
4. Verify output shows 4 triggers installed

**Option B: Via psql**
```bash
psql -h your-supabase-host.supabase.co \
     -U postgres \
     -d postgres \
     -f docs/auto_update_timestamps.sql
```

### Step 3: Verify Installation

Run this query in SQL Editor:
```sql
SELECT 
    tgname as trigger_name,
    tgrelid::regclass as table_name,
    tgenabled as enabled
FROM pg_trigger 
WHERE tgname LIKE 'update_%_updated_at'
ORDER BY tgrelid::regclass;
```

Expected output:
```
trigger_name                      | table_name      | enabled
----------------------------------+-----------------+---------
update_classes_updated_at         | classes         | O
update_roadmap_items_updated_at   | roadmap_items   | O
update_roadmap_plans_updated_at   | roadmap_plans   | O
update_users_updated_at           | users           | O
```

### Step 4: Test the Triggers

```sql
-- Test on classes table (replace with actual ID)
UPDATE classes SET name = 'Test Update' WHERE id = 'your-class-id';

-- Check if updated_at changed
SELECT id, name, updated_at FROM classes WHERE id = 'your-class-id';
```

The `updated_at` should show current timestamp!

---

## 🔧 What Gets Updated

### Tables with Auto Timestamps

1. **users** - User profile updates
2. **classes** - Class information updates
3. **roadmap_plans** - Roadmap plan updates
4. **roadmap_items** - Roadmap item updates (status, progress)

### How It Works

```sql
-- Before (manual in code)
UPDATE classes SET name = 'New Name', updated_at = NOW() WHERE id = 'xxx';

-- After (automatic)
UPDATE classes SET name = 'New Name' WHERE id = 'xxx';
-- updated_at is set automatically by trigger!
```

---

## 🧹 Code Cleanup (Optional)

After applying triggers, you can remove manual `updated_at` updates from code:

### Before
```python
# api/routes/roadmap.py
payload = {
    "status": status,
    "updated_at": datetime.now(timezone.utc).isoformat()  # ❌ Not needed anymore
}
```

### After
```python
# api/routes/roadmap.py
payload = {
    "status": status
    # updated_at will be set automatically by trigger ✅
}
```

**Note:** This cleanup is optional. The trigger will override any manual value anyway.

---

## ⚠️ Important Notes

### 1. Trigger Fires on UPDATE Only
- ✅ Fires on: `UPDATE` statements
- ❌ Does NOT fire on: `INSERT` (uses default NOW())
- ❌ Does NOT fire on: `DELETE`

### 2. Applies to ALL Updates
- Even if you don't change any data
- `UPDATE table SET col = col` will still update timestamp

### 3. Cannot Be Bypassed
- Trigger always fires before UPDATE
- Even if you manually set `updated_at`, trigger will override it

---

## 🔄 Rollback Instructions

If you need to remove the triggers:

```sql
-- Remove all triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_classes_updated_at ON classes;
DROP TRIGGER IF EXISTS update_roadmap_plans_updated_at ON roadmap_plans;
DROP TRIGGER IF EXISTS update_roadmap_items_updated_at ON roadmap_items;

-- Remove the function
DROP FUNCTION IF EXISTS update_updated_at_column();
```

Then restore from backup if needed:
```bash
psql -h your-host -U postgres -d postgres < backup_YYYYMMDD_HHMMSS.sql
```

---

## ✅ Testing Checklist

- [ ] Backup database created
- [ ] SQL script applied successfully
- [ ] 4 triggers verified in pg_trigger
- [ ] Test UPDATE on classes table
- [ ] Verify updated_at changed automatically
- [ ] Test UPDATE on users table
- [ ] Test UPDATE on roadmap_items table
- [ ] Document completion in WEEK1_PROGRESS.md

---

## 📊 Impact

**Before:**
- Manual `updated_at` management in code
- Risk of forgetting to update timestamp
- Inconsistent timestamp updates

**After:**
- ✅ Automatic timestamp updates
- ✅ No risk of forgetting
- ✅ Consistent across all updates
- ✅ Less code to maintain

**Time Saved:** ~2 hours (no more manual timestamp management)

---

## 🎯 Next Steps

After completing this:
1. Update WEEK1_PROGRESS.md
2. Move to Phase 1.5: Improved Delete Operations
3. Continue with Week 1 roadmap

---

**Status:** Ready to apply  
**Estimated Time:** 15-30 minutes  
**Risk Level:** Low (easily reversible)
