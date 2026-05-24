from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import sqlite3
import json
import os
import datetime
from dotenv import load_dotenv
import requests

# ─── ENV & CONFIG ───────────────────────────────────────────────
load_dotenv(override=False)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME ="openai/gpt-oss-20b:free"
import tempfile
# بدل os.getcwd()
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "murshid.db")

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)


# ─── SYSTEM PROMPT ──────────────────────────────────────────────
SYSTEM_PROMPT = """أنت "المرشد الذكي"، مساعد ذكي متخصص في مساعدة طلاب تخصص تكنولوجيا التعليم في جامعة الشرق الأوسط (MEU).

مهمتك:
- الإجابة على أسئلة الطلاب الجدد حول التخصص والجامعة
- شرح الخطة الدراسية والمقررات
- توجيه الطلاب نحو فرص العمل والتدريب
- تقديم معلومات عن مرافق الجامعة والحياة الأكاديمية

معلومات مهمة تعرفها:
- الجامعة: جامعة الشرق الأوسط (MEU) - عمّان، الأردن - تأسست 2005
- التخصص: تكنولوجيا التعليم - 132 ساعة معتمدة - 4 سنوات
- التدريب الميداني: السنة الرابعة - 120 ساعة معتمدة
- فرص العمل: مصمم تعليمي، منتج محتوى رقمي، مدير تدريب، مستشار تعليمي رقمي
- أبرز المهارات: Instructional Design, Moodle, Articulate Storyline, Adobe Suite

قواعد الإجابة:
- تكلم بالعربية دائماً
- كن ودوداً ومشجعاً
- أجوبتك واضحة ومختصرة
- استخدم نقاط عند الحاجة
- إذا سُئلت عن شيء خارج نطاق الجامعة أو التخصص، وجّه الطالب بلطف"""

# ─── OPENROUTER ────────────────────────────────────────────────
def ask_openrouter(messages):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://wallaa-project.onrender.com", 
        "X-Title": "Murshid Bot" 
    }

    data = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print("OpenRouter Error:", response.text)
        return "صار خطأ، حاول مرة ثانية"

    result = response.json()
    return result["choices"][0]["message"]["content"]

# ─── DATABASE ───────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_name TEXT DEFAULT "طالب جديد",
            created_at TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            student_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            university_email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?,?,?,?)",
        (session_id, role, content, datetime.datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

def get_history(session_id, limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "SELECT role, content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit)
    )

    rows = c.fetchall()
    conn.close()

    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def ensure_session(session_id, user_name="طالب جديد"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "INSERT OR IGNORE INTO sessions (session_id, user_name, created_at) VALUES (?,?,?)",
        (session_id, user_name, datetime.datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

with app.app_context():
    init_db()
# ─── ROUTES ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return app.send_static_file("log_in.html")


@app.route("/api/student/register", methods=["POST"])
def register_student():
    data = request.get_json()

    full_name = data.get("full_name")
    student_id = data.get("student_id")
    password = data.get("password")
    university_email = data.get("university_email")
    phone = data.get("phone")

    if not all([full_name, student_id, password, university_email, phone]):
        return jsonify({"error": "جميع الحقول مطلوبة"}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute("""
            INSERT INTO students
            (full_name, student_id, password, university_email, phone, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            full_name,
            student_id,
            password,
            university_email,
            phone,
            datetime.datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "تم إنشاء الحساب بنجاح"
        })

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "الرقم الجامعي أو الإيميل مستخدم مسبقاً"
        }), 409

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@app.route("/api/student/login", methods=["POST"])
def login_student():
    data = request.get_json()
    student_id = data.get("student_id")
    password = data.get("password")

    if not student_id or not password:
        return jsonify({"error": "الرجاء إدخال الرقم الجامعي وكلمة السر"}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, full_name, university_email, phone FROM students WHERE student_id = ? AND password = ?", (student_id, password))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({
            "success": True,
            "student": {
                "name": user[1],
                "email": user[2],
                "phone": user[3]
            }
        })
    else:
        return jsonify({"error": "الرقم الجامعي أو كلمة السر غير صحيحة"}), 401

@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    user_msg   = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    user_name  = data.get("user_name", "طالب جديد")

    if not user_msg:
        return jsonify({"error": "الرسالة فارغة"}), 400

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify({"error": "OpenRouter API غير مضبوط"}), 503

    ensure_session(session_id, user_name)
    save_message(session_id, "user", user_msg)

    history = get_history(session_id, limit=8)

    messages = []

    messages.append({"role": "system", "content": SYSTEM_PROMPT})

    for msg in history[:-1]:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    messages.append({"role": "user", "content": user_msg})

    bot_reply = ask_openrouter(messages)

    save_message(session_id, "assistant", bot_reply)

    return jsonify({
        "reply": bot_reply,
        "session_id": session_id
    })


# ─── STREAMING CHAT ─────────────────────────────────────────────
@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data       = request.get_json()
    user_msg   = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    user_name  = data.get("user_name", "طالب جديد")

    if not user_msg:
        return jsonify({"error": "الرسالة فارغة"}), 400

    ensure_session(session_id, user_name)
    save_message(session_id, "user", user_msg)

    history = get_history(session_id, limit=8)

    def generate():
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history[:-1]:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_msg})

        reply = ask_openrouter(messages)

        save_message(session_id, "assistant", reply)

        yield f"data: {json.dumps({'token': reply}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Access-Control-Allow-Origin": "*",
        }
    )


@app.route("/api/history/<session_id>", methods=["GET"])
def history(session_id):
    return jsonify({
        "messages": get_history(session_id, limit=50)
    })


@app.route("/api/clear/<session_id>", methods=["DELETE"])
def clear_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


@app.route("/api/status", methods=["GET"])
def status():
    if not OPENROUTER_API_KEY:
        return jsonify({"ai": "not_configured"}), 503

    return jsonify({"ai": "openrouter_ready"})


# ─── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    print("=" * 50)
    print("  المرشد الذكي — OpenRouter Edition")
    print("=" * 50)
    print(f"  Model  : {MODEL_NAME}")
    port = int(os.environ.get("PORT", 5000))
    print(f"  Server : http://localhost:{port}")
    print("=" * 50)

    app.run(debug=False, host="0.0.0.0", port=port)