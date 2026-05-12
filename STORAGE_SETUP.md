# Setup Supabase Storage - Quick Guide

## 🚀 Cách nhanh nhất (2 bước)

### Bước 1: Tạo buckets (chọn 1 trong 3 cách)

**Cách A: Python script (Đơn giản nhất)**
```bash
python setup_buckets.py
```

**Cách B: Bash script**
```bash
chmod +x setup_storage.sh
./setup_storage.sh
```

**Cách C: Manual curl**
```bash
source .env

curl -X POST "$SUPABASE_URL/storage/v1/bucket" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"id":"user-uploads","name":"user-uploads","public":false,"file_size_limit":20971520}'

curl -X POST "$SUPABASE_URL/storage/v1/bucket" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"id":"class-files","name":"class-files","public":false,"file_size_limit":20971520}'
```

### Bước 2: Setup RLS Policies

**Vào Supabase SQL Editor:**
1. Mở: https://supabase.com/dashboard/project/ebeyqqmzkdaxoszdqrka/sql/new
2. Copy toàn bộ nội dung file `supabase_storage_setup.sql`
3. Paste và click **Run**

✅ Xong!

---

## 📁 Files trong project

- `supabase_storage_setup.sql` - SQL script đầy đủ (buckets + policies)
- `setup_buckets.py` - Python script tạo buckets
- `setup_storage.sh` - Bash script tự động
- `STORAGE_SETUP.md` - File này

---

## ✅ Verify

```bash
# Check buckets
curl "$SUPABASE_URL/storage/v1/bucket" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"

# Test upload
curl -X POST "$SUPABASE_URL/storage/v1/object/user-uploads/test/hello.txt" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: text/plain" \
  --data "Hello World"
```

---

## 🔧 Troubleshooting

**Lỗi: "Bucket already exists"**
- Bình thường, buckets đã được tạo rồi
- Chỉ cần chạy bước 2 (RLS policies)

**Lỗi: "Invalid API key"**
- Check `SUPABASE_SERVICE_ROLE_KEY` trong `.env`
- Phải dùng service_role key, không phải anon key

**Lỗi: "Permission denied"**
- RLS policies chưa được setup
- Chạy lại bước 2

---

## 📚 Chi tiết đầy đủ

Xem file `setup_storage_guide.md` trong artifacts để biết thêm chi tiết về:
- Cách dùng Supabase CLI
- Cách dùng psql
- Giải thích từng policy
