# AI Teaching Assistant

> Nền tảng trợ giảng AI cho sinh viên và giảng viên, hỗ trợ hỏi đáp tài liệu học tập bằng RAG, quản lý lớp học, tài liệu, thành viên và lộ trình học.

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-blue)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-18.3-61dafb)](https://react.dev/)

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng](#tính-năng)
- [Công nghệ](#công-nghệ)
- [Kiến trúc](#kiến-trúc)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
- [Cấu hình môi trường](#cấu-hình-môi-trường)
- [Chạy ứng dụng](#chạy-ứng-dụng)
- [API chính](#api-chính)
- [Kiểm tra nhanh](#kiểm-tra-nhanh)
- [Troubleshooting](#troubleshooting)

---

## Tổng quan

AI Teaching Assistant giúp:

- **Sinh viên** hỏi đáp dựa trên tài liệu học tập, nhận câu trả lời có nguồn trích dẫn, theo dõi roadmap học tập.
- **Giảng viên** tạo lớp, quản lý thành viên, upload tài liệu lớp, duyệt yêu cầu tham gia.
- **Hệ thống AI** đọc tài liệu, chunk nội dung, lưu embedding vào ChromaDB, truy xuất ngữ cảnh bằng RAG.

---

## Tính năng

### Sinh viên

- Hỏi đáp với AI chatbot theo tài liệu cá nhân và tài liệu lớp.
- Upload, xem, tải xuống và xóa tài liệu cá nhân.
- Tham gia lớp bằng mã lớp.
- Xem tài liệu lớp sau khi được duyệt.
- Theo dõi lộ trình học tập.
- Chat có memory theo session và hồ sơ người dùng.

### Giảng viên

- Tạo và quản lý lớp học.
- Sinh mã lớp để sinh viên tham gia.
- Duyệt hoặc từ chối thành viên chờ duyệt.
- Upload, xem, tải xuống và xóa tài liệu lớp.
- Xem dashboard lớp và thành viên.

### Kỹ thuật

- Next.js App Router làm frontend.
- Next.js API routes làm proxy bảo vệ backend.
- FastAPI làm backend AI/service layer.
- Supabase dùng cho PostgreSQL và Storage.
- ChromaDB dùng làm vector store.
- LangGraph orchestration cho agent pipeline.
- Internal secret bảo vệ các request từ frontend proxy sang FastAPI.

---

## Công nghệ

### Frontend

- Next.js 16
- React 18
- TypeScript
- TailwindCSS
- NextAuth

### Backend

- FastAPI
- Uvicorn
- LangChain
- LangGraph
- ChromaDB
- Supabase Python client

### AI / RAG

- OpenAI / Anthropic model provider
- Embedding + vector search
- Document ingestion cho PDF, DOCX, TXT, Markdown
- Retrieval theo nguồn được phép của user

---

## Kiến trúc

```text
Browser
  |
  | Next.js pages/components
  v
Next.js App Router
  |
  | /app/api/* proxy routes
  | inject authenticated user/session
  v
FastAPI backend (/api/index.py)
  |
  | routers: chat, uploads, classes, roadmap
  v
AI / Data layer
  |-- Supabase PostgreSQL: users, classes, memberships, metadata
  |-- Supabase Storage: uploaded files
  |-- ChromaDB: document chunks + embeddings
  |-- LangGraph: memory, guardrail, retrieval, tutor response
```

### Chat flow

```text
User message
  -> Next.js /api/chat/stream
  -> FastAPI /api/chat/stream
  -> Load memory
  -> Guardrail
  -> Retrieval from allowed sources
  -> Tutor response with citations
  -> Save memory
  -> Stream response to UI
```

---

## Cấu trúc thư mục

```text
.
├── app/                    # Next.js App Router pages + API proxy routes
│   ├── api/                # Frontend API proxy, auth, upload, chat, classes
│   ├── lecturer/           # Lecturer pages
│   ├── student/            # Student pages
│   ├── login/              # Login page
│   └── signup/             # Signup page
├── components/             # React components
│   ├── app-shell/          # Main layout
│   ├── student/            # Student chat UI
│   └── ui/                 # Shared UI components
├── lib/                    # Frontend API/session helpers
├── api/                    # FastAPI backend
│   ├── index.py            # Backend entrypoint
│   ├── routes/             # Backend routers
│   ├── lib/                # Supabase, auth, storage, ingest helpers
│   └── models/             # API schemas
├── src/                    # AI agent, RAG, memory modules
│   ├── agents/
│   ├── graph/
│   ├── memory/
│   ├── rag/
│   ├── storage/
│   ├── tools/
│   └── utils/
├── package.json
├── requirements.txt
├── render.yaml
└── vercel.json
```

---

## Yêu cầu hệ thống

- Node.js `>= 18`
- Python `>= 3.11`
- Supabase project
- OpenAI API key hoặc Anthropic API key
- Tối thiểu 8GB RAM khuyến nghị cho ingestion/vector store local

---

## Cài đặt

### 1. Cài Node dependencies

```bash
npm install
```

### 2. Tạo Python environment

Dùng `venv`:

```bash
python3.11 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Hoặc dùng Conda:

```bash
conda create -p ./env python=3.11 -y
conda activate ./env
pip install -r requirements.txt
```

---

## Cấu hình môi trường

Copy file mẫu:

```bash
cp .env.example .env
```

Các biến quan trọng:

```bash
# AI providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=claude-sonnet-4-20250514

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ANON_KEY=...

# NextAuth
NEXTAUTH_SECRET=...
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Internal proxy auth
BACKEND_INTERNAL_SECRET=...

# Backend URL used by Next.js proxy routes
BACKEND_API_URL=http://localhost:8000

# Runtime
CHAT_RUN_AGENT_TIMEOUT_SECONDS=35
LOG_LEVEL=INFO
```

Tạo `NEXTAUTH_SECRET`:

```bash
openssl rand -base64 32
```

> Lưu ý: schema Supabase cần được tạo trong Supabase SQL Editor trước khi dùng các tính năng lớp, upload và roadmap. Nếu bạn đã xóa thư mục `docs/`, hãy lấy schema từ migration/source quản lý database hiện tại của dự án hoặc backup Supabase.

---

## Chạy ứng dụng

### Terminal 1: backend

```bash
source env/bin/activate
npm run dev:backend
```

Backend chạy tại:

```text
http://localhost:8000
```

### Terminal 2: frontend

```bash
npm run dev
```

Frontend chạy tại:

```text
http://localhost:3000
```

### Production local

```bash
npm run build
npm run start
npm run start:backend
```

---

## API chính

> Frontend nên gọi Next.js API routes trong `app/api/*`. Các route này lấy session và proxy sang FastAPI với internal secret.

### Health

```http
GET /api/health
```

### Chat

```http
POST /api/chat/stream
Content-Type: application/json
```

Payload ví dụ:

```json
{
  "message": "Tóm tắt tài liệu này",
  "session_id": "web_session",
  "preferred_sources": []
}
```

### Upload cá nhân

```http
POST /api/uploads
Content-Type: multipart/form-data
```

### Lớp học

```http
GET /api/classes
POST /api/classes
POST /api/classes/join
GET /api/classes/public
GET /api/classes/pending
POST /api/classes/members/{membershipId}/approve
```

### File lớp

```http
GET /api/class-files
POST /api/class-files/upload
GET /api/class-files/download
GET /api/class-files/view
```

### Roadmap

```http
GET /api/roadmap
POST /api/roadmap/refresh
PATCH /api/roadmap/items/{itemId}
```

---

## Kiểm tra nhanh

### TypeScript

```bash
npm run typecheck
```

### Backend import/compile

```bash
python -m py_compile api/index.py api/routes/*.py api/lib/*.py src/**/*.py
```

### Health check

```bash
curl http://localhost:8000/api/health
```

### Frontend build

```bash
npm run build
```

---

## Deployment

### Vercel

- `vercel.json` cấu hình frontend deployment.
- Đặt đầy đủ biến môi trường trên Vercel Dashboard.
- `NEXTAUTH_URL` phải trỏ đúng production domain.
- `BACKEND_API_URL` phải trỏ backend đang chạy nếu tách backend riêng.

### Render / backend server

- `render.yaml` dùng cho backend deployment.
- Start command tương ứng:

```bash
npm run start:backend
```

### Lưu ý production

- Không commit `.env`.
- Supabase Storage dùng cho file thật.
- ChromaDB local có thể mất dữ liệu nếu chạy trên môi trường ephemeral.
- Với production ổn định, nên dùng persistent disk hoặc vector database managed.

---

## Troubleshooting

### Backend không start do thiếu module

```bash
source env/bin/activate
pip install -r requirements.txt
```

### Port 8000 đã được dùng

```bash
lsof -ti:8000 | xargs kill -9
```

Hoặc chạy port khác:

```bash
uvicorn api.index:app --reload --port 8001
```

### Frontend không gọi được backend

Kiểm tra:

1. Backend có chạy không:

   ```bash
   curl http://localhost:8000/api/health
   ```

2. `BACKEND_API_URL` trong `.env` đúng chưa.
3. `BACKEND_INTERNAL_SECRET` khớp giữa Next.js proxy và FastAPI.
4. `NEXTAUTH_SECRET` và `NEXTAUTH_URL` đúng chưa.

### Upload/RAG không trả nguồn

Kiểm tra:

1. File upload thành công lên Supabase Storage chưa.
2. Metadata file đã có trong Supabase table chưa.
3. Backend log có lỗi parse/chunk tài liệu không.
4. ChromaDB có quyền ghi và không bị reset giữa các lần chạy.

### Supabase lỗi kết nối

Kiểm tra:

1. `SUPABASE_URL` đúng project.
2. `SUPABASE_SERVICE_ROLE_KEY` hợp lệ.
3. Database schema/table đã tồn tại.
4. Storage bucket đã tồn tại và policy phù hợp.

---

## License

Internal/student project. Cập nhật license theo nhu cầu trước khi public repository.

---
