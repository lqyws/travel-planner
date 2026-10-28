"""历史方案查询接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import TravelPlan

router = APIRouter()


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(TravelPlan).order_by(TravelPlan.id.desc()).limit(50).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "destination": p.destination,
            "days": p.days,
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for p in plans
    ]


@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(TravelPlan).filter(TravelPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")
    return {
        "id": plan.id,
        "title": plan.title,
        "destination": plan.destination,
        "days": plan.days,
        "content": plan.content,
        "created_at": plan.created_at.strftime("%Y-%m-%d %H:%M"),
    }
