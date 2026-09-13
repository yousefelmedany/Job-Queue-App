import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def database_url():
    if url := os.getenv("DATABASE_URL"):
        return url
    password_file = os.getenv("DB_PASSWORD_FILE")
    if not password_file:
        raise RuntimeError("Set DATABASE_URL or DB_PASSWORD_FILE")
    password = Path(password_file).read_text(encoding="utf-8").strip()
    if not password:
        raise RuntimeError("Database password file is empty")
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("DB_USER", "queue"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "queue"),
    )


DATABASE_URL = database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
