# Tổng hợp chức năng hiện có trong project

## 1) Tổng quan
Project hiện tại là hệ thống **AI Teaching Assistant** với:
- Frontend: Next.js App Router
- Backend: FastAPI (`api/index.py`)
- Auth: NextAuth (Google)
- Data/Storage: Supabase + local uploads
- AI flow: Chat streaming + retrieval theo phạm vi quyền truy cập

---

## 2) Chức năng frontend theo màn hình

### 2.1. Xác thực & onboarding
- **Đăng nhập Google** tại `/login`
  - Nút `Login with Google` (đi thẳng vào luồng sử dụng)
  - Nút `Sign up with Google` (đi vào onboarding)
- **Onboarding hồ sơ** tại `/signup`
  - Nhập `full_name`
  - Chọn `role`: `student` hoặc `lecturer`
  - Lưu hồ sơ qua API `/api/users/onboard`
  - Nếu đã onboard thì tự động chuyển hướng đúng vai trò

### 2.2. Layout dùng chung (`MainLayout`)
- Sidebar điều hướng theo vai trò:
  - Student: Chat / Roadmap / Materials
  - Lecturer: Dashboard / Materials
- **Role guard**: chặn mở sai khu vực theo role, tự redirect về đúng trang
- **Account menu** (chỉ 1 vị trí global):
  - Hiển thị avatar, tên, email, role
  - Đăng xuất
- **New materials indicator** (student):
  - Hiển thị chấm thông báo tại menu Materials khi có file lớp mới

### 2.3. Student
#### `/student/chat`
- Chat với AI assistant theo dạng streaming (`/api/chat/stream`)
- Tải lịch sử chat (`/api/chat/history`)
- Upload file cá nhân ngay trong khung chat (`/api/upload`)
- Gửi message bằng Enter (Shift+Enter xuống dòng)
- Có danh sách “Suggested topics” (roadmap gợi ý UI)

#### `/student/materials`
- Xem danh sách lớp công khai
- Gửi yêu cầu tham gia lớp (`/api/classes/join`)
- Xem trạng thái membership (pending/approved/rejected)
- Xem/tải file lớp đã được quyền truy cập (`/api/class-files`, `/api/class-files/download`)
- Xem/tải file cá nhân đã upload (`/api/uploads`, `/api/uploads/download`)

#### `/student/roadmap`
- Trang roadmap student đã có route, mức hoàn thiện chi tiết phụ thuộc component hiện tại

### 2.4. Lecturer
#### `/lecturer/materials`
- Tạo lớp học (`/api/classes`)
- Xem danh sách lớp đã tạo
- Xem yêu cầu tham gia lớp đang chờ duyệt (`/api/classes/pending`)
- Duyệt / từ chối membership (`/api/classes/members/{membership_id}/approve`)
- Upload file cho lớp (`/api/class-files/upload`)
- Xem / tải file lớp (`/api/class-files`, `/api/class-files/download`)

#### `/lecturer/dashboard`
- Có giao diện dashboard cơ bản (placeholder UI cho analytics/KPI)

---

## 3) Chức năng backend API (FastAPI)

Các endpoint chính đang có trong `api/index.py`:

### 3.1. Chat / AI
- `POST /api/chat`
- `POST /api/chat/stream`
- `GET /api/chat/history`
- `GET /api/memory/debug`

### 3.2. Upload cá nhân
- `POST /api/upload`
- `GET /api/uploads`
- `GET /api/uploads/download`

### 3.3. Class management
- `GET /api/classes`
- `GET /api/classes/public`
- `GET /api/classes/pending`
- `POST /api/classes`
- `PATCH /api/classes/{class_id}`
- `POST /api/classes/join`
- `POST /api/classes/members/{membership_id}/approve`

### 3.4. Class files
- `GET /api/class-files`
- `POST /api/class-files/upload`
- `GET /api/class-files/download`

### 3.5. Khác
- `GET /api/health`

### 3.6. Next.js API routes (frontend server)
- `POST /api/users/onboard`
- `GET /api/users/me`
- `...nextauth` route cho auth

---

## 4) Quyền truy cập & phân tách dữ liệu
- User chưa đăng nhập bị điều hướng về `/login`
- Role-based routing giữa student/lecturer
- Student chỉ thấy file lớp khi membership được approve
- Tải file có kiểm tra ownership/quyền truy cập theo `user_id + file_id`
- Retrieval đã có scope theo user/access (tránh global mặc định)

---

## 5) Trạng thái tính năng hiện tại

### Đã hoạt động chính
- Đăng nhập Google + onboarding role
- Chat AI streaming + lịch sử chat
- Upload/list/download file cá nhân
- Luồng lớp học cơ bản: tạo lớp, join, approve/reject
- Upload/list/download file theo lớp
- Layout chung + account menu + role guard

### Đang ở mức cơ bản / placeholder
- Lecturer dashboard analytics (hiện là UI placeholder)
- Roadmap nâng cao/cá nhân hóa học tập (mới mức hiển thị/gợi ý)

---

## 6) Luồng nghiệp vụ chính
1. User đăng nhập Google
2. Nếu chưa onboard -> vào `/signup` để chọn role
3. Student:
   - Chat AI
   - Join lớp
   - Nhận quyền file lớp khi được lecturer duyệt
4. Lecturer:
   - Tạo lớp
   - Duyệt yêu cầu tham gia
   - Upload tài liệu lớp
5. AI retrieval phục vụ trả lời dựa trên phạm vi tài liệu user được phép truy cập
