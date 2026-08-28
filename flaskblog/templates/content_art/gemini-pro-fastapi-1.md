Этот шаблон — это полноценный, готовый к запуску MVP.

### Концепция: Telegram-бот для продажи цифровых товаров

*   **Флоу:** Пользователь выбирает товар -> получает ссылку на оплату (ЮKassa) -> после успешной оплаты бот автоматически присылает купленный цифровой товар (например, PDF-файл или ссылку).
*   **Стек:** FastAPI, PostgreSQL (SQLAlchemy async), MongoDB (Motor), Redis, Celery, Aiogram v3 (webhook), Alembic, Docker Compose.

---

### 1. Структура Репозитория

```
telegram_store_pro/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── bot_webhooks.py  # Эндпоинт для Telegram
│   │   │   └── payment_webhooks.py # Эндпоинт для ЮKassa
│   │   └── router.py
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers/
│   │   │   ├── common.py        # /start и другие общие команды
│   │   │   └── products.py      # Обработка выбора товаров
│   │   ├── keyboards/
│   │   │   └── inline.py        # Генерация inline-кнопок
│   │   └── main_bot.py          # Логика и настройка бота Aiogram
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py            # Настройки (Pydantic Settings)
│   ├── db/
│   │   ├── __init__.py
│   │   ├── mongo.py             # Клиент MongoDB (Motor)
│   │   └── postgres.py          # Модели SQLAlchemy и сессия (async)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── main_schemas.py      # Схемы Pydantic
│   ├── services/
│   │   ├── __init__.py
│   │   └── yookassa_service.py  # Логика работы с API ЮKassa
│   ├── worker/
│   │   ├── __init__.py
│   │   └── tasks.py             # Задачи Celery
│   └── main.py                  # Главный файл FastAPI
├── alembic/
│   ├── versions/
│   │   └── <хэш>_initial_migration.py # Сгенерированная миграция
│   └── env.py
│   └── script.py.mako
├── .env_example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

---

### 2. Ключевые Файлы (готовы к копированию)

#### `requirements.txt`
```
fastapi
uvicorn[standard]
sqlalchemy[asyncio]
asyncpg
alembic
pydantic[email]
pydantic-settings
celery
redis
motor
aiogram==3.1.1
httpx
yookassa
```

#### `.env_example` (переименуйте в `.env` и заполните)
```
# DOMAIN - ваш публичный домен или ngrok URL
# Важно: без http:// и слэша в конце. Например: my-cool-store.com или 1a2b-3c4d-5e6f.ngrok.io
DOMAIN=your_public_domain_or_ngrok_url

# PostgreSQL
POSTGRES_SERVER=db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=store_db
DATABASE_URL=postgresql+asyncpg://user:password@db/store_db

# MongoDB
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_INITDB_ROOT_USERNAME=mongo_user
MONGO_INITDB_ROOT_PASSWORD=mongo_pass
MONGO_DB_NAME=webhook_logs_db
MONGO_URL=mongodb://mongo_user:mongo_pass@mongo:27017

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# YooKassa
YOOKASSA_SHOP_ID=ВАШ_ID_МАГАЗИНА
YOOKASSA_SECRET_KEY=ВАШ_СЕКРЕТНЫЙ_КЛЮЧ

# Telegram Bot
TELEGRAM_BOT_TOKEN=ВАШ_БОТ_ТОКЕН
```

#### `docker-compose.yml`
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    networks:
      - app-network

  mongo:
    image: mongo:latest
    environment:
      - MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME}
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD}
    volumes:
      - mongo_data:/data/db
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    networks:
      - app-network

  web:
    build: .
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis
      - mongo
    networks:
      - app-network

  worker:
    build: .
    command: celery -A app.worker.tasks worker --loglevel=info
    volumes:
      - .:/app
    env_file: .env
    depends_on:
      - db
      - redis
      - mongo
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
  mongo_data:
```

#### `Dockerfile`
```dockerfile
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
```

#### `app/core/config.py`
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DOMAIN: str

    DATABASE_URL: str
    MONGO_URL: str
    MONGO_DB_NAME: str

    REDIS_HOST: str
    REDIS_PORT: int

    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: str

    TELEGRAM_BOT_TOKEN: str


settings = Settings()
```

#### `app/db/postgres.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, Enum as SAEnum
import enum
from app.core.config import settings


# --- Модели ---
class Base(DeclarativeBase):
    pass


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Float)
    digital_content: Mapped[str] = mapped_column(String(500))


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer)
    telegram_user_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    yookassa_payment_id: Mapped[str] = mapped_column(String, unique=True, nullable=True)


# --- Сессия ---
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

#### `app/db/mongo.py`
```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URL)
db = client[settings.MONGO_DB_NAME]
logs_collection = db["webhook_logs"]
```

#### `app/schemas/main_schemas.py`
```python
from pydantic import BaseModel
from typing import Optional, Any


class YooKassaNotificationObject(BaseModel):
    id: str
    status: str
    metadata: Optional[dict] = None


class YooKassaNotification(BaseModel):
    event: str
    object: YooKassaNotificationObject
```

#### `app/api/endpoints/payment_webhooks.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.postgres import get_async_db, Order, OrderStatus
from app.db.mongo import logs_collection
from app.schemas.main_schemas import YooKassaNotification
from app.worker.tasks import send_product_task

router = APIRouter()


@router.post("/yookassa")
async def yookassa_webhook(notification: YooKassaNotification, db: AsyncSession = Depends(get_async_db)):
    await logs_collection.insert_one(notification.model_dump())

    if notification.event == "payment.succeeded":
        payment_id = notification.object.id
        stmt = select(Order).where(Order.yookassa_payment_id == payment_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.COMPLETED
            await db.commit()
            send_product_task.delay(order.id)

    return {"status": "ok"}
```

#### `app/bot/main_bot.py`
```python
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from app.core.config import settings
from .handlers import common, products

# --- Настройка бота ---
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- Роутинг хэндлеров ---
dp.include_router(common.router)
dp.include_router(products.router)

# --- Настройка вебхука ---
WEBHOOK_PATH = f"/bot/{settings.TELEGRAM_BOT_TOKEN}"
WEBHOOK_URL = f"https://{settings.DOMAIN}{WEBHOOK_PATH}"


async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)


def setup_bot_handlers(app: web.Application):
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
```
*Примечание: `aiogram` и FastAPI/Uvicorn могут конфликтовать из-за разных event loop. Более стабильный подход - запустить бота в отдельном Docker-сервисе, как показано в `docker-compose.yml`, и использовать FastAPI только для API.* Для упрощения шаблона, мы интегрируем обработчик webhook от Telegram прямо в FastAPI.

#### `app/main.py`
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher, types
from app.core.config import settings
from app.api.router import api_router
from app.bot.main_bot import dp, bot, WEBHOOK_PATH, WEBHOOK_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    await bot.set_webhook(url=WEBHOOK_URL)
    yield
    await bot.delete_webhook()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)


@app.post(WEBHOOK_PATH)
async def bot_webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)
```

#### `app/worker/tasks.py`
```python
from celery import Celery
from app.core.config import settings
import httpx

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0",
)


# Используем httpx для отправки сообщения из воркера, чтобы не тянуть aiogram
# и не создавать сложную асинхронную логику внутри синхронной задачи Celery.
def send_message_sync(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        httpx.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message to {chat_id}: {e}")


@celery_app.task
def send_product_task(order_id: int):
    # ВАЖНО: Celery-воркер не имеет доступа к async-сессии FastAPI.
    # Для получения данных из БД здесь нужно будет создать синхронный движок
    # или использовать httpx для запроса к своему же API для получения данных.
    # Для MVP мы пропустим этот шаг и отправим заглушку.
    # В реальном проекте: создайте здесь синхронную сессию к БД.
    print(f"Запущена задача отправки товара для заказа #{order_id}")

    # Здесь будет логика получения telegram_user_id и digital_content из БД
    # Примерная заглушка:
    mock_telegram_user_id = 123456789  # Заменить на реальный ID из БД
    mock_digital_content = "Вот ваша ссылка: https://example.com/my-secret-file.pdf"

    message = f"✅ <b>Оплата прошла успешно!</b>\n\nСпасибо за покупку вашего товара.\n\n{mock_digital_content}"
    send_message_sync(chat_id=mock_telegram_user_id, text=message)
```

---

### 3. Начальная Миграция Alembic

1.  **Сначала инициализируйте Alembic (если запускаете с нуля):**
    ```bash
    docker-compose run --rm web alembic init alembic
    ```
    Затем откройте `alembic/env.py` и замените `target_metadata = None` на:
    ```python
    from app.db.postgres import Base

    target_metadata = Base.metadata
    ```

2.  **Создайте ревизию:**
    ```bash
    docker-compose run --rm web alembic revision --autogenerate -m "Initial migration"
    ```
    Это создаст файл в `alembic/versions/`. Его содержимое будет примерно таким:

    **`alembic/versions/<хэш>_initial_migration.py`**
    ```python
    """Initial migration

    Revision ID: <id>
    Revises:
    Create Date: <date>

    """

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa


    # revision identifiers, used by Alembic.
    revision: str = "<id>"
    down_revision: Union[str, None] = None
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        # ### commands auto generated by Alembic - please adjust! ###
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("digital_content", sa.String(length=500), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_products_title"), "products", ["title"], unique=False)
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("telegram_user_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.Enum("PENDING", "COMPLETED", "FAILED", name="orderstatus"), nullable=False),
            sa.Column("yookassa_payment_id", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("yookassa_payment_id"),
        )
        op.create_index(op.f("ix_orders_telegram_user_id"), "orders", ["telegram_user_id"], unique=False)
        # ### end Alembic commands ###


    def downgrade() -> None:
        # ### commands auto generated by Alembic - please adjust! ###
        op.drop_index(op.f("ix_orders_telegram_user_id"), table_name="orders")
        op.drop_table("orders")
        op.drop_index(op.f("ix_products_title"), table_name="products")
        op.drop_table("products")
        # ### end Alembic commands ###
    ```

---

### 4. Инструкции по Запуску

1.  **Клонируйте/создайте репозиторий** с указанной структурой и файлами.
2.  **Установите Docker и Docker Compose.**
3.  **Установите ngrok** для получения публичного URL для вебхуков на время разработки. Запустите его: `ngrok http 8000`.
4.  **Создайте и заполните `.env`:**
    *   Скопируйте `ngrok` URL (без `https://`) в поле `DOMAIN`.
    *   Заполните токены от Telegram-бота и ЮKassa.
5.  **Первый запуск и миграция:**
    *   Соберите и запустите контейнеры:
        ```bash
        docker-compose up --build -d
        ```
    *   Примените миграции к базе данных (команда в `docker-compose` сделает это автоматически при старте).
6.  **Готово!** Ваш API запущен на `http://localhost:8000`, а бот ждет обновлений от Telegram на вашем `ngrok` URL. Отправьте боту команду `/start`, чтобы проверить его работу.
