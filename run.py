"""
Launcher Script for AI Voice Technical Support Agent
Runs FastAPI server with Uvicorn on http://127.0.0.1:8000
"""
import sys
import io

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import subprocess
import shutil
import uvicorn
from backend.app.config import settings

if __name__ == "__main__":
    print("=" * 70)
    print(f">> Starting {settings.APP_NAME} (v{settings.APP_VERSION})")
    print(f">> Support Agent: {settings.AGENT_NAME} | Company: {settings.SUPPORT_COMPANY}")
    print(f">> Voice Hotline: {settings.SUPPORT_HOTLINE}")
    print(f">> Voice Interface: http://127.0.0.1:{settings.PORT}")
    print(f">> API Docs: http://127.0.0.1:{settings.PORT}/docs")
    print("=" * 70)

    # Check if ngrok is already running to prevent ERR_NGROK_334
    ngrok_bin = shutil.which("ngrok")
    if ngrok_bin:
        ngrok_url = settings.NGROK_PUBLIC_URL.replace("https://", "").replace("http://", "").strip()
        already_running = False
        try:
            import urllib.request
            with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=1) as resp:
                if resp.status == 200:
                    already_running = True
                    print(f">> Ngrok tunnel is already running and connected on https://{ngrok_url}")
        except Exception:
            already_running = False

        if not already_running:
            try:
                print(f">> Launching Ngrok Tunnel on https://{ngrok_url} ...")
                subprocess.Popen([ngrok_bin, "http", f"127.0.0.1:{settings.PORT}", f"--url={ngrok_url}"])
            except Exception as e:
                print(f">> Ngrok auto-launch note: {e}")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
