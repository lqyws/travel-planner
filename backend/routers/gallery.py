"""城市图片画廊接口"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import CityImage

router = APIRouter()


@router.get("/gallery/{city}")
def get_city_gallery(
    city: str,
    category: Optional[str] = Query(None, description="可选分类过滤,如 景点/美食/地标"),
    db: Session = Depends(get_db),
):
    """根据城市名返回已入库的风景图列表,用于攻略展示区渲染"""
    q = db.query(CityImage).filter(CityImage.city == city)
    if category:
        q = q.filter(CityImage.category == category)
    items = q.order_by(CityImage.sort.asc(), CityImage.id.asc()).all()
    return {
        "city": city,
        "total": len(items),
        "images": [
            {
                "id": i.id,
                "spot": i.spot,
                "filename": i.filename,
                "url": f"/scenery/{i.filename}",
                "category": i.category,
                "description": i.description or "",
            }
            for i in items
        ],
    }


@router.get("/cities")
def list_cities(db: Session = Depends(get_db)):
    """列出已入库图片的所有城市,附带每城封面图(第一张)与图片总数"""
    rows = (
        db.query(CityImage)
        .order_by(CityImage.city.asc(), CityImage.sort.asc(), CityImage.id.asc())
        .all()
    )
    buckets: dict[str, dict] = {}
    for r in rows:
        if r.city not in buckets:
            buckets[r.city] = {
                "city": r.city,
                "image_count": 0,
                "cover_spot": r.spot,
                "cover_url": f"/scenery/{r.filename}",
            }
        buckets[r.city]["image_count"] += 1
    cities = sorted(buckets.values(), key=lambda x: x["city"])
    return {"cities": cities}
