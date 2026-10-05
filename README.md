# CV Lab

Это общий репозиторий приложения. Он фиксирует совместимые версии трёх самостоятельных модулей через Git submodules:

| Каталог | Назначение |
| --- | --- |
| [cv-test](cv-test/README.md) | Python API для детекции объектов |
| [cv-web](cv-web/README.md) | React UI для детекции и входа |
| [keycloak-integration-test](keycloak-integration-test/README.md) | Kotlin API, проверка JWT и роли Keycloak |

Исходный код каждого модуля хранится в его собственном репозитории. В корневом коммите записаны конкретные коммиты модулей, поэтому обычное обновление корня не меняет их версии произвольно.

## Клонирование

```bash
git clone --recurse-submodules <URL-корневого-репозитория>
```

Если корень уже клонирован без модулей:

```bash
git submodule update --init --recursive
```

## Запуск

Запустите Python API по инструкции в `cv-test/README.md`, Kotlin API и Keycloak по `keycloak-integration-test/README.md`, затем React UI по `cv-web/README.md`. Локальный адрес интерфейса: **http://127.0.0.1:5173/**.

## Обновление версии модуля в корне

Сначала отправьте изменения в репозиторий самого модуля. Затем обновите его указатель в корневом репозитории. Например, для `cv-web`:

```bash
git submodule update --remote cv-web
git add cv-web
git commit -m "chore: update cv-web submodule"
```

Обычное `git submodule update --init --recursive` восстанавливает именно версии, сохранённые в корневом коммите.
