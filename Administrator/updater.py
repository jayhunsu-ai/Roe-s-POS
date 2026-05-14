import sys, os, subprocess, threading, requests
from packaging.version import Version
from config import GITHUB_TOKEN

CURRENT_VERSION = "1.0.0"
GITHUB_API = "https://api.github.com/repos/jayhunsu-ai/Roe-s-POS/releases/latest"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

def check_for_update():
    try:
        r = requests.get(GITHUB_API, headers=HEADERS, timeout=5)
        r.raise_for_status()
        data = r.json()
        latest = data["tag_name"].lstrip("v")

        if Version(latest) <= Version(CURRENT_VERSION):
            return

        asset = next((a for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not asset:
            return

        exe_path = sys.executable
        new_path = exe_path + ".new"

        dl = requests.get(
            asset["url"],
            headers={**HEADERS, "Accept": "application/octet-stream"},
            stream=True,
            timeout=30
        )
        with open(new_path, "wb") as f:
            for chunk in dl.iter_content(8192):
                f.write(chunk)

        bat = os.path.join(os.path.dirname(exe_path), "_update.bat")
        with open(bat, "w") as f:
            f.write(f"""@echo off
timeout /t 2 /nobreak >nul
move /y "{new_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
""")
        subprocess.Popen(bat, shell=True)
        sys.exit(0)

    except Exception as e:
        print(f"Update check failed: {e}")
