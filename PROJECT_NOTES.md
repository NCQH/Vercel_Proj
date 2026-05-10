# PROJECT_NOTES

## Mục tiêu
- AI Teaching Assistant (Next.js + FastAPI + LangGraph + RAG + Supabase).
- Student có chat, upload tài liệu, xem danh sách, tải file đã upload.

## Luồng chính
- Chat: `/api/chat/stream` -> `run_agent()` -> graph `router -> retrieval/tutor`.
- Upload: `/api/upload` -> lưu file local + ingest vectorstore + lưu metadata Supabase.
- List file: `/api/uploads`.
- Download file: `/api/uploads/download` (check ownership theo `user_id + file_id`).

## Trạng thái hiện tại
- Account button chỉ còn 1 chỗ ở `MainLayout`.
- Router có guardrail cho câu hỏi học tập.
- Tutor có low-confidence fallback khi retrieval yếu.
- Khi low-confidence reply: không append Sources.
- Retrieval đã sửa scope theo `user_id` (không còn default global).
- Đã thêm logs router/tutor + source retrieval.

## Ghi chú vận hành
- Dev servers đang dùng:
  - `npm run dev`
  - `uvicorn api.index:app --reload --port 8000`

## TODO bạn có thể chỉnh ở đây
- Lecture sẽ có thể tạo các lớp học, chỉnh sửa thông tin lớp học
- Tải file lên lớp học
- Học sinh có thể tham gia vào các lớp học, có thể xem file được lecture tải lên ở lớp học
- LLM được phép retrie vào các file mà user có thể truy cập

