"""对话与行程生成接口"""
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from graph import run_planner, stream_planner
from models import ChatMessage, TravelPlan
from redis_client import append_message, get_history

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="未配置环境变量 OPENAI_API_KEY")

    history = get_history(req.session_id)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])

    try:
        state = run_planner(req.message, history_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"规划生成失败:{e}")

    reply = state["final_plan"]

    # Redis 缓存会话上下文
    append_message(req.session_id, "user", req.message)
    append_message(req.session_id, "assistant", reply)

    # MySQL 持久化消息与方案
    db.add(ChatMessage(session_id=req.session_id, role="user", content=req.message))
    db.add(ChatMessage(session_id=req.session_id, role="assistant", content=reply))
    plan = TravelPlan(
        session_id=req.session_id,
        title=f'{state["destination"]}{state["days"]}日游',
        destination=state["destination"],
        days=state["days"],
        content=reply,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return {
        "reply": reply,
        "plan_id": plan.id,
        "destination": state["destination"],
        "days": state["days"],
    }


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """SSE 流式对话:逐 token 推送方案,前端打字机渲染"""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="未配置环境变量 OPENAI_API_KEY")

    history = get_history(req.session_id)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])

    def event_stream():
        final_plan = None
        destination, days = "", 0
        try:
            for ev in stream_planner(req.message, history_text):
                if ev["type"] == "done":
                    final_plan = ev["plan"]
                    destination, days = ev["destination"], ev["days"]
                    continue
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            err = {"type": "error", "detail": f"规划生成失败:{e}"}
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"
            return

        if not final_plan:
            return

        # 流结束后:Redis 缓存会话 + MySQL 持久化
        append_message(req.session_id, "user", req.message)
        append_message(req.session_id, "assistant", final_plan)

        db = SessionLocal()
        try:
            db.add(ChatMessage(session_id=req.session_id, role="user", content=req.message))
            db.add(ChatMessage(session_id=req.session_id, role="assistant", content=final_plan))
            plan = TravelPlan(
                session_id=req.session_id,
                title=f"{destination}{days}日游",
                destination=destination,
                days=days,
                content=final_plan,
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            saved = {"type": "saved", "plan_id": plan.id}
            yield f"data: {json.dumps(saved, ensure_ascii=False)}\n\n"
        finally:
            db.close()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history/{session_id}")
def history(session_id: str):
    return {"messages": get_history(session_id)}
