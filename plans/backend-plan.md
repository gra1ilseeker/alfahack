# Backend MVP Plan

## 1. Требования
- Предоставить API для онбординга профиля, загрузки CSV и сохранения финансовых метрик.
- Рассчитывать показатели для дашборда (выручка, расходы, чистый поток, индекс устойчивости).
- Делать запросы к ML-сервису логистической регрессии для ранжирования продуктов.
- Управлять каталогом продуктов и хранить результаты ранжирования.
- Обеспечить логирование действий и базовую аутентификацию.

## 2. Модули и эндпоинты
1. **Auth & Session**: POST /auth/login, middleware для токена.
2. **Profile Module**:
   - GET /profile/{id}
   - POST /profile (создание с базовой информацией)
   - POST /profile/{id}/metrics (загрузка CSV или JSON метрик)
3. **Dashboard Module**:
   - GET /dashboard/{id} → агрегированные метрики + подсказки.
4. **Product Catalog**:
   - GET /products
   - POST /products (админ, при необходимости)
5. **Ranking Module**:
   - POST /rank-products → обращения к ML-сервису, сохранение результатов.
6. **Logs & Analytics**:
   - POST /events (UI действия)

## 3. Схема данных (SQLite/SQLAlchemy)
- tables:
  - users: id, email, hash, role.
  - profiles: id, user_id, industry, revenue_band, employees, goals, created_at.
  - metrics: id, profile_id, period, revenue, expenses, cash_flow, online_share.
  - dashboard_snapshots: id, profile_id, snapshot_json.
  - products: id, name, type, rate, min_limit, max_limit, requirements_json.
  - rankings: id, profile_id, generated_at, result_json.
  - events: id, profile_id, event_type, payload, created_at.

## 4. Взаимодействие с ML и аналитикой
- Backend подготавливает фичи (agg metrics + goals) и отправляет POST /score к ML-сервису (внутренний endpoint).
- ML отвечает списком продуктов с вероятностями/скор.
- Backend обогащает ответ условиями продукта и хранит в таблице rankings.
- Аналитический модуль (internal Python) рассчитывает индекс устойчивости (формула: normalized cash_flow + margin + stability score).

## 5. План реализации
1. Настроить FastAPI проект, конфигурацию, базу данных и миграции (Alembic).
2. Реализовать модели данных и репозитории.
3. Покрыть Auth/Profile/Products CRUD.
4. Реализовать загрузку CSV, парсинг и сохранение metrics.
5. Реализовать расчёты дашборда и endpoint /dashboard/{id}.
6. Подключить ML-сервис: клиент и endpoint /rank-products.
7. Добавить логирование событий и подготовить фикстуры данных.
8. Подготовить OpenAPI/Swagger, минимальные тесты и инструкции запуска.

## 6. Риски
- ML-сервис может быть не готов → предусмотреть моковый ответ.
- Обработка CSV ошибок → валидация и отчёт об ошибках.
- Производительность при больших объёмах → пока MVP, но предусмотреть батчи.

## 7. Следующие шаги
- Утвердить backend план.
- Перейти в режим Code для реализации (поднятие FastAPI, схемы, модели).
