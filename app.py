"""一键启动:前后端一起运行

用法:python app.py

两种模式:
1. frontend/dist 存在 -> FastAPI 单端口托管前后端(http://localhost:8000)
2. dist 不存在 -> 自动启动 Vite 开发服务器 + 后端(http://localhost:5173)
"""
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"

# 后端模块以 backend 为根目录
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")


def start_frontend_dev() -> subprocess.Popen:
    """启动 Vite 开发服务器(首次自动 npm install)"""
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if not (FRONTEND / "node_modules").exists():
        print("[前端] 首次运行,执行 npm install ...")
        subprocess.run([npm, "install"], cwd=FRONTEND, check=True)
    return subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND)


def open_browser(url: str, delay: float) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        print("[警告] 未检测到环境变量 OPENAI_API_KEY,规划接口将不可用")

    import uvicorn

    if DIST.exists():
        url = "http://localhost:8000"
        print(f"[模式] 检测到 frontend/dist,单端口运行: {url}")
        threading.Thread(target=open_browser, args=(url, 2), daemon=True).start()
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
        return

    url = "http://localhost:5173"
    print(f"[模式] 未构建前端,启动 Vite 开发服务器 + 后端: {url}")
    proc = start_frontend_dev()
    threading.Thread(target=open_browser, args=(url, 5), daemon=True).start()
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8000)
    finally:
        proc.terminate()
        print("\n[退出] 已关闭前端开发服务器")


if __name__ == "__main__":
    main()
