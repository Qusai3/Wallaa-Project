# المرشد الذكي — إعداد الشات بوت

## المتطلبات
- Python 3.8+
- Ollama مثبت ويعمل
- نموذج llama3 محمّل في Ollama

---

## خطوات التشغيل

### 1. تأكد أن Ollama يعمل
```bash
ollama serve
```

### 2. تأكد أن نموذج llama3 موجود
```bash
ollama pull llama3
```

### 3. ثبّت المكتبات
```bash
pip install -r requirements.txt
```

### 4. شغّل الخادم
```bash
python app.py
```

### 5. افتح المتصفح
```
http://localhost:5000
```
أو افتح `03-chat.html` مباشرة (تأكد أن Flask يعمل على 5000).

---

## هيكل الملفات
```
murshid/
├── app.py            ← Flask backend
├── requirements.txt  ← المكتبات
├── murshid.db        ← SQLite (تُنشأ تلقائياً)
└── 03-chat.html      ← واجهة الشات
```

## API Endpoints
| Method | Endpoint | الوصف |
|--------|----------|-------|
| POST | `/api/chat` | إرسال رسالة والحصول على رد |
| GET  | `/api/history/:id` | سجل المحادثة |
| DELETE | `/api/clear/:id` | مسح المحادثة |
| GET  | `/api/status` | حالة Ollama |
| GET  | `/api/sessions` | قائمة الجلسات |
