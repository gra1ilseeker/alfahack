#!/bin/sh
# Запуск кабинета. Адрес сервера задаётся в .env (VITE_API_URL).
cd "$(dirname "$0")"
exec npm run dev
