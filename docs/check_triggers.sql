-- ============================================
-- CHECK AUTO UPDATE TRIGGERS STATUS
-- ============================================
-- Run this in Supabase SQL Editor to check if triggers are installed

-- Check if the trigger function exists
SELECT 
    proname as function_name,
    pg_get_functiondef(oid) as definition
FROM pg_proc 
WHERE proname = 'update_updated_at_column';

-- Check if triggers are installed on tables
SELECT 
    tgname as trigger_name,
    tgrelid::regclass as table_name,
    tgenabled as enabled,
    CASE tgenabled
        WHEN 'O' THEN '✅ Enabled'
        WHEN 'D' THEN '❌ Disabled'
        ELSE '⚠️ Unknown'
    END as status
FROM pg_trigger 
WHERE tgname LIKE 'update_%_updated_at'
ORDER BY tgrelid::regclass;

-- Expected output if triggers are installed:
-- trigger_name                      | table_name      | enabled | status
-- ----------------------------------+-----------------+---------+-------------
-- update_classes_updated_at         | classes         | O       | ✅ Enabled
-- update_roadmap_items_updated_at   | roadmap_items   | O       | ✅ Enabled
-- update_roadmap_plans_updated_at   | roadmap_plans   | O       | ✅ Enabled
-- update_users_updated_at           | users           | O       | ✅ Enabled

-- If you see 0 rows, triggers are NOT installed yet!
