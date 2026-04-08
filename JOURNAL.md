# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

> 
### Đề tài

**Trợ giảng AI - Q&A & Ôn tập cá nhân hóa**

**Mô tả bài toán**
    - Giảng viên mất 10h/tuần trả lời câu hỏi lặp lại từ 500+ sinh viên. 60% sinh viên không biết bắt đầu ôn tập từ đâu trước kỳ thi. Cần 1 platform tự động hóa hỗ trợ học tập, cá nhân hóa lộ trình học tập, và giảm tải Q&A cho giảng viên
    - Xây dựng hệ thống có khả năng upload và index tài liệu môn học (PDF, slide, video transcript); dashboard giảng viên; thống kê top câu hỏi, knowledge gaps của lớp, hệ thống gợi ý ôn tập cá nhân...

**Yêu cầu sản phẩm tối thiểu**
    - Sản phẩm web/app hoàn chỉnh - deployed online, đăng nhập & phân quyền cơ bản, giao diện UI/UX hoàn chỉnh, quản lý user

**Kỹ thuật định hướng**
    - RAG

**Tech Stack (định hướng)** 
    - LangChain + Qdrant, OpenAI/Anthropic API, Next.js hoặc Streamlit, PostgreSQL, Railway/Vercel

### Quyết định kỹ thuật
**LLM sử dụng**
    - Sử dụng gpt-4o-mini thông qua endpoint github
    - Backup sử dụng gemini-3.1-flash-lite-preview
    - Backup 1 LLM chạy local (chưa chọn)