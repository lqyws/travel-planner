"""MySQL 连接(自动建库建表)"""
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

MYSQL_URL = os.getenv(
    "MYSQL_URL",
    "mysql+pymysql://root:123456@localhost:3306/travel_planner?charset=utf8mb4",
)


def _ensure_database() -> None:
    """自动创建数据库(需要账号有建库权限)"""
    server_url, _, db_part = MYSQL_URL.rpartition("/")
    db_name = db_part.split("?")[0]
    tmp_engine = create_engine(server_url)
    with tmp_engine.connect() as conn:
        conn.execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARSET utf8mb4")
        )
        conn.commit()


_ensure_database()

engine = create_engine(MYSQL_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
