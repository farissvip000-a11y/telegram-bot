import telebot
import json
import os
import time
from telebot import types
from flask import Flask, request

# --- 1. الإعدادات الأساسية ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = 8426760652
DATA_FILE = "data.json"

# تعريف التطبيق للسيرفر (هذا هو الـ app اللي كان ناقص)
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- 2. نظام إدارة البيانات ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "structure": {},
        "settings": {"start_msg": "👋 أهلاً بكم في بوت مكتبة الدفعة - جامعة سنار"},
        "users": {},
        "admins": [ADMIN_ID]
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

user_path = {}

# --- 3. لوحة المفاتيح ---
def main_keyboard(user_id, path=[]):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    data = load_data()
    curr = data["structure"]
    for folder in path:
        curr = curr.get(folder, {}).get("sub", {})
    
    for btn_name in curr.keys():
        markup.add(types.KeyboardButton(btn_name))

    nav = []
    if path:
        nav.extend([types.KeyboardButton("⬅️ رجوع"), types.KeyboardButton("🏠 الرئيسية")])
    nav.append(types.KeyboardButton("🔄 إنعاش"))
    markup.add(*nav)

    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("➕ إضافة قسم"), types.KeyboardButton("📥 إضافة محتوى"))
        markup.add(types.KeyboardButton("🔐 الإدارة"))
    return markup

# --- 4. إعدادات السيرفر (Webhook) ---
@app.route('/' + (TOKEN if TOKEN else "webhook"), methods=['POST'])
def receive_update():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "ok", 200
    return "forbidden", 403

@app.route("/")
def webhook_setup():
    app_url = os.getenv('APP_URL')
    if app_url:
        bot.remove_webhook()
        time.sleep(1)
        # التأكد من صياغة الرابط بشكل صحيح
        clean_url = app_url.replace("https://", "").replace("http://", "").rstrip('/')
        bot.set_webhook(url=f"https://{clean_url}/{TOKEN}")
        return "✅ تم ربط الـ Webhook بنجاح!", 200
    return "❌ أضف رابط الـ APP_URL في إعدادات ريندر", 400

# --- 5. أوامر الإدارة والإحصائيات ---
@bot.message_handler(func=lambda m: m.text == "🔐 الإدارة")
def admin_menu(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 الإحصائيات", "📢 إذاعة للكل", "🏠 الرئيسية")
        bot.send_message(message.chat.id, "👑 لوحة تحكم المالك", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def stats(message):
    if message.from_user.id == ADMIN_ID:
        data = load_data()
        total = len(data.get("users", {}))
        bot.send_message(message.chat.id, f"👥 عدد الطلاب المشتركين: {total}")

@bot.message_handler(func=lambda m: m.text == "📢 إذاعة للكل")
def broadcast(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "📝 أرسل الإعلان الآن:")
        bot.register_next_step_handler(msg, send_to_all)

def send_to_all(message):
    data = load_data()
    users = data.get("users", {})
    count = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **إعلان مهم:**\n\n{message.text}")
            count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ تم الإرسال لـ {count} طالب")

# --- 6. الأوامر العامة ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    data = load_data()
    if user_id not in data["users"]:
        data["users"][user_id] = {"name": message.from_user.first_name}
        save_data(data)
    
    user_path[message.chat.id] = []
    bot.send_message(message.chat.id, data["settings"]["start_msg"], 
                     reply_markup=main_keyboard(message.from_user.id))

# تشغيل السيرفر
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
