#!/bin/bash
# Quick verification script for backend optimizations
# Run this before pushing to production

set -e

echo "=== Backend Optimization Verification ==="
echo ""

# 1. Syntax check
echo "1️⃣  Checking Python syntax..."
python -m py_compile \
  api/routes/chat.py \
  api/lib/supabase.py \
  api/lib/async_http.py \
  api/index.py \
  src/cache.py \
  scripts/benchmark_api.py
echo "✅ Syntax OK"
echo ""

# 2. Start backend in background
echo "2️⃣  Starting backend server..."
pkill -f "uvicorn api.index:app" 2>/dev/null || true
sleep 1

# Activate conda env if exists
if [ -d "./env" ]; then
  source ./env/bin/activate 2>/dev/null || true
fi

uvicorn api.index:app --host 127.0.0.1 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for startup
echo "Waiting for backend to start..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend started"
    break
  fi
  sleep 1
  if [ $i -eq 30 ]; then
    echo "❌ Backend failed to start"
    cat /tmp/backend.log
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
  fi
done
echo ""

# 3. Health check
echo "3️⃣  Testing /api/health..."
HEALTH=$(curl -s http://127.0.0.1:8000/api/health)
if echo "$HEALTH" | grep -q "ok"; then
  echo "✅ Health check passed"
else
  echo "❌ Health check failed: $HEALTH"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi
echo ""

# 4. Cache stats endpoint
echo "4️⃣  Testing /api/perf/cache-stats..."
STATS=$(curl -s http://127.0.0.1:8000/api/perf/cache-stats)
if echo "$STATS" | grep -q "cache"; then
  echo "✅ Cache stats endpoint working"
  echo "$STATS" | python -m json.tool 2>/dev/null || echo "$STATS"
else
  echo "❌ Cache stats failed: $STATS"
  kill $BACKEND_PID 2>/dev/null || true
  exit 1
fi
echo ""

# 5. Quick load test (if benchmark script exists)
if [ -f "scripts/benchmark_api.py" ]; then
  echo "5️⃣  Running quick load test (20 concurrent, 100 requests)..."
  python scripts/benchmark_api.py \
    --url http://127.0.0.1:8000/api/health \
    --concurrency 20 \
    --requests 100 \
    --timeout 10
  echo ""
fi

# Cleanup
echo "🧹 Cleaning up..."
kill $BACKEND_PID 2>/dev/null || true
sleep 1

echo ""
echo "=== ✅ All Checks Passed ==="
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff HEAD~1"
echo "  2. Push to remote: git push origin main"
echo "  3. Monitor Vercel deployment logs"
echo "  4. Check production metrics after deploy"
echo ""
