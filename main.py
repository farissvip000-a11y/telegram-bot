import telebot
import json
import os
from telebot import types
from flask import Flask, request

# --- الإعدادات الأساسية ---
# ريندر هيقرأ التوكن من الإعدادات اللي هتدخلها يدوي (Environment Variables)
TOKEN = os.getenv("TOKEN") 
ADMIN_ID = 8426760652
DATA_FILE = "data.json"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# --- نظام إدارة البيانات ---
def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading data: {e}")
    
    # القالب الأساسي لو الملف مش موجود أو فاضي
    return {
        "structure": {},
        "settings": {"start_msg": "👋 أهلاً بكم في بوت جامعة سنار - مكتبة الدفعة"},
        "admins": [ADMIN_ID]
    }

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

user_path = {}

def get_buttons_at_path(path):
    data = load_data()
    curr = data["structure"]
    for folder in path:
        if folder in curr:
            curr = curr[folder].get("sub", {})
        else:
            return {}
    return curr

def get_content_at_path(path):
    data = load_data()
    curr = data["structure"]
    for folder in path:
        if folder in curr:
            curr = curr[folder]
        else:
            return []
    return curr.get("files", [])

def main_keyboard(user_id, path=[]):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = get_buttons_at_path(path)

    for btn_name in buttons.keys():
        markup.add(types.KeyboardButton(btn_name))

    nav_row = []
    if path:
        nav_row.append(types.KeyboardButton("⬅️ رجوع"))
        nav_row.append(types.KeyboardButton("🏠 الرئيسية"))

    nav_row.append(types.KeyboardButton("🔄 إنعاش البوت"))
    markup.add(*nav_row)

    if user_id == ADMIN_ID:
        admin_row = [types.KeyboardButton("➕ إضافة قسم"), types.KeyboardButton("📥 إضافة محتوى هنا")]
        markup.add(*admin_row)
        markup.add(types.KeyboardButton("🔐 الإدارة"))

    return markup

# --- Webhook ---
@app.route('/' + (TOKEN if TOKEN else "webhook"), methods=['POST'])
def receive_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    else:
        return "forbidden", 403

@app.route("/")
def webhook_setup():
    app_url = os.getenv('APP_URL')
    if app_url and TOKEN:
        bot.remove_webhook()
        bot.set_webhook(url=f"https://{app_url}/{TOKEN}")
        return "✅ تم ربط الـ Webhook بنجاح!", 200
    return "❌ خطأ: APP_URL أو TOKEN غير معرف في الإعدادات", 400

# --- أوامر البوت ---
@bot.message_handler(func=lambda m: m.text == "/start" or m.text == "🔄 إنعاش البوت")
def start(message):
    user_path[message.chat.id] = []
    data = load_data()
    bot.send_message(
        message.chat.id,
        data["settings"]["start_msg"],
        reply_markup=main_keyboard(message.from_user.id, [])
    )

@bot.message_handler(func=lambda m: m.text == "🔐 الإدارة")
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "❌ غير مصرح لك بدخول لوحة التحكم")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📊 الإحصائيات", "📢 إعلان للكل", "🏠 الرئيسية")
    bot.send_message(message.chat.id, "👑 لوحة تحكم الأدمن", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📥 إضافة محتوى هنا")
def add_content_hint(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "📤 قم بإرسال (الملف، الصورة، الفيديو، أو الصوت) وسيتم حفظه في القسم الحالي مباشرة.")

@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_docs(message):
    if message.from_user.id != ADMIN_ID:
        return

    path = user_path.get(message.chat.id, [])
    data = load_data()
    curr = data["structure"]

    # الوصول للمسار الحالي
    for folder in path:
        if folder in curr:
            curr = curr[folder]
        else:
            return bot.reply_to(message, "❌ خطأ في المسار، اعد المحاولة من الرئيسية")

    if "files" not in curr:
        curr["files"] = []

    f_type = message.content_type
    f_id = ""

    if f_type == 'document':
        f_id = message.document.file_id
    elif f_type == 'photo':
        f_id = message.photo[-1].file_id
    elif f_type == 'video':
        f_id = message.video.file_id
    elif f_type == 'audio':
        f_id = message.audio.file_id

    curr["files"].append({
        "type": f_type,
        "id": f_id,
        "caption": message.caption or "ملف جديد"
    })

    save_data(data)
    bot.send_message(message.chat.id, f"✅ تم حفظ {f_type} بنجاح!")

@bot
