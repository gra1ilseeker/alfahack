# Backend service

## Требования
- Python 3.11+
- venv

## Установка
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Запуск
```bash
uvicorn app.main:app --reload
```
По умолчанию используется SQLite `data.db`. Настройте переменные среды:
- `DATABASE_URL` — строка подключения (по умолчанию sqlite:///./data.db)
- `ML_SERVICE_URL` — endpoint ML (по умолчанию http://localhost:8001/score)
- `DEBUG` — true/false

## Основные эндпоинты
- `GET /health`
- `POST /auth/login`, `POST /auth/register`
- `POST /profile/`, `GET /profile/{id}`
- `POST /metrics/{profile_id}`
- `GET /dashboard/{profile_id}`
- `GET /products/`, `POST /products/`
- `POST /rank/products`
- `POST /events/`

## Заметки
- Токен сейчас моковый `token-{user.id}` — заменить на JWT при доработке.
- ML-клиент возвращает заглушку 0.5 при ошибке запроса.
- Миграции не подключены (Alembic можно добавить позже).
