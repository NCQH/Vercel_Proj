#!/bin/bash

# ============================================
# AI Teaching Assistant - Critical Fixes Script
# ============================================
# This script fixes the 4 most critical issues
# Run: bash scripts/fix_critical_issues.sh
# ============================================

set -e  # Exit on error

echo "🔧 AI Teaching Assistant - Critical Fixes"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# Task 1: Fix Exposed API Key
# ============================================
echo -e "${YELLOW}[1/4] Fixing exposed API key...${NC}"

if grep -q "AI_LOG_API_KEY=lMfm8NPzHVHlOtYx2kOQ7c9PTxJOB0E3DJbD_UBlsFw" .env.example 2>/dev/null; then
    echo "  ⚠️  Found exposed API key in .env.example"
    
    # Backup original
    cp .env.example .env.example.backup
    echo "  📦 Backed up to .env.example.backup"
    
    # Remove exposed key
    sed -i.tmp '/AI_LOG_API_KEY=lMfm8NPzHVHlOtYx2kOQ7c9PTxJOB0E3DJbD_UBlsFw/d' .env.example
    rm -f .env.example.tmp
    
    # Add placeholder
    if ! grep -q "AI_LOG_API_KEY=" .env.example; then
        echo "AI_LOG_API_KEY=your_api_key_here" >> .env.example
    fi
    
    echo -e "  ${GREEN}✓ Removed exposed API key${NC}"
    echo "  ⚠️  ACTION REQUIRED: Rotate this API key at https://ai-logs.note.transformerlabs.ai"
else
    echo -e "  ${GREEN}✓ No exposed API key found${NC}"
fi

echo ""

# ============================================
# Task 2: Create Complete .env.example
# ============================================
echo -e "${YELLOW}[2/4] Creating complete .env.example...${NC}"

cat > .env.example.complete << 'EOF'
# ============================================
# AI TEACHING ASSISTANT - ENVIRONMENT VARIABLES
# ============================================

# -----------------
# AI Providers
# -----------------
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=gpt-4o-mini

# -----------------
# Database (Supabase)
# -----------------
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_ANON_KEY=eyJhbGc...

# -----------------
# Authentication (NextAuth)
# -----------------
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=generate_with_openssl_rand_base64_32

# -----------------
# Vector Store (ChromaDB)
# -----------------
CHROMA_DB_DIR=chroma_db
CHROMA_TENANT=default_tenant
CHROMA_DATABASE=default_database

# -----------------
# Storage
# -----------------
STORAGE_BACKEND=supabase
UPLOADS_BUCKET=user-uploads
CLASS_FILES_BUCKET=class-files

# -----------------
# Logging & Monitoring
# -----------------
LOG_LEVEL=INFO
AI_LOG_SERVER=https://ai-logs.note.transformerlabs.ai/api/ingest
AI_LOG_API_KEY=your_api_key_here
AI_LOG_DIR=.ai-log

# -----------------
# Memory System
# -----------------
MEMORY_CONTEXT_TURNS=8
MEMORY_FACT_TOP_K=5
MEMORY_SEMANTIC_TOP_K=5
MEMORY_LONG_TERM_TOP_K=4
MEMORY_EPISODIC_TOP_K=3

# -----------------
# RAG Configuration
# -----------------
CHUNK_SIZE=400
CHUNK_OVERLAP=80
TOP_K_SEARCH=10
TOP_K_SELECT=3
EOF

echo -e "  ${GREEN}✓ Created .env.example.complete${NC}"
echo "  📝 Review and merge into .env.example"
echo ""

# ============================================
# Task 3: Create Database Schema
# ============================================
echo -e "${YELLOW}[3/4] Creating database schema documentation...${NC}"

mkdir -p docs

cat > docs/database_schema.sql << 'EOF'
-- ============================================
-- AI TEACHING ASSISTANT - DATABASE SCHEMA
-- ============================================
-- Platform: Supabase (PostgreSQL 15+)
-- Created: 2026-05-12

-- -----------------
-- Users Table
-- -----------------
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT CHECK (role IN ('student', 'lecturer', 'admin')) DEFAULT 'student',
    class_name TEXT,
    onboarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- -----------------
-- Classes Table
-- -----------------
CREATE TABLE IF NOT EXISTS classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lecturer_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_classes_lecturer ON classes(lecturer_id);
CREATE INDEX idx_classes_code ON classes(code);
CREATE INDEX idx_classes_active ON classes(is_active);

-- -----------------
-- Class Members Table
-- -----------------
CREATE TABLE IF NOT EXISTS class_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT CHECK (status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    UNIQUE(class_id, student_id)
);

CREATE INDEX idx_class_members_class ON class_members(class_id);
CREATE INDEX idx_class_members_student ON class_members(student_id);
CREATE INDEX idx_class_members_status ON class_members(status);

-- -----------------
-- Class Files Table
-- -----------------
CREATE TABLE IF NOT EXISTS class_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    file_id TEXT UNIQUE NOT NULL,
    uploader_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_class_files_class ON class_files(class_id);
CREATE INDEX idx_class_files_uploader ON class_files(uploader_id);
CREATE INDEX idx_class_files_file_id ON class_files(file_id);

-- -----------------
-- Personal Uploads Table
-- -----------------
CREATE TABLE IF NOT EXISTS uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_uploads_user ON uploads(user_id);
CREATE INDEX idx_uploads_file_id ON uploads(file_id);

-- -----------------
-- Chat Messages Table
-- -----------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    role TEXT CHECK (role IN ('user', 'assistant', 'system')) NOT NULL,
    content TEXT NOT NULL,
    citations TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_user_session ON chat_messages(user_id, session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at DESC);

-- -----------------
-- Roadmap Items Table
-- -----------------
CREATE TABLE IF NOT EXISTS roadmap_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT CHECK (status IN ('todo', 'doing', 'done')) DEFAULT 'todo',
    order_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_roadmap_user ON roadmap_items(user_id);
CREATE INDEX idx_roadmap_status ON roadmap_items(status);

-- -----------------
-- Row Level Security (RLS)
-- -----------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE class_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE roadmap_items ENABLE ROW LEVEL SECURITY;

-- Note: Add RLS policies based on your authentication setup
EOF

echo -e "  ${GREEN}✓ Created docs/database_schema.sql${NC}"
echo ""

# ============================================
# Task 4: Create Setup Instructions
# ============================================
echo -e "${YELLOW}[4/4] Creating setup instructions...${NC}"

cat > docs/SETUP.md << 'EOF'
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
EOF

echo -e "  ${GREEN}✓ Created docs/SETUP.md${NC}"
echo ""

# ============================================
# Summary
# ============================================
echo "=========================================="
echo -e "${GREEN}✅ Critical fixes completed!${NC}"
echo ""
echo "📋 What was done:"
echo "  1. ✓ Removed exposed API key from .env.example"
echo "  2. ✓ Created complete .env.example.complete"
echo "  3. ✓ Created database schema (docs/database_schema.sql)"
echo "  4. ✓ Created setup instructions (docs/SETUP.md)"
echo ""
echo "⚠️  ACTION REQUIRED:"
echo "  1. Rotate exposed API key at https://ai-logs.note.transformerlabs.ai"
echo "  2. Review and merge .env.example.complete into .env.example"
echo "  3. Run database schema in Supabase SQL Editor"
echo "  4. Update your local .env with all required variables"
echo ""
echo "📚 Next steps:"
echo "  - Read: docs/SETUP.md"
echo "  - Review: executive_summary.md"
echo "  - Follow: action_plan.md"
echo ""
echo "🚀 Ready to continue? Run: npm run dev"
echo "=========================================="
