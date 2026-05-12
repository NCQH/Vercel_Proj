# Setup Instructions

## Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL (via Supabase)
- OpenAI API key

## Quick Start

### 1. Clone and Install

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
# Copy template
cp .env.example.complete .env

# Edit .env and fill in:
# - OPENAI_API_KEY
# - SUPABASE_URL
# - SUPABASE_SERVICE_ROLE_KEY
# - NEXTAUTH_SECRET (generate with: openssl rand -base64 32)
```

### 3. Database Setup

```bash
# Go to Supabase Dashboard
# SQL Editor > New Query
# Copy and run: docs/database_schema.sql
```

### 4. Run Development Servers

```bash
# Terminal 1: Frontend
npm run dev

# Terminal 2: Backend
npm run dev:backend
```

### 5. Access Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Troubleshooting

### "Missing SUPABASE_URL"
- Check .env file exists
- Verify SUPABASE_URL is set
- Restart backend server

### "ChromaDB connection error"
- First run creates chroma_db/ directory
- Check write permissions

### "OpenAI API error"
- Verify OPENAI_API_KEY is valid
- Check API quota/billing

## Next Steps

1. Review `executive_summary.md` for overview
2. Follow `action_plan.md` for production deployment
3. Read `project_audit_report.md` for detailed analysis
