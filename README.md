# Stopcard Backend

[![CI](https://github.com/karl4th/stop-card-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/karl4th/stop-card-backend/actions/workflows/ci.yml)

Backend сервиса производственной безопасности **StopКарта** для `stop-card.kz`.
Приложение принимает сообщения о небезопасной работе, проверяет Telegram Mini App
авторизацию, хранит фотографии в MinIO и предоставляет администраторам управление
обращениями и справочниками.

## Технологии

- Python 3.12+, FastAPI, Pydantic 2
- PostgreSQL 17, SQLAlchemy 2 (async), Alembic
- MinIO с приватными объектами и временными ссылками
- JWT для администраторов, Argon2 для паролей
- Docker Compose, Ruff, Pytest, GitHub Actions

Redis намеренно не добавлен: текущей нагрузке и синхронному сценарию создания
стопкарты он не нужен. Его следует подключать при появлении фоновых задач,
распределённого rate limiting или измеримой потребности в кэше.

## Архитектура

Проект реализован как модульный монолит:

```text
app/
├── api/          # HTTP-маршруты и зависимости
├── core/         # конфигурация, безопасность, общие ошибки
├── db/           # engine и сессии PostgreSQL
├── models/       # SQLAlchemy-модели
├── schemas/      # входные и выходные DTO
└── services/     # Telegram, MinIO, бизнес-операции и аудит
```

Бизнес-справочники находятся в PostgreSQL. Их подписи, порядок и активность
редактируются через административный API. Стабильные `code` не изменяются, потому
что являются частью контракта с frontend и сохраняются в исторических записях.
Секреты и адреса инфраструктуры задаются только через переменные окружения.

## Запуск

Требуются Docker и Docker Compose.

```bash
cp .env.example .env
# Заполнить TELEGRAM_BOT_TOKEN, JWT_SECRET и безопасные MINIO_* credentials
docker compose up -d postgres minio
docker compose run --rm api alembic upgrade head
docker compose up -d api
docker compose run --rm api stopcard create-admin admin
```

API доступен на `http://localhost:8000`. В development OpenAPI находится на
`/docs`. Миграции запускаются отдельной командой, чтобы несколько экземпляров API
не пытались изменять схему одновременно.

Локальный запуск без Docker для приложения:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Production-развёртывание для `api.stop-card.kz`, Nginx, TLS и обновление
сертификатов описаны в [`deploy/README.md`](deploy/README.md). Используйте
`docker-compose.prod.yml`; локальный `docker-compose.yml` не предназначен для VPS.

## API

Основной контракт описан в [`backend.md`](backend.md).

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/stopcards` | Создание стопкарты (`multipart/form-data`) |
| `GET` | `/api/reference/{type}` | Активные `reason`, `circumstance`, `hazard` |
| `POST` | `/api/admin/auth/login` | Получение admin JWT |
| `GET` | `/api/admin/auth/me` | Текущий администратор |
| `GET/POST/PATCH` | `/api/admin/catalogs/...` | Управление справочниками |
| `GET/PATCH` | `/api/admin/statuses/...` | Настройка статусов |
| `GET` | `/api/admin/stopcards` | Список с пагинацией и фильтром статуса |
| `GET` | `/api/admin/stopcards/{id}` | Карточка обращения |
| `GET` | `/api/admin/stopcards/{id}/photo-url` | Временная ссылка на фотографию |
| `PATCH` | `/api/admin/stopcards/{id}/status` | Изменение статуса с аудитом |
| `GET` | `/health/live`, `/health/ready` | Проверки контейнера и PostgreSQL |

Все административные endpoint'ы доступны только аутентифицированным администраторам.

## Безопасность

- Telegram `initData` проверяется HMAC-SHA256 по алгоритму Mini Apps, включая
  `auth_date`; `initDataUnsafe` не используется.
- MIME фотографии сверяется с фактической сигнатурой, размер ограничен, имя
  объекта генерируется backend.
- Bucket остаётся приватным. Клиент получает presigned URL с ограниченным сроком.
- Внутренний `MINIO_ENDPOINT` отделён от доступного клиенту
  `MINIO_PRESIGN_ENDPOINT`, поэтому подпись содержит корректный внешний host.
- Пароли администраторов хешируются Argon2, изменения справочников и статусов
  записываются в `audit_logs`.
- Production-конфигурация отклоняет пустой Telegram token, короткий JWT secret и
  стандартные MinIO credentials.

Перед публичным запуском TLS и security headers должны завершаться на reverse
proxy, PostgreSQL и MinIO не должны публиковаться наружу, а backup/restore следует
регулярно проверять.

## Проверки

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run alembic upgrade head --sql > /tmp/schema.sql
```
