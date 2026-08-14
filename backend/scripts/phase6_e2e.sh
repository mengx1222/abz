#!/bin/bash
# phase6_e2e.sh — Start backend, run UAT, stop backend
set -e
cd /home/z/my-project/backend
source .venv/bin/activate
export AZB_DEMO_MODE=true
export AZB_DEBUG=false
export AZB_BASE_URL=http://localhost:8999

echo "=== Starting backend on :8999 ==="
python -m uvicorn app.main:app --host 127.0.0.1 --port 8999 &>/tmp/azb_backend.log &
BACKEND_PID=$!
echo "PID=$BACKEND_PID"

# Wait for readiness
for i in $(seq 1 20); do
    if curl -sf http://localhost:8999/api/v1/health >/dev/null 2>&1; then
        echo "Backend ready after ${i}x0.5s"
        break
    fi
    sleep 0.5
done

# Verify health
echo "=== Health Check ==="
curl -s http://localhost:8999/api/v1/health | python3 -m json.tool
echo ""

echo "=== Ready Check ==="
curl -s http://localhost:8999/api/v1/ready | python3 -m json.tool
echo ""

echo "=== Health Detail ==="
curl -s http://localhost:8999/api/v1/health/detail | python3 -m json.tool
echo ""

echo "=== Running UAT Smoke Test ==="
python scripts/phase6_uat_smoke.py
UAT_EXIT=$?

echo ""
echo "=== Backend Log (last 30 lines) ==="
tail -30 /tmp/azb_backend.log

# Cleanup
kill $BACKEND_PID 2>/dev/null
echo "=== Done (UAT exit=$UAT_EXIT) ==="
exit $UAT_EXIT
