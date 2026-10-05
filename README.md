# CV Lab

Единая точка запуска приложения: **Docker Compose находится только в этом репозитории**.
Три самостоятельных модуля подключены через Git submodules; корневой коммит фиксирует их совместимые версии.

| Каталог | Назначение |
| --- | --- |
| [cv-test](cv-test/README.md) | Python / FastAPI, детекция объектов YOLO11n |
| [keycloak-integration-test](keycloak-integration-test/README.md) | Kotlin / Spring Boot, JWT и роли Keycloak |
| [cv-web](cv-web/README.md) | React UI, Nginx и проксирование запросов |

## Запуск всего проекта

Нужны Git и Docker Engine или Docker Desktop с Docker Compose v2.20+.
Устанавливать Java, Gradle, Node.js и Python для контейнерного запуска не нужно.
Все команды Compose выполняются **из корня `cv-complex-test`**:

```bash
git clone --recurse-submodules https://github.com/DanyaChetvyrtov/cv-complex-test.git
cd cv-complex-test
docker compose up --build --detach --wait --wait-timeout 600
```

Если репозиторий уже клонирован:

```bash
git pull --ff-only
git submodule update --init --recursive
docker compose up --build --detach --wait --wait-timeout 600
```

Compose собирает модули и запускает **Keycloak, Kotlin API, Python CV и React UI**.
Kotlin ждёт готовности Keycloak; Nginx запускается после готовности обоих API.
Первый запуск требует интернета для образов, зависимостей и весов YOLO и может занять несколько минут.
После загрузки весов распознавание выполняется локально; изображения во внешние сервисы не отправляются.

| Сервис | Адрес |
| --- | --- |
| React UI | **http://127.0.0.1:5173/** |
| Kotlin API | http://127.0.0.1:8080/api/public |
| Python API / Swagger | http://127.0.0.1:8000/docs |
| Keycloak | http://localhost:8081/ |
| Админка Keycloak | http://localhost:8081/admin/ — `admin / admin` |

Открывайте UI именно на **127.0.0.1:5173**: этот адрес зарегистрирован в redirect URI и web origin Keycloak.
Аккаунты: `demo / demo123` (USER), `manager / manager123` (USER, ADMIN).
Регистрация создаёт пользователя с ролью USER. Это локальный учебный стенд с демонстрационными паролями.

## Маршруты и настройки

React собран в Docker и обслуживается Nginx:

| Путь в браузере | Внутренний адрес |
| --- | --- |
| `/api/health` | `http://cv:8000/health` |
| `/api/vision/detect` | `http://cv:8000/vision/detect` |
| `/auth-api/public`, `/auth-api/me`, `/auth-api/user`, `/auth-api/admin` | `http://api:8080/api/...` |

Вход использует Authorization Code + PKCE: браузер обращается к Keycloak, Kotlin проверяет JWT.
Детекция остаётся отдельным публичным Python API.
Issuer для браузера и Kotlin — `http://localhost:8081/realms/demo`;
ключи JWT Kotlin получает по внутреннему адресу `http://keycloak:8080`.

Необязательные `API_PORT` и `CV_PORT` можно задать в корневом `.env` по [.env.example](.env.example).
Они меняют только опубликованные порты API; внутренние адреса Nginx остаются прежними.
Порты UI и Keycloak фиксированы, поскольку связаны с настройками OAuth.

## Остановка, логи и данные

```bash
docker compose ps
docker compose logs -f
docker compose down
```

Обычная остановка сохраняет пользователей/настройки Keycloak и веса модели.
Volumes используют прежние имена `keycloak-integration-test_keycloak-data` и `cv-test_model-cache`,
поэтому существующие данные сохраняются при переходе на корневой запуск.
Если старый отдельный Compose ещё работает, остановите его контейнеры перед запуском корневого стенда.

Если realm был импортирован до появления React-регистрации, обновите его без удаления пользователей:

```bash
python3 keycloak-integration-test/scripts/enable_registration.py --keycloak-url http://localhost:8081
```

Полный сброс **удаляет пользователей, настройки Keycloak и скачанные веса**:

```bash
docker compose down --volumes
docker compose up --build --detach --wait --wait-timeout 600
```

## Проверка

С запущенным стендом и Python 3:

```bash
python3 scripts/smoke_test.py
python3 keycloak-integration-test/scripts/smoke_test.py
```

В Windows используйте `python` вместо `python3`.
Первая проверка открывает собранный UI, проверяет прокси, отказ без JWT и настоящую детекцию изображения.
Вторая проверяет реальные токены, роли USER/ADMIN, вход через PKCE, регистрацию, refresh и logout.
GitHub Actions корня выполняет обе проверки после сборки и запуска единого Compose.
CI модулей проверяет их собственный код.

## Разработка и обновление модулей

Для разработки React с Vite запустите зависимости из корня:

```bash
docker compose up --build --detach --wait --wait-timeout 600 api cv
docker compose stop web
cd cv-web
npm ci
npm run dev
```

`stop web` освобождает порт 5173, если контейнер UI уже запущен.
Локальный запуск Python и Kotlin из IDE описан в README модулей.
Dockerfile и конфигурация образа остаются в модуле; Compose-файлов в модулях нет.

Сначала отправьте изменения модуля в его собственный репозиторий, затем обновите указатель в корне:

```bash
git submodule update --remote cv-web
git add cv-web
git commit -m "chore: update cv-web submodule"
git push
```

Обычное `git submodule update --init --recursive` восстанавливает версии, сохранённые в корневом коммите.
