# System Architecture Document

## Overview

Hệ thống AI Learning Assistant được thiết kế theo kiến trúc RAG (Retrieval-Augmented Generation) để trả lời câu hỏi dựa trên tài liệu môn học.

---

# High-Level Architecture

User
↓
Frontend (Web UI)
↓
Backend API
↓
RAG Pipeline
├── Retriever
├── Vector Database
└── LLM
↓
Response with Citation

---

# Components

## Frontend

Chức năng:

- nhập câu hỏi
- hiển thị câu trả lời
- upload tài liệu

Công nghệ đề xuất:

- React / NextJS

---

## Backend API

Chức năng:

- nhận request từ frontend
- gọi RAG pipeline
- trả câu trả lời

Công nghệ:

- FastAPI

---

## RAG Pipeline

Pipeline AI xử lý câu hỏi.

Các bước:

1. nhận câu hỏi từ user
2. chuyển câu hỏi thành embedding
3. tìm đoạn tài liệu liên quan
4. gửi context vào LLM
5. sinh câu trả lời

---

## Vector Database

Chức năng:

- lưu embedding của tài liệu
- tìm kiếm similarity

Công nghệ:

- FAISS

---

## LLM

Chức năng:

- sinh câu trả lời từ context

Ví dụ:

- GPT
- Llama