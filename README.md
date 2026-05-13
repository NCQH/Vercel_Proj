# AI Teaching Assistant

> Hệ thống chatbot AI hỗ trợ sinh viên học tập với RAG (Retrieval-Augmented Generation), quản lý lớp học, và theo dõi lộ trình học tập.

[![Next.js](https://img.shields.io/badge/Next.js-16.2-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-blue)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📋 Mục Lục

- [Tổng Quan](#-tổng-quan)
- [Tính Năng](#-tính-năng)
- [Kiến Trúc](#-kiến-trúc)
- [Yêu Cầu Hệ Thống](#-yêu-cầu-hệ-thống)
- [Cài Đặt](#-cài-đặt)
- [Cấu Hình](#-cấu-hình)
- [Chạy Ứng Dụng](#-chạy-ứng-dụng)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## 🎯 Tổng Quan

AI Teaching Assistant là một nền tảng học tập thông minh giúp:

- **Sinh viên:** Hỏi đáp về tài liệu học tập, nhận câu trả lời với trích dẫn nguồn, theo dõi lộ trình học
- **Giảng viên:** Quản lý lớp học, upload tài liệu, duyệt sinh viên, giảm câu hỏi lặp lại

### Công Nghệ Sử Dụng

**Frontend:**
- Next.js 16 (App Router) + React 18
- TypeScript + TailwindCSS
- NextAuth (Authentication)

**Backend:**
- FastAPI (Python)
- LangChain + LangGraph (Multi-agent AI)
- ChromaDB (Vector database)
- Supabase (PostgreSQL + Storage)

**AI Models:**
- OpenAI GPT-4o / GPT-4o-mini
- Anthropic Claude Sonnet 4
- RAG với hybrid search (semantic + keyword)

---

## ✨ Tính Năng

### Cho Sinh Viên
- ✅ **AI Chatbot:** Hỏi đáp về tài liệu học tập với trích dẫn nguồn
- ✅ **Quản lý tài liệu:** Upload và quản lý tài liệu cá nhân
- ✅ **Tham gia lớp học:** Join lớp bằng class code, truy cập tài liệu lớp
- ✅ **Lộ trình học tập:** Theo dõi roadmap và tiến độ học tập
- ✅ **Memory system:** AI nhớ context và preferences của bạn

### Cho Giảng Viên
- ✅ **Quản lý lớp học:** Tạo lớp, generate class code, quản lý thông tin
- ✅ **Quản lý thành viên:** Duyệt/từ chối yêu cầu tham gia, xem danh sách sinh viên
- ✅ **Upload tài liệu:** Upload tài liệu lớp (PDF, DOCX, TXT, MD)
- ✅ **Dashboard:** Xem thống kê và quản lý tất cả lớp học

### Tính Năng Kỹ Thuật
- ✅ **RAG Pipeline:** Retrieval-Augmented Generation với ChromaDB
- ✅ **Multi-agent System:** Router → Retrieval/Tutor agents
- ✅ **Caching Layer:** TTL cache với thread-safe, giảm latency
- ✅ **Connection Pooling:** Optimize database connections
- ✅ **Async/Await:** Non-blocking I/O cho performance tốt

---

## 🏗️ Kiến Trúc

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  Next.js 16 + React + TypeScript + TailwindCSS              │
│  (Student Dashboard | Lecturer Dashboard | Chat Interface)   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────┐
│                      Backend API                             │
│  FastAPI + Uvicorn (Python)                                 │
│  ├─ /api/chat        - Chat & RAG                           │
│  ├─ /api/classes     - Class management                     │
│  ├─ /api/uploads     - File uploads                         │
│  └─ /api/roadmap     - Learning path                        │
└────────┬──────────────┬──────────────┬──────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌────────────┐  ┌──────────────┐  ┌──────────────┐
│  Supabase  │  │  ChromaDB    │  │  OpenAI/     │
│  (DB +     │  │  (Vector     │  │  Anthropic   │
│  Storage)  │  │  Store)      │  │  (LLM)       │
└────────────┘  └──────────────┘  └──────────────┘
```

### Data Flow - Chat Request

```
User Question
    ↓
Router Agent (classify intent)
    ↓
┌───────────────┬──────────────┐
│               │              │
▼               ▼              ▼
Retrieval    Tutor Agent    General
Agent        (teaching)     Response
│
├─ Fetch user's allowed sources
├─ Query ChromaDB (semantic search)
├─ Rank results (BM25 + semantic)
└─ Return context + citations
    ↓
LLM generates answer with sources
    ↓
Response to user
```

---

## 💻 Yêu Cầu Hệ Thống

### Prerequisites

- **Node.js:** >= 18.0.0
- **Python:** >= 3.11
- **Conda/Miniconda:** (recommended)
- **Supabase Account:** [supabase.com](https://supabase.com)
- **OpenAI API Key:** [platform.openai.com](https://platform.openai.com)
- **Anthropic API Key:** [console.anthropic.com](https://console.anthropic.com) (optional)

### Recommended System
- **RAM:** >= 8GB
- **Storage:** >= 5GB free space
- **OS:** Linux, macOS, or Windows (WSL2)

---

## 🚀 Cài Đặt

### 1. Clone Repository

```bash
git clone <repository-url>
cd A20-App-013_copy
```

### 2. Setup Python Environment

**Option A: Conda (Recommended)**
```bash
conda create -p ./env python=3.11 -y
conda activate ./env
pip install -r requirements.txt
```

**Option B: venv**
```bash
python3.11 -m venv env
source env/bin/activate  # Linux/Mac
# env\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Setup Node.js Dependencies

```bash
npm install
```

### 4. Setup Supabase

#### 4.1. Tạo Project trên Supabase
1. Đăng nhập [supabase.com](https://supabase.com)
2. Tạo project mới
3. Copy `URL` và `service_role key`

#### 4.2. Chạy Database Schema
1. Vào **SQL Editor** trong Supabase Dashboard
2. Copy nội dung từ `docs/database_schema.sql`
3. Paste và **Run**
4. Chạy tiếp `docs/supabase_class_schema.sql`
5. Chạy tiếp `docs/auto_update_timestamps.sql`

#### 4.3. Setup Storage Buckets
```bash
# Option 1: Python script
python scripts/setup_buckets.py

# Option 2: Manual (xem docs/STORAGE_SETUP.md)
```

Sau đó chạy RLS policies từ `docs/supabase_storage_setup.sql` trong SQL Editor.

---

## ⚙️ Cấu Hình

### 1. Environment Variables

Copy file mẫu:
```bash
cp .env.example .env
```

Điền các giá trị:

```bash
# AI Provider API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Default model
DEFAULT_MODEL=claude-sonnet-4-20250514
# DEFAULT_MODEL=gpt-4o

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_ANON_KEY=eyJhbGc...

# NextAuth
NEXTAUTH_SECRET=your-secret-here  # Generate: openssl rand -base64 32
NEXTAUTH_URL=http://localhost:3000

# Chat runtime
CHAT_RUN_AGENT_TIMEOUT_SECONDS=35

# Logging
LOG_LEVEL=INFO
```

### 2. Generate NextAuth Secret

```bash
openssl rand -base64 32
```

Copy output vào `NEXTAUTH_SECRET` trong `.env`

---

## 🏃 Chạy Ứng Dụng

### Development Mode

**Terminal 1 - Backend:**
```bash
conda activate ./env
npm run dev:backend
```

Backend sẽ chạy tại: `http://localhost:8000`

**Terminal 2 - Frontend:**
```bash
npm run dev
```

Frontend sẽ chạy tại: `http://localhost:3000`

### Production Mode

```bash
# Build frontend
npm run build

# Start production servers
npm run start              # Frontend
npm run start:backend      # Backend (with workers)
```

### Verify Installation

```bash
# Check backend health
curl http://localhost:8000/api/health

# Check cache stats
curl http://localhost:8000/api/perf/cache-stats
```

---

## 🌐 Deployment

### Deploy to Vercel

#### 1. Install Vercel CLI
```bash
npm i -g vercel
```

#### 2. Login
```bash
vercel login
```

#### 3. Deploy
```bash
vercel --prod
```

#### 4. Configure Environment Variables
Vào Vercel Dashboard → Settings → Environment Variables, thêm tất cả biến từ `.env`

#### 5. Verify Deployment
```bash
curl https://your-domain.vercel.app/api/health
```

### Important Notes

- **Python Runtime:** Vercel tự động detect `api/index.py` và build Python backend
- **ChromaDB:** Sẽ tạo mới mỗi lần deploy (ephemeral). Consider external vector DB cho production
- **File Storage:** Dùng Supabase Storage, không lưu local
- **Environment:** Set `NODE_ENV=production` và `NEXTAUTH_URL` đúng domain

---

## 📚 API Documentation

### Base URL
- **Local:** `http://localhost:8000`
- **Production:** `https://your-domain.vercel.app`

### Endpoints

#### Health Check
```bash
GET /api/health
```

#### Chat
```bash
POST /api/chat/stream
Content-Type: application/json

{
  "user_id": "user@example.com",
  "message": "Explain transformers",
  "session_id": "web_session"
}
```

#### Classes
```bash
# List classes
GET /api/classes?user_id=user@example.com&role=student

# Create class (lecturer)
POST /api/classes
Content-Type: multipart/form-data

user_id=lecturer@example.com
name=Machine Learning 101
description=Introduction to ML

# Join class (student)
POST /api/classes/join
Content-Type: multipart/form-data

user_id=student@example.com
code=ABC12345
```

#### File Upload
```bash
POST /api/classes/files/upload
Content-Type: multipart/form-data

file=@document.pdf
user_id=lecturer@example.com
class_id=class-uuid
```

**Full API Reference:** See `docs/API_QUICK_REFERENCE.md`

---

## 🔧 Troubleshooting

### Backend không start

**Lỗi:** `ModuleNotFoundError`
```bash
# Activate environment
conda activate ./env

# Reinstall dependencies
pip install -r requirements.txt
```

**Lỗi:** `Port 8000 already in use`
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn api.index:app --port 8001
```

### Frontend không kết nối backend

**Check:**
1. Backend có đang chạy? `curl http://localhost:8000/api/health`
2. CORS settings trong `api/index.py`
3. Environment variables đúng chưa?

### ChromaDB errors

**Lỗi:** `Collection not found`
```bash
# Run backfill script
python scripts/backfill_class_files.py

# Verify
python scripts/check_chromadb_status.py
```

### Supabase connection errors

**Check:**
1. `SUPABASE_URL` và `SUPABASE_SERVICE_ROLE_KEY` đúng chưa?
2. Database schema đã chạy chưa?
3. RLS policies đã setup chưa?

### Authentication issues

**Lỗi:** `NEXTAUTH_SECRET` not set
```bash
# Generate new secret
openssl rand -base64 32

# Add to .env
NEXTAUTH_SECRET=<generated-secret>
```

---

## 🧪 Testing

### Run Tests
```bash
# Backend tests (when available)
pytest tests/ -v

# Frontend tests (when available)
npm test
```

### Load Testing
```bash
python scripts/benchmark_api.py \
  --url http://localhost:8000/api/health \
  --concurrency 20 \
  --requests 200
```

---

## 📖 Documentation

- **Setup Guide:** `docs/SETUP.md`
- **API Reference:** `docs/API_QUICK_REFERENCE.md`
- **Database Schema:** `docs/database_schema.sql`
- **Architecture:** `docs/system_architecture.md`
- **PRD:** `docs/PRD.md`
- **Optimization Guide:** `docs/BACKEND_OPTIMIZATION_GUIDE.md`

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

- **Developer:** [Your Name]
- **Instructor:** [Instructor Name]
- **Institution:** [University Name]

---

## 🙏 Acknowledgments

- LangChain & LangGraph for AI orchestration
- Supabase for backend infrastructure
- Vercel for hosting
- OpenAI & Anthropic for LLM APIs

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Email:** your-email@example.com
- **Documentation:** [Wiki](https://github.com/your-repo/wiki)

---

**Built with ❤️ for education**
