import telebot
import json
import os
import time
from telebot import types
from flask import Flask, request

# --- الإعدادات الأساسية ---
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
                content = f.read()
                return json.loads(content) if content else create_default_data()
    except Exception as e:
        print(f"Error loading data: {e}")
    return create_default_data()

def create_default_data():
    return {
        "structure": {},
        "settings": {"start_msg": "👋 أهلاً بكم في بوت جامعة سنار - مكتبة الدفعة"},
        "users": {}, # لتخزين المشتركين
        "admins": [ADMIN_ID]
    }

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

user_path = {}

# --- دوال المساعدة ---
def main_keyboard(user_id, path=[]):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # جلب الأقسام الحالية
    data = load_data()
    curr = data["structure"]
    for folder in path:
        curr = curr.get(folder, {}).get("sub", {})
    
    for btn_name in curr.keys():
        markup.add(types.KeyboardButton(btn_name))

    # أزرار التنقل
    nav_btns = []
    if path:
        nav_btns.append(types.KeyboardButton("⬅️ رجوع"))
        nav_btns.append(types.KeyboardButton("🏠 الرئيسية"))
    nav_btns.append(types.KeyboardButton("🔄 إنعاش البوت"))
    markup.add(*nav_btns)

    # أزرار الأدمن
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("➕ إضافة قسم"), types.KeyboardButton("📥 إضافة محتوى هنا"))
        markup.add(types.KeyboardButton("🔐 الإدارة"))

    return markup

# --- Webhook Setup ---
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
    if app_url and TOKEN:
        bot.remove_webhook()
        time.sleep(1) # تأخير بسيط لضمان المسح
        bot.set_webhook(url=f"https://{app_url}/{TOKEN}")
        return "✅ تم ربط الـ Webhook بنجاح!", 200
    return "❌ خطأ: APP_URL أو TOKEN غير معرف", 400

# --- الأوامر الأساسية ---
@bot.message_handler(func=lambda m: m.text in ["/start", "🔄 إنعاش البوت", "🏠 الرئيسية"])
def start(message):
    user_id = str(message.from_user.id)
    user_path[message.chat.id] = []
    
    data = load_data()
    # تسجيل المستخدم إذا لم يكن موجوداً
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "name": message.from_user.first_name,
            "username": message.from_user.username,
            "joined": time.strftime("%Y-%m-%d")
        }
        save_data(data)
    
    bot.send_message(
        message.chat.id, 
        data["settings"]["start_msg"], 
        reply_markup=main_keyboard(message.from_user.id, [])
    )

@bot.message_handler(func=lambda m: m.text == "🔐 الإدارة")
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 الإحصائيات", "📢 إعلان للكل")
        markup.add("🏠 الرئيسية")
        bot.send_message(message.chat.id, "👑 مرحباً بك في لوحة تحكم المالك", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 الإحصائيات")
def statistics(message):
    if message.from_user.id == ADMIN_ID:
        data = load_data()
        users = data.get("users", {})
        total = len(users)
        msg = f"📊 **إحصائيات البوت الحالية:**\n\n"
        msg += f"👥 إجمالي الطلاب المشتركين: {total}\n"
        msg += "--- آخر 5 منضمين ---\n"
        for uid in list(users.keys())[-5:]:
            msg += f"- {users[uid]['name']} (@{users[uid].get('username', 'None')})\n"
        bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "📢 إعلان للكل")
def broadcast_hint(message):
    if message.from_user.id == ADMIN_ID:
        msg = bot.send_message(message.chat.id, "📝 أرسل الآن الرسالة التي تريد إذاعتها لكل الطلاب (نص فقط):")
        bot.register_next_step_handler(msg, perform_broadcast)

def perform_broadcast(message):
    if message.text == "🏠 الرئيسية": return
    data = load_data()
    users = data.get("users", {})
    success = 0
    fail = 0
    
    bot.send_message(message.chat.id, f"⏳ جاري الإرسال إلى {len(users)} مستخدم...")
    
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 **إعلان من إدارة البوت:**\n\n{message.text}")
            success += 1
            time.sleep(0.05) # حماية من الحظر (Flood)
        except:
            fail += 1
    
    bot.send_message(message.chat.id, f"✅ تم الإرسال بنجاح: {success}\n❌ فشل الإرسال (بوت محظور): {fail}")

# --- معالجة الملفات (رفع المحتوى) ---
@bot.message_handler(content_types=['document', 'photo', 'video', 'audio'])
def handle_docs(message):
    if message.from_user.id != ADMIN_ID: return
    
    path = user_path.get(message.chat.id, [])
    data = load_data()
    curr = data["structure"]
    
    try:
        for folder in path:
            curr = curr[folder]
        if "files" not in curr: curr["files"] = []
        
        # تحديد نوع الملف والـ ID
        f_type = message.content_type
        f_id = getattr(message, f_type).file_id if f_type != 'photo' else message.photo[-1].file_id
        
        curr["files"].append({
            "type": f_type,
            "id": f_id,
            "caption": message.caption or "بدون وصف"
        })
        save_data(data)
        bot.reply_to(message, "✅ تم حفظ الملف في هذا القسم بنجاح!")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء الحفظ: {e}")

# تشغيل السيرفر
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
