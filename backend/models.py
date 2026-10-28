"""数据表模型"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class TravelPlan(Base):
    """旅行方案"""

    __tablename__ = "travel_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True)
    title = Column(String(255))
    destination = Column(String(255))
    days = Column(Integer, default=0)
    content = Column(Text)  # Markdown 完整方案
    created_at = Column(DateTime, default=datetime.now)


class ChatMessage(Base):
    """对话消息"""

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True)
    role = Column(String(16))  # user / assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class CityImage(Base):
    """城市景点图片库 —— 支撑城市攻略画廊展示"""

    __tablename__ = "city_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(128), index=True, comment="所属城市,如 杭州")
    spot = Column(String(255), comment="景点或地标名称,如 西湖")
    filename = Column(String(255), comment="前端 public/scenery 下的文件名,如 西湖.jpg")
    category = Column(String(32), default="景点", comment="分类:景点/美食/地标/民俗")
    description = Column(Text, comment="配图说明,用于攻略展示")
    sort = Column(Integer, default=0, comment="同城市内排序,值小在前")
    created_at = Column(DateTime, default=datetime.now)
