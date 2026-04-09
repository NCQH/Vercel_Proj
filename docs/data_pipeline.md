# Data Pipeline Document

## Overview

Pipeline xử lý tài liệu để phục vụ hệ thống RAG.

---

# Pipeline Flow
PDF / Slides
↓
Text Extraction
↓
Text Chunking
↓
Embedding Generation
↓
Vector Database Storage


---

# Step 1 — Document Upload

Giảng viên upload:

- PDF
- Slides

---

# Step 2 — Text Extraction

Tài liệu được chuyển thành text.

Ví dụ:

- pdfminer
- pymupdf

---

# Step 3 — Text Chunking

Text được chia thành các đoạn nhỏ.

Ví dụ:
chunk_size = 500 tokens
overlap = 100 tokens

Mục đích:

- cải thiện retrieval accuracy

---

# Step 4 — Embedding

Text chunk được chuyển thành vector embedding.

Ví dụ:

- OpenAI embedding
- BGE embedding

---

# Step 5 — Vector Storage

Embedding được lưu vào vector database.

Ví dụ:

- FAISS

