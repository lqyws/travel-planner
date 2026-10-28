"""FastAPI 入口"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # 支持从 .env 读取 OPENAI_API_KEY 等配置

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import models  # noqa: F401  确保表模型注册后再建表
from database import Base, engine
from routers import chat, gallery, plans

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 旅游规划平台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(plans.router, prefix="/api")
app.include_router(gallery.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 若前端已构建(npm run build),直接由 FastAPI 托管,实现单端口运行
DIST = Path(__file__).parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
