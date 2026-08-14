#!/usr/bin/env python3
"""Phase 6 — Start backend + run UAT smoke test in sequence.

Usage:
    cd backend && python scripts/phase6_run_uat.py
    # or with custom timeout:
    PYTHON_UAT_TIMEOUT=120 python scripts/phase6_run_uat.py
"""
import os
import signal
import subprocess
import sys
import time

# Ensure we're in the backend directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BACKEND_DIR)

# Activate venv if available
VENV = os.path.join(BACKEND_DIR, ".venv", "bin", "python")
if os.path.exists(VENV):
    os.environ["VIRTUAL_ENV"] = os.path.join(BACKEND_DIR, ".venv")
    os.environ["PATH"] = os.path.dirname(VENV) + ":" + os.environ.get("PATH", "")
    PYTHON = VENV
else:
    PYTHON = sys.executable

PORT = 8999  # Use a non-conflicting port
BASE_URL = f"http://localhost:{PORT}"
PROC = None


def start_backend():
    """Start uvicorn in background, wait for it to be ready."""
    global PROC
    env = os.environ.copy()
    env["AZB_DEMO_MODE"] = "true"
    env["AZB_DEBUG"] = "false"

    PROC = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=BACKEND_DIR,
    )

    # Wait for readiness (up to 15s)
    import requests
    for i in range(30):
        try:
            r = requests.get(f"{BASE_URL}/api/v1/health", timeout=1)
            if r.status_code == 200:
                print(f"  Backend ready after {(i + 1) * 0.5:.1f}s")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        time.sleep(0.5)
        # Check if process died
        if PROC.poll() is not None:
            print(f"  Backend exited early with code {PROC.returncode}")
            print(f"  Output: {PROC.stdout.read().decode()[:500]}")
            return False

    print("  Backend failed to start within 15s")
    return False


def stop_backend():
    if PROC and PROC.poll() is None:
        PROC.terminate()
        try:
            PROC.wait(timeout=5)
        except subprocess.TimeoutExpired:
            PROC.kill()
            PROC.wait()
    print("  Backend stopped")


def run_uat():
    env = os.environ.copy()
    env["AZB_BASE_URL"] = BASE_URL
    result = subprocess.run(
        [PYTHON, "scripts/phase6_uat_smoke.py"],
        env=env,
        cwd=BACKEND_DIR,
        capture_output=False,
        timeout=int(os.environ.get("PYTHON_UAT_TIMEOUT", "120")),
    )
    return result.returncode


def main():
    print("=" * 60)
    print("  Phase 6 — E2E Smoke Test Runner")
    print("=" * 60)

    # Install requests if needed
    try:
        import requests  # noqa: F401
    except ImportError:
        print("  Installing requests...")
        subprocess.check_call([PYTHON, "-m", "pip", "install", "-q", "requests"])

    print(f"\n  Starting backend on {BASE_URL} ...")
    if not start_backend():
        stop_backend()
        sys.exit(1)

    try:
        print(f"\n  Running UAT smoke tests...")
        code = run_uat()
    finally:
        stop_backend()

    print("\n" + "=" * 60)
    if code == 0:
        print("  E2E RESULT: ALL PASSED")
    else:
        print(f"  E2E RESULT: FAILED (exit code {code})")
    print("=" * 60)
    sys.exit(code)


if __name__ == "__main__":
    main()
