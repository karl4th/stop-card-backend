# Backend contract: Stopcard

## Endpoint

```http
POST /api/stopcards
Content-Type: multipart/form-data
```

Форма отправляется один раз после завершения всех семи шагов.

## Multipart fields

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `payload` | JSON string | Да | Все текстовые данные стопкарты |
| `photo` | File | Нет | Фотография нарушения |
| `telegram_init_data` | string | Рекомендуется | Подписанные Telegram Mini App данные |

Рекомендуемые форматы фотографии: `image/jpeg`, `image/png`, `image/webp`, `image/heic`, `image/heif`.

## Payload

```json
{
  "author": {
    "lastName": "Нурланов",
    "firstName": "Асет",
    "patronymic": "Нурланович"
  },
  "worker": {
    "fullName": "Ахметов Бауыржан Серікұлы",
    "department": "Цех №3 / Служба безопасности",
    "object": "Буровая установка БУ-5000"
  },
  "reason": {
    "reason": "accident"
  },
  "circumstances": {
    "selected": ["w1", "t2"]
  },
  "description": {
    "text": "Описание нарушения"
  },
  "hazards": {
    "selected": ["chemical", "other"],
    "otherText": "Другой опасный фактор"
  },
  "corrective": {
    "text": "Необходимые корректирующие действия"
  }
}
```

Файл не включается в JSON. Если пользователь выбрал фотографию, она передаётся отдельным multipart-полем `photo`.

## Validation

| JSON path | Тип | Правило |
|---|---|---|
| `author.lastName` | string | Обязательное, после `trim` не пустое |
| `author.firstName` | string | Обязательное, после `trim` не пустое |
| `author.patronymic` | string | Необязательное, может быть пустым |
| `worker.fullName` | string | Обязательное, после `trim` не пустое |
| `worker.department` | string | Обязательное, после `trim` не пустое |
| `worker.object` | string | Обязательное, после `trim` не пустое |
| `reason.reason` | enum | Обязательное |
| `circumstances.selected` | string[] | Минимум один уникальный элемент |
| `description.text` | string | Обязательное, после `trim` не пустое |
| `hazards.selected` | string[] | Минимум один уникальный элемент |
| `hazards.otherText` | string | Обязательное только при наличии `other` |
| `corrective.text` | string | Обязательное, после `trim` не пустое |

Backend должен повторно валидировать все значения независимо от клиентской валидации.

## Stop reasons

| ID | Значение |
|---|---|
| `accident` | Угроза несчастного случая на производстве |
| `emergency` | Угроза аварии или инцидента |
| `traffic` | Угроза дорожно-транспортного происшествия |
| `fire` | Угроза пожара |
| `environment` | Угроза загрязнения окружающей среды |

## Circumstances

### Работник

| ID | Значение |
|---|---|
| `w1` | Не проведён инструктаж по безопасному ведению работы |
| `w2` | Отсутствует необходимое обучение, удостоверения или сертификаты |
| `w3` | СИЗ отсутствуют или не соответствуют выполняемым работам |

### Инструменты и оборудование

| ID | Значение |
|---|---|
| `t1` | Отсутствует необходимое оборудование или инструменты |
| `t2` | Оборудование или инструменты неисправны |
| `t3` | Неправильное использование оборудования или инструментов |
| `t4` | Оборудование или инструменты используются в опасном положении |

### Процедуры и регламенты

| ID | Значение |
|---|---|
| `p1` | Неизвестные |
| `p2` | Не выполняются |
| `p3` | Непонятные |

### Окружающая среда

| ID | Значение |
|---|---|
| `e1` | Высокая температура |
| `e2` | Низкая температура |
| `e3` | Шум |
| `e4` | Вибрация |
| `e5` | Химические вещества |
| `e6` | Ионизирующее излучение |
| `e7` | Другие нарушения требований безопасности |

## Hazards

| ID | Значение |
|---|---|
| `chemical` | Химическое воздействие |
| `mechanical` | Механическое воздействие |
| `radiation` | Ионизирующее излучение |
| `rotating` | Вращающиеся части машин и механизмов |
| `other` | Другой опасный фактор |

## Telegram authentication

Frontend может передавать `Telegram.WebApp.initData` в поле `telegram_init_data`.

Backend должен:

1. Проверить подпись `initData` по алгоритму Telegram Mini Apps.
2. Проверить срок `auth_date`.
3. Не доверять данным из `initDataUnsafe`.
4. После проверки связать стопкарту с Telegram user ID.

## Photo handling

Backend должен:

1. Проверить MIME type и фактическую сигнатуру файла.
2. Ограничить максимальный размер файла.
3. Генерировать собственное безопасное имя файла.
4. Не использовать исходное имя как путь хранения.
5. Сохранить файл в объектном хранилище и записать URL/key в стопкарту.
6. Обрабатывать отсутствие поля `photo` как нормальный сценарий.

## Successful response

```http
HTTP/1.1 201 Created
Content-Type: application/json
```

```json
{
  "id": "01JZ123456789ABCDEFGHJKMNP",
  "status": "created",
  "createdAt": "2026-06-28T12:00:00Z",
  "photoUrl": "https://storage.example.com/stopcards/photo.jpg"
}
```

Если фотографии нет, `photoUrl` должен быть `null`.

## Validation error

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json
```

```json
{
  "error": "validation_error",
  "fields": {
    "author.lastName": "Поле обязательно"
  }
}
```
