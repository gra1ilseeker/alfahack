# Frontend service

## Требования
- Node.js 18+
- npm

## Установка
npm install

## Запуск
npm run dev
# → http://localhost:8080

## Переменные окружения
- VITE_API_URL — URL бэкенда
- VITE_AUTH_SECRET — секрет для better-auth
- DATABASE_URL — строка подключения к БД

## Основные страницы
- / — дашборд
- /login, /register — авторизация
- /profile — профиль
- /products — каталог
- /ranking — ранжирование
- /metrics — метрики

## Стек
React 19, Vite, Tailwind, Radix UI, TanStack, better-auth, Zustand, Zod...

## NPM-скрипты
dev, build, preview, typecheck, lint, format, test, db:migrate

## Заметки
- PGlite локально (PostgreSQL не нужна)
- Серверная часть в server/
- Связь с бэкендом через OpenAPI