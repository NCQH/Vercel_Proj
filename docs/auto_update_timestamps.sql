-- ============================================
-- AUTO UPDATE TIMESTAMPS - Quick Apply Script
-- ============================================
-- Tự động cập nhật updated_at khi có thay đổi
-- Run in Supabase SQL Editor

-- -----------------
-- 1. CREATE TRIGGER FUNCTION
-- -----------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- -----------------
-- 2. APPLY TO USERS TABLE
-- -----------------
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------
-- 3. APPLY TO CLASSES TABLE
-- -----------------
DROP TRIGGER IF EXISTS update_classes_updated_at ON classes;
CREATE TRIGGER update_classes_updated_at 
    BEFORE UPDATE ON classes
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------
-- 4. APPLY TO ROADMAP_PLANS TABLE
-- -----------------
DROP TRIGGER IF EXISTS update_roadmap_plans_updated_at ON roadmap_plans;
CREATE TRIGGER update_roadmap_plans_updated_at 
    BEFORE UPDATE ON roadmap_plans
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------
-- 5. APPLY TO ROADMAP_ITEMS TABLE
-- -----------------
DROP TRIGGER IF EXISTS update_roadmap_items_updated_at ON roadmap_items;
CREATE TRIGGER update_roadmap_items_updated_at 
    BEFORE UPDATE ON roadmap_items
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- -----------------
-- 6. VERIFY INSTALLATION
-- -----------------
-- Check if triggers are installed
SELECT 
    tgname as trigger_name,
    tgrelid::regclass as table_name,
    tgenabled as enabled
FROM pg_trigger 
WHERE tgname LIKE 'update_%_updated_at'
ORDER BY tgrelid::regclass;

-- Expected output:
-- trigger_name                      | table_name      | enabled
-- ----------------------------------+-----------------+---------
-- update_classes_updated_at         | classes         | O
-- update_roadmap_items_updated_at   | roadmap_items   | O
-- update_roadmap_plans_updated_at   | roadmap_plans   | O
-- update_users_updated_at           | users           | O

-- -----------------
-- 7. TEST THE TRIGGERS
-- -----------------
-- Test on classes table (replace with actual class_id)
-- UPDATE classes SET name = name WHERE id = 'your-class-id-here';
-- SELECT id, name, updated_at FROM classes WHERE id = 'your-class-id-here';
-- Verify that updated_at has changed

-- -----------------
-- ROLLBACK (if needed)
-- -----------------
-- DROP TRIGGER IF EXISTS update_users_updated_at ON users;
-- DROP TRIGGER IF EXISTS update_classes_updated_at ON classes;
-- DROP TRIGGER IF EXISTS update_roadmap_plans_updated_at ON roadmap_plans;
-- DROP TRIGGER IF EXISTS update_roadmap_items_updated_at ON roadmap_items;
-- DROP FUNCTION IF EXISTS update_updated_at_column();
