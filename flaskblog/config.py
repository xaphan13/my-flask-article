import os
from pathlib import Path

from dotenv import load_dotenv

env_path: Path = Path(__file__).resolve().parent.parent / "local.env"
load_dotenv(env_path)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # настройки для базы данных
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URI")
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # logger settings
    LOG_DIR = os.environ.get("LOG_DIR")
    LOG_FILE = os.environ.get("LOG_FILE")
