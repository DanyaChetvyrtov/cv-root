# CV Lab — React + Kotlin BFF + Keycloak + Python CV

Единая точка запуска — **корневой `compose.yaml`**. Модули подключены через Git submodules.

React обращается только к Kotlin BFF. BFF управляет OIDC-сессией с Keycloak и вызывает внутренний Python CV.
Access/refresh-токены хранятся в серверной HTTP-сессии; браузер получает HttpOnly-cookie `BFFSESSION`.
Вход и регистрация открывают формы Keycloak через редирект BFF. React не обменивает код на токены и не знает адрес CV.
Keycloak использует кастомную тему `cv-access`, визуально повторяющую тёмную зелёно-синюю стилистику React-приложения.

## Сотрудники и проверка по лицу

1. Откройте UI и войдите как `manager / manager123` (ADMIN + USER).
2. В блоке «Пропускной пункт» задайте табельный номер, ФИО, отдел (необязательно) и чёткое фото с одним лицом.
3. Нажмите «Добавить в базу». YuNet выделит лицо, SFace создаст его числовой шаблон, Kotlin сохранит запись в PostgreSQL.
4. В «Проверить человека» загрузите другое фото того же человека. Результат: сотрудник найден, не найден или неоднозначное совпадение.
5. Удаление сотрудника также удаляет шаблон лица; после удаления он больше не распознаётся по этой записи.

Управление базой и её просмотр доступны ADMIN, проверка — USER. `demo / demo123` может только проверять.
Сотрудник в базе — бизнес-запись; ему не требуется учётная запись Keycloak. На одного сотрудника сохраняется один шаблон.
Исходные фотографии не сохраняются: в PostgreSQL остаются метаданные и 128 чисел с версией модели.
База хранится в volume `employee-data` и переживает перезапуски. Веса YuNet/SFace скачиваются один раз в существующий model-cache,
проверяются по SHA-256 и затем работают локально без интернета. Обучение модели для каждого сотрудника не нужно.

Фото без лица, с несколькими лицами или слишком маленьким лицом возвращает 422. Повторный табельный номер или уже
зарегистрированное лицо — 409. Ошибка CV/БД не превращается в результат «не найден». При близких совпадениях ответ
`ambiguous` не содержит выбранного сотрудника. Фото-проверка не включает liveness: фотография/экран могут обмануть её;
результат не должен самостоятельно открывать реальный турникет.

Порог cosine similarity задаёт администратор через `FACE_SIMILARITY_THRESHOLD` (по умолчанию 0.5),
минимальный разрыв с ближайшим другим кандидатом — `FACE_AMBIGUITY_MARGIN` (0.05).
Показатель сходства не является вероятностью: порог нужно проверять на ваших фотографиях, включая посторонних людей.
Поиск линейный и подходит для учебной базы; для большой базы потребуется отдельный индекс векторов.

## Запуск всего проекта

Нужны Git и Docker с Compose v2.20+. Из корня проекта:

```bash
git clone --recurse-submodules https://github.com/DanyaChetvyrtov/cv-root.git
cd cv-complex-test
docker compose up --build --detach --wait --wait-timeout 600
```

Обновление существующей копии:

```bash
git pull --ff-only
git submodule update --init --recursive
docker compose up --build --detach --wait --wait-timeout 600
```

Первый запуск скачивает образы, зависимости и веса YuNet/SFace. Java, Gradle, Node.js и Python на хосте не нужны.
Compose запускает пять основных сервисов и одноразовый `keycloak-init`.
Инициализатор создаёт/обновляет confidential-клиент `demo-bff`, роли, регистрацию и тему `cv-access`, отключает прежние
`demo-browser`/`demo-cli`, **сохраняя существующих пользователей и их роли**. Удалять volumes при обновлении не нужно.

| Сервис | Адрес |
| --- | --- |
| React и все пользовательские API через BFF | **http://127.0.0.1:5173/** |
| Kotlin BFF, локальный диагностический порт | http://127.0.0.1:8080/api/public |
| Keycloak | http://localhost:8081/ |
| Админка Keycloak | http://localhost:8081/admin/ — `admin / admin` |
| Python CV | Только Docker-сеть: `http://cv:8000`, порт на хост не опубликован |
| PostgreSQL сотрудников | Только Docker-сеть: `postgres:5432`, volume `employee-data` |

Открывайте UI именно на **127.0.0.1:5173**: этот origin зарегистрирован для callback/logout.
Аккаунты: `demo / demo123` (USER), `manager / manager123` (USER, ADMIN).
Новому пользователю назначается USER. Для детекции необходимо войти.
Распознавание выполняется локально; изображения не отправляются внешнему ML-сервису.

## Маршруты

Nginx и Vite направляют **все `/api/*` в Kotlin без изменения пути**.

| Маршрут | Поведение |
| --- | --- |
| `GET /api/public` | Публичная информация BFF, без issuer/client secret/токенов |
| `GET /api/health` | Состояние внутреннего CV через BFF |
| `GET /api/auth/login` | BFF начинает Authorization Code + PKCE |
| `GET /api/auth/register` | BFF открывает регистрацию Keycloak |
| `GET /api/auth/callback/keycloak` | Callback обрабатывает Kotlin; React получает редирект на `/` |
| `GET /api/auth/csrf` | CSRF-токен для текущей cookie-сессии |
| `GET /api/me` | Профиль без OAuth-токенов |
| `GET /api/user`, `GET /api/admin` | Проверка USER / ADMIN |
| `POST /api/vision/detect` | USER + CSRF; Kotlin передаёт multipart в Python |
| `GET /api/employees` | ADMIN; список с `page` и `size` (до 100) |
| `POST /api/employees` | ADMIN + CSRF; multipart `employeeCode`, `fullName`, `department`, `image` |
| `DELETE /api/employees/{id}` | ADMIN + CSRF; удаление записи и шаблона |
| `POST /api/employees/identifications` | USER + CSRF; multipart `image`, сопоставление лица с базой |
| `POST /api/auth/logout` | CSRF; очистка BFF-сессии и OIDC logout Keycloak |

BFF проверяет state/nonce, подпись и claims ID token. Клиент confidential, с PKCE S256;
password grant для приложения отключён. Access token обновляется на сервере при защищённых запросах.
При отозванном refresh token сессия удаляется и API отвечает 401.
Роли берутся только из `resource_access.demo-api.roles`, не из realm-admin или чужого клиента.

Сессия имеет 30-минутный idle timeout и сохраняется после обновления страницы.
CSRF обязателен для POST, включая logout; React получает новый токен перед каждым изменяющим запросом.
API отвечает 401 без сессии и 403 без прав/с валидной сессией, но неверным CSRF.
OIDC logout может выполнять навигацию браузера через Keycloak; OAuth-протоколом управляет сервер, а не React.

## Настройки и данные

Необязательные настройки находятся в корневом [.env.example](.env.example):
`API_PORT` — диагностический порт BFF; `KEYCLOAK_CLIENT_SECRET` — secret confidential-клиента.
Инициализатор и BFF используют одно значение secret. Публичные URL локального стенда фиксированы. `DATABASE_PASSWORD` используется PostgreSQL и BFF;
Liquibase автоматически создаёт таблицы сотрудников при запуске API.

```bash
docker compose ps -a
docker compose logs -f api keycloak-init
docker compose down
```

Обычная остановка сохраняет пользователей и веса.
Volumes сохраняют прежние имена `keycloak-integration-test_keycloak-data` и `cv-test_model-cache`.
Если остались контейнеры прежнего раздельного запуска, сначала остановите их.
Повторный импорт realm сам по себе не обновляет существующий realm; это делает `keycloak-init`.

`docker compose down --volumes` **удаляет сотрудников, пользователей/настройки Keycloak и веса моделей** — для обычного обновления не используйте.

## Проверка

С запущенным стендом и Python 3:

```bash
python3 scripts/smoke_test.py
```

Для проверки сотрудников с тестовым публичным NASA-фото:

```bash
python3 -m pip install 'Pillow>=11,<13'
python3 cv-test/scripts/fetch_test_face.py /tmp/cv-test-face.png
python3 scripts/smoke_test.py --face-image /tmp/cv-test-face.png
```

В Windows — `python` и путь в вашей временной папке вместо `/tmp`. Без `--face-image` проверяется существующий сценарий OIDC/YOLO. Проверяются реальные вход/регистрация, USER/ADMIN, HttpOnly/SameSite cookie,
CSRF, серверный refresh, отзыв сессии в Keycloak, logout и детекция через BFF.
Тест временно задаёт клиенту короткий срок access token для проверки refresh и восстанавливает настройку;
создаёт и удаляет только собственный временный аккаунт.
CI корня запускает оба сценария после сборки единого Compose, затем перезапускает BFF/CV и проверяет сохранность базы и шаблонов; CI Kotlin тестирует реальный OIDC-код с локальными HTTP-фикстурами.

## Разработка

Для Vite запустите зависимости из корня:

```bash
docker compose up --build --detach --wait --wait-timeout 600 api cv
docker compose stop web
cd cv-web
npm ci
npm run dev
```

Для Kotlin из IDE: из корня поднимите `keycloak-init cv`, остановите контейнер `api`, затем запустите
`./gradlew bootRun` из `keycloak-integration-test`. Локальному BFF также нужен PostgreSQL с `DATABASE_URL`, `DATABASE_USERNAME`, `DATABASE_PASSWORD` (контейнерная БД наружу не опубликована).
Локальному BFF нужен `CV_SERVICE_URL`, доступный с хоста:
для этого режима Python можно запустить локально по README `cv-test`; контейнер CV по умолчанию наружу не опубликован.
README модулей описывают их разработку. Dockerfile остаются в модулях; Compose-файлов в них нет.

После изменений модуля отправьте его коммит в собственный репозиторий и обновите gitlink в корне:

```bash
git submodule update --remote cv-web
git add cv-web
git commit -m "chore: update cv-web submodule"
git push
```

## Ограничения учебного стенда

`start-dev`, H2, локальные HTTP-адреса и демонстрационные credentials не предназначены для production.
Там нужны HTTPS, `SESSION_COOKIE_SECURE=true`, PostgreSQL для Keycloak, защищённые secrets и разрешённые callback/logout URL.
HTTP-сессии BFF сейчас в памяти одного экземпляра: перезапуск завершит их; для нескольких экземпляров нужен общий session store.
MFA настраивается политиками Keycloak, в этом demo принудительно не включена.


## Keycloak theme

Формы входа, регистрации и остальные страницы login flow используют тему `cv-access` из
`keycloak-integration-test/keycloak/themes/cv-access`. Тема наследует штатные шаблоны Keycloak и меняет только presentation layer:
фон, карточку, типографику, поля, кнопки, ссылки и сообщения об ошибках. Это позволяет сохранить стандартный OIDC flow,
MFA/required actions и встроенную валидацию Keycloak без копирования FreeMarker-шаблонов.

После обновления темы достаточно перезапустить Keycloak:

```bash
docker compose restart keycloak keycloak-init
```

Для полной пересборки стенда используйте обычный `docker compose up --build --detach --wait --wait-timeout 600`.
