# Product Requirement Document (PRD) 
# Dự kiến

## 1. Product Overview

### Product Name
AI Learning Assistant for University Courses

### Product Description
AI Learning Assistant là một hệ thống chatbot hỗ trợ sinh viên ôn tập và tìm kiếm thông tin từ tài liệu học tập như slide bài giảng, PDF hoặc tài liệu tham khảo. Hệ thống sử dụng mô hình ngôn ngữ lớn (LLM) kết hợp với phương pháp Retrieval-Augmented Generation (RAG) để trả lời câu hỏi của sinh viên dựa trên nội dung tài liệu môn học.

Hệ thống giúp:
- Sinh viên tìm câu trả lời nhanh từ tài liệu
- Tóm tắt nội dung bài học
- Giảm số lượng câu hỏi lặp lại gửi đến giảng viên

---

# 2. Problem Statement

Trong các lớp học đại học có số lượng sinh viên lớn (300–500 sinh viên), giảng viên phải dành nhiều thời gian để trả lời các câu hỏi giống nhau từ sinh viên. Đồng thời, sinh viên thường gặp khó khăn khi ôn tập vì không biết bắt đầu từ đâu và phải đọc nhiều tài liệu để tìm thông tin cần thiết.

Điều này dẫn đến:

- Giảng viên bị quá tải khi hỗ trợ sinh viên
- Sinh viên tốn nhiều thời gian tìm kiếm thông tin
- Không có hệ thống hỗ trợ học tập hiệu quả

---

# 3. Target Users

## Primary Users

### Sinh viên
- Sinh viên đại học
- Cần ôn tập sau buổi học
- Cần hỗ trợ trước kỳ thi

### Giảng viên
- Dạy lớp có số lượng sinh viên lớn
- Muốn giảm các câu hỏi lặp lại từ sinh viên

---

# 4. Goals & Success Metrics

## Product Goals

- Giúp sinh viên tìm thông tin nhanh từ tài liệu môn học
- Giảm số lượng câu hỏi lặp lại gửi cho giảng viên
- Hỗ trợ sinh viên ôn tập hiệu quả hơn

## Success Metrics

- ≥ 100 sinh viên sử dụng hệ thống trong giai đoạn thử nghiệm
- ≥ 70% câu hỏi được chatbot trả lời từ tài liệu
- Giảm ≥ 30% câu hỏi lặp lại gửi cho giảng viên
- Thời gian tìm câu trả lời < 1 phút

---

# 5. User Stories

## Sinh viên

**US1**

As a student,  
I want to ask questions about lecture slides,  
so that I can quickly understand the material.

**US2**

As a student,  
I want to receive summarized content of lecture materials,  
so that I can review quickly before exams.

**US3**

As a student,  
I want answers with citations from lecture materials,  
so that I can verify the information source.

---

## Giảng viên

**US4**

As a lecturer,  
I want students to get answers automatically from course materials,  
so that I don't have to answer repetitive questions.

---

# 6. Functional Requirements

## FR1 — Document Upload

Giảng viên có thể tải lên:

- Slide bài giảng
- PDF tài liệu
- Tài liệu tham khảo

Hệ thống sẽ:

- xử lý tài liệu
- chia nhỏ văn bản (chunking)
- tạo embedding
- lưu vào vector database

---

## FR2 — Question Answering (RAG)

Sinh viên có thể nhập câu hỏi về nội dung bài học.

Hệ thống sẽ:

1. tìm các đoạn văn liên quan trong tài liệu
2. gửi context vào LLM
3. sinh câu trả lời dựa trên tài liệu

---

## FR3 — Citation Support

Câu trả lời phải kèm trích dẫn nguồn từ tài liệu.

Ví dụ:

> Theo slide Lecture 3, trang 5:  
> "Transformer sử dụng self-attention để xử lý chuỗi."

---

## FR4 — Document Summarization

Sinh viên có thể yêu cầu:

- tóm tắt bài học
- tóm tắt chương
- tóm tắt tài liệu

---

## FR5 — Study Guidance

Hệ thống có thể:

- gợi ý các phần quan trọng cần ôn tập
- liệt kê các chủ đề chính của bài học

---

# 7. Non-Functional Requirements

## Performance
- Thời gian phản hồi < 5 giây

## Scalability
- Hỗ trợ ≥ 100 sinh viên sử dụng đồng thời

## Reliability
- Câu trả lời phải dựa trên tài liệu đã tải lên

## Security
- Chỉ người dùng trong lớp mới truy cập được tài liệu

---

# 8. MVP Scope

## Included in MVP

- Upload tài liệu (PDF / slide)
- Chatbot hỏi đáp từ tài liệu (RAG)
- Trích dẫn nguồn trong câu trả lời
- Tóm tắt tài liệu

---

## Not Included in MVP

- Mobile application
- Cá nhân hóa lộ trình học bằng AI nâng cao
- Hệ thống đánh giá năng lực học tập
- Gamification

---

# 9. System Architecture (High-Level)
Lecture Materials (PDF / Slides)
↓
Document Processing
↓
Text Chunking
↓
Embedding Model
↓
Vector Database (FAISS)
↓
Retriever
↓
LLM (GPT / Llama)
↓
Answer + Citation

---

# 10. Risks & Limitations

- Câu trả lời phụ thuộc vào chất lượng tài liệu đầu vào
- LLM có thể tạo thông tin sai nếu retrieval không chính xác
- Cần tối ưu chunking và retrieval để cải thiện độ chính xác

---

# 11. AI Components

Hệ thống sử dụng các thành phần AI sau:

- **Embedding Model**: chuyển văn bản thành vector
- **Vector Database (FAISS)**: lưu trữ embedding
- **Retriever**: tìm đoạn văn liên quan
- **Large Language Model (LLM)**: sinh câu trả lời
- **RAG Pipeline**: kết hợp retrieval và generation

---

# 12. Evaluation

Để đánh giá hệ thống, các tiêu chí sau sẽ được sử dụng:

- Retrieval accuracy
- Answer correctness
- Citation accuracy
- User satisfaction
