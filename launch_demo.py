"""
Rakshak AI — One-Click Mentor Demo Console
Launches Uvicorn backend + Cloudflare Tunnel + Auto-detects URL + Auto-updates .env + Interactive Call Trigger.
Designed for high-reliability live demonstrations.
"""

import sys
import os
import re
import time
import subprocess
import threading
import urllib.request
from pathlib import Path

# Ensure UTF-8 printing on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
REPORTS_DIR = BASE_DIR / "reports"


def update_env_base_url(tunnel_url: str):
    """Updates BASE_URL in .env file with the active Cloudflare tunnel URL."""
    if not ENV_FILE.exists():
        return
    lines = []
    updated = False
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("BASE_URL="):
                lines.append(f"BASE_URL={tunnel_url}\n")
                updated = True
            else:
                lines.append(line)
    if not updated:
        lines.append(f"BASE_URL={tunnel_url}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ["BASE_URL"] = tunnel_url
    print(f"[CONFIG] .env BASE_URL updated to: {tunnel_url}")


def check_health(url: str = "http://127.0.0.1:8000/health", timeout: float = 2.0) -> bool:
    """Checks if local FastAPI backend is responsive."""
    try:
        req = urllib.request.urlopen(url, timeout=timeout)
        return req.getcode() == 200
    except Exception:
        return False


def find_cloudflared_path() -> str:
    """Locates cloudflared.exe on system."""
    common_paths = [
        "cloudflared",
        r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
        r"C:\Program Files\cloudflared\cloudflared.exe",
    ]
    for p in common_paths:
        try:
            res = subprocess.run([p, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                return p
        except Exception:
            continue
    return "cloudflared"


def main():
    print("=" * 65)
    print("      RAKSHAK AI — MENTOR DEMO CONSOLE LAUNCHER")
    print("=" * 65)
    print(f"Working Directory: {BASE_DIR}")

    # 1. Start Uvicorn Backend
    print("\n[1/3] Starting Rakshak AI backend (FastAPI + Uvicorn)...")
    uvicorn_cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
    uvicorn_proc = subprocess.Popen(
        uvicorn_cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Pipe uvicorn output in background
    def log_uvicorn():
        for line in iter(uvicorn_proc.stdout.readline, ""):
            if "INFO:" in line or "[CALL]" in line or "[SPEECH]" in line or "[PDF]" in line:
                print(f"  [SERVER] {line.strip()}")

    threading.Thread(target=log_uvicorn, daemon=True).start()

    # Wait for backend health
    print("      Waiting for server to initialize...", end="", flush=True)
    for _ in range(20):
        if check_health():
            print(" READY (Port 8000)")
            break
        time.sleep(0.5)
    else:
        print(" TIMEOUT! Backend failed to respond.")
        uvicorn_proc.terminate()
        sys.exit(1)

    # 2. Start Cloudflare Tunnel
    cloudflared_bin = find_cloudflared_path()
    print(f"\n[2/3] Starting Cloudflare Tunnel ({cloudflared_bin})...")
    cf_proc = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    tunnel_url = None
    print("      Acquiring public HTTPS tunnel...", end="", flush=True)
    t0 = time.time()
    while time.time() - t0 < 30:
        line = cf_proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if m:
            tunnel_url = m.group(0)
            print(f" CONNECTED!")
            break

    if not tunnel_url:
        print(" FAILED to acquire tunnel URL.")
        print("      Check your internet connection or run 'cloudflared tunnel' manually.")
        cf_proc.terminate()
        uvicorn_proc.terminate()
        sys.exit(1)

    # 3. Update .env with new tunnel URL
    print("\n[3/3] Syncing Twilio Webhook Configuration...")
    update_env_base_url(tunnel_url)

    # Display Ready Banner
    print("\n" + "═" * 65)
    print("  ★  RAKSHAK AI DEMO ENVIRONMENT IS FULLY ONLINE & READY  ★")
    print("═" * 65)
    print(f"  • Local Dashboard  : http://localhost:8000")
    print(f"  • Public Tunnel    : {tunnel_url}")
    print(f"  • Twilio Webhook   : {tunnel_url}/incoming-call")
    print(f"  • Server Health    : http://localhost:8000/health (200 OK)")
    print(f"  • Hash (#) Key     : ENABLED (Instant finishOnKey='#')")
    print("═" * 65)
    print("\nDEMO ACTIONS:")
    print("  [C] Trigger Demo Phone Call NOW (via call_me.py)")
    print("  [T] Run Quick Local LLM Scenario (0 telephony credits, 2s demo)")
    print("  [R] Open Reports Folder")
    print("  [Q] Exit & Shut Down")
    print("═" * 65)

    # Interactive Loop
    try:
        while True:
            cmd = input("\nEnter choice [C = Call | T = Local Test | R = Reports | Q = Quit]: ").strip().lower()
            if cmd in ("c", "call"):
                print("\nInitiating live demo call to your registered phone...")
                try:
                    from call_me import make_outbound_call
                    make_outbound_call(base_url=tunnel_url)
                except Exception as e:
                    print(f"[CALL ERROR] {e}")
            elif cmd in ("t", "test"):
                print("\nRunning offline LLM analysis demo (Banking OTP Fraud)...")
                try:
                    subprocess.run([sys.executable, "test_llm.py", "--scenario", "otp"], cwd=str(BASE_DIR))
                except Exception as e:
                    print(f"[TEST ERROR] {e}")
            elif cmd in ("r", "reports"):
                if sys.platform == "win32":
                    os.startfile(str(REPORTS_DIR))
                else:
                    print(f"Reports path: {REPORTS_DIR}")
            elif cmd in ("q", "quit", "exit"):
                print("\nShutting down demo console...")
                break
            else:
                print("Invalid command. Type C, T, R, or Q.")
    except (KeyboardInterrupt, EOFError):
        print("\nStopping servers...")
    finally:
        cf_proc.terminate()
        uvicorn_proc.terminate()
        print("Demo environment stopped. Good luck with the scoring round!")


if __name__ == "__main__":
    main()
