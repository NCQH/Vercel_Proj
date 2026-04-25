# AI Model Documentation

## Overview

Hệ thống sử dụng RAG để kết hợp:

- Retrieval (tìm tài liệu)
- Generation (LLM sinh câu trả lời)

---

# AI Components

## Embedding Model

Chức năng:

chuyển text thành vector để tìm kiếm similarity.

Ví dụ:

- text-embedding-3-small
- BGE-small

---

# Vector Database

Lưu trữ embedding.

Ví dụ:

- FAISS

---

# Retriever

Tìm các đoạn văn liên quan nhất.

Cấu hình:
top_k = 5


---

# Large Language Model (LLM)

LLM nhận:

- câu hỏi
- context từ retrieval

Sau đó sinh câu trả lời.

Ví dụ:

- GPT
- Llama

---

# Prompt Design

Prompt template:
You are an AI teaching assistant.

Use the provided context to answer the question.

Context:
{retrieved_chunks}

Question:
{user_question}

Answer:


---

# Output Format

Câu trả lời nên:

- rõ ràng
- ngắn gọn
- có trích dẫn nguồn