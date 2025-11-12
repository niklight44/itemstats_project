# ItemStats — мини‑сервис на Django для импорта и выдачи товарной статистики

## Функциональность
- Импорт из публичного CSV по HTTP/HTTPS **или** простого JSON API (также можно указать локальный путь).
- Нормализация входных данных к полям: `name, category, price, updated_at` (через **Pandas**).
- Расчёт средней цены по категории (в API — через **Pandas**; результат кэшируется в Redis).
- REST API (DRF):
  - `GET /api/items/` — фильтры `category`, `price_min`, `price_max`, пагинация.
  - `GET /api/stats/avg-price-by-category/` — агрегат, кэш.
- БД: PostgreSQL + миграции.
- Плановый импорт: Celery + Redis, запуск каждые `N` минут (env `IMPORT_INTERVAL_MINUTES`).
- Идемпотентность импорта: апсерты по (`name`, `category`) и сравнение `updated_at`.
- Инфраструктура: Docker Compose (`web`, `db`, `redis`, `worker`, `beat`).

## Быстрый старт
```bash
# 1) Клонируйте репозиторий и перейдите в директорию
docker compose build
docker compose run --rm web python manage.py migrate

# 2) (Опционально) первичный импорт из примера в репозитории
docker compose run --rm web python manage.py import_items --source items/sample_data/sample.csv

# 3) Запуск всех сервисов
docker compose up
# Backend будет на http://localhost:8000
```

## Переменные окружения (.env)
Смотри `.env.example` (он же положен как `.env` по умолчанию):
- `POSTGRES_*` — настройки БД
- `REDIS_URL` — URL Redis
- `IMPORT_INTERVAL_MINUTES` — период запуска Celery Beat
- `STATS_CACHE_TTL` — TTL кэша для статистики (секунды)
- `SOURCE_URL_CSV` / `SOURCE_URL_JSON` — URL источников (если удобно задавать из env)

## Импорт данных
- **Management command**:
```bash
docker compose run --rm web python manage.py import_items --source https://example.com/items.csv
# или локальный путь
docker compose run --rm web python manage.py import_items --source items/sample_data/sample.json
```
- **Celery задача** вручную:
```bash
docker compose run --rm worker celery -A itemstats call items.tasks.import_items_task --args='["https://example.com/items.csv"]'
```
- По расписанию Celery Beat вызывает `items.tasks.import_items_task` каждые `IMPORT_INTERVAL_MINUTES` минут.

### Идемпотентность
- Уникальный ключ (`name`, `category`).
- При повторном импорте запись обновится **только если** новое `updated_at` свежее текущего.

## Примеры запросов (curl)
```bash
# Список товаров с фильтрами и пагинацией
curl "http://localhost:8000/api/items/?category=Electronics&price_min=10&price_max=200&page=1"

# Средняя цена по категориям (кэшируется)
curl "http://localhost:8000/api/stats/avg-price-by-category/"
```

## Тесты (pytest)
```bash
docker compose run --rm web pytest -q
```
Минимум 3 теста:
- парсинг/нормализация входных данных;
- корректный расчёт средней цены;
- фильтрация/пагинация в эндпоинте.

## Принятые решения
- **Pandas** используется при импорте (ETL-нормализация) и при расчёте средней цены в API.
- Кэш — через Redis (Django cache). Для ORM-запросов включён `cacheops`.
- Идемпотентность обеспечена апсертом и сравнением `updated_at`.
- Простая схема ключа: уникальность по (`name`, `category`) — достаточно для мини-сервиса.
```

