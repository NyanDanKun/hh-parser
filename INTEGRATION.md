# 🔗 Service Integration Guide

**Версия:** 1.0  
**Дата:** 2026-01-14

Этот документ описывает стандарты для интеграции сервисов в единую экосистему Marketing Tools.

---

## 📋 Общая архитектура

```
Gateway (localhost:5000)           # Авторизация + Меню сервисов
├─ Service: HH Parser (5001)      # Парсер вакансий
├─ Service: Auto-ID Parser (5002) # Парсер цен оборудования  
├─ Service: ROI Calculator (5003) # Калькулятор метрик
└─ Service: [Новый] (5004+)       # Следующие сервисы
```

**Связь между сервисами:**
- Nginx reverse proxy объединяет все порты под один домен
- JWT токены для единой авторизации
- Общие стили для единообразного UI

---

## 🔐 Стандарт авторизации

### Shared Secret Key
```python
SECRET_KEY = "marketing-tools-secret-2026"  # Одинаковый для всех сервисов
```

### Auth Middleware (скопируй в каждый сервис)

Создай файл `auth_middleware.py`:

```python
"""Authentication middleware for service integration."""
import jwt
from functools import wraps
from flask import request, redirect, jsonify
import os

# Единый секретный ключ для всех сервисов
SECRET_KEY = os.getenv('JWT_SECRET', 'marketing-tools-secret-2026')
GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:5000')

def require_auth(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Получаем токен из cookie или header
        token = request.cookies.get('auth_token')
        if not token:
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            # Редирект на gateway для авторизации
            return redirect(f'{GATEWAY_URL}/login?redirect={request.url}')
        
        try:
            # Проверяем токен
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload.get('user_id')
            request.username = payload.get('username')
        except jwt.ExpiredSignatureError:
            return redirect(f'{GATEWAY_URL}/login?expired=true')
        except jwt.InvalidTokenError:
            return redirect(f'{GATEWAY_URL}/login?invalid=true')
        
        return f(*args, **kwargs)
    return decorated

def create_token(user_id, username):
    """Create JWT token (только для Gateway)."""
    from datetime import datetime, timedelta
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

### Использование в сервисе

```python
from flask import Flask
from auth_middleware import require_auth

app = Flask(__name__)

@app.route('/')
@require_auth  # Защита роута
def index():
    username = request.username  # Доступ к данным пользователя
    return render_template('index.html', username=username)
```

---

## 🎨 Стандарты UI/UX

### Обязательные элементы в каждом сервисе:

1. **Навигационная панель** (верхняя часть):
```html
<header class="service-header">
    <div class="service-nav">
        <a href="http://localhost:5000/dashboard" class="btn-back">
            ← Назад в меню
        </a>
        <h1>📊 [Название сервиса]</h1>
        <div class="user-info">
            Привет, {{ username }}! | <a href="/logout">Выход</a>
        </div>
    </div>
</header>
```

2. **Общие CSS переменные** (единый стиль):
```css
:root {
    --primary: #6366f1;
    --secondary: #8b5cf6;
    --success: #10b981;
    --danger: #ef4444;
    --warning: #f59e0b;
    --dark: #1f2937;
    --light: #f3f4f6;
    --border: #e5e7eb;
    --radius: 8px;
    --radius-lg: 12px;
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
```

3. **Футер** (опционально):
```html
<footer class="service-footer">
    <p>Marketing Tools © 2026 | <a href="https://github.com/yourname">GitHub</a></p>
</footer>
```

---

## 🔧 Стандарты портов

| Сервис | Порт | URL (локально) | URL (production) |
|--------|------|----------------|------------------|
| Gateway | 5000 | localhost:5000 | yoursite.ru |
| HH Parser | 5001 | localhost:5001 | yoursite.ru/tools/hh-parser |
| Auto-ID Parser | 5002 | localhost:5002 | yoursite.ru/tools/auto-parser |
| ROI Calculator | 5003 | localhost:5003 | yoursite.ru/tools/roi-calc |
| [Новый сервис] | 5004+ | localhost:5004+ | yoursite.ru/tools/[name] |

### Конфигурация в app.py

```python
import os

# Порт сервиса (переменная окружения или дефолт)
PORT = int(os.getenv('SERVICE_PORT', 5001))  # Меняй для каждого сервиса

if __name__ == '__main__':
    app.run(
        debug=False,
        host='0.0.0.0',
        port=PORT
    )
```

---

## 📡 API Endpoints стандарты

### Обязательные endpoints:

```python
@app.route('/health')
def health():
    """Health check для мониторинга."""
    return jsonify({'status': 'ok', 'service': 'hh-parser'})

@app.route('/api/info')
def api_info():
    """Информация о сервисе."""
    return jsonify({
        'name': 'HH Parser',
        'version': '1.0',
        'port': PORT,
        'endpoints': ['/api/stats', '/api/projects', '/api/collect']
    })
```

### Стандартный формат ответов:

```python
# Успех
{
    "success": true,
    "data": {...},
    "message": "Operation completed"
}

# Ошибка
{
    "success": false,
    "error": "Error description",
    "code": "ERROR_CODE"
}
```

---

## 🗂️ Структура файлов сервиса

```
service-name/
├── app.py                  # Главный Flask файл
├── auth_middleware.py      # Копия из этого документа
├── requirements.txt        # Зависимости
├── .env                    # Переменные окружения (не в git!)
├── README.md              # Описание сервиса
├── INTEGRATION.md         # Эта инструкция
├── static/
│   ├── style.css          # Использует общие CSS переменные
│   └── script.js
├── templates/
│   ├── index.html
│   └── ...
├── src/                   # Бизнес-логика
│   ├── __init__.py
│   └── ...
└── data/                  # Локальная база/файлы
    └── database.db
```

---

## 🚀 Nginx конфигурация (для production)

```nginx
# /etc/nginx/sites-available/marketing-tools

server {
    listen 80;
    server_name yoursite.ru;

    # Gateway (главная страница)
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Сервис: HH Parser
    location /tools/hh-parser/ {
        proxy_pass http://localhost:5001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Сервис: Auto-ID Parser
    location /tools/auto-parser/ {
        proxy_pass http://localhost:5002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Добавляй новые сервисы по этому шаблону
}
```

---

## 📦 requirements.txt (базовый набор)

```txt
Flask==3.0.0
flask-cors==4.0.0
PyJWT==2.8.0
python-dotenv==1.0.0
requests==2.31.0
```

---

## 🔄 Переменные окружения (.env)

Создай `.env` файл в каждом сервисе:

```bash
# Service configuration
SERVICE_PORT=5001
SERVICE_NAME="HH Parser"

# Auth
JWT_SECRET=marketing-tools-secret-2026
GATEWAY_URL=http://localhost:5000

# Database (если нужна)
DATABASE_PATH=data/database.db

# API keys (если нужны)
# HH_API_KEY=your-key-here
```

**Важно:** Добавь `.env` в `.gitignore`!

---

## 🧪 Локальное тестирование интеграции

### 1. Запусти Gateway
```bash
cd gateway
python app.py  # Порт 5000
```

### 2. Запусти сервис
```bash
cd service-hh-parser
python app.py  # Порт 5001
```

### 3. Проверь
- Gateway: http://localhost:5000
- Сервис напрямую: http://localhost:5001
- Авторизация работает между ними

---

## ✅ Checklist для нового сервиса

Перед интеграцией убедись:

- [ ] Скопирован `auth_middleware.py`
- [ ] Добавлен `@require_auth` на все роуты
- [ ] Использованы общие CSS переменные
- [ ] Добавлена кнопка "Назад в меню"
- [ ] Порт настроен правильно (5001, 5002, etc.)
- [ ] Создан `.env` файл
- [ ] Endpoints `/health` и `/api/info` работают
- [ ] README.md описывает как запустить

---

## 📞 Контакты / Помощь

Если возникли вопросы при интеграции:
1. Проверь этот документ
2. Посмотри примеры в других сервисах
3. Проверь токен через jwt.io
4. Проверь логи Nginx/Flask

---

**Последнее обновление:** 2026-01-14  
**Версия документа:** 1.0  
**Совместимость:** Все сервисы Marketing Tools
