# ============================================
#  Voice Translate Pro v3.0
#  Dev: @U_MP_7
#  Hosting: Flask Webhook - Render.com
# ============================================

import telebot
from telebot import types
import os
import sqlite3
from datetime import datetime
from deep_translator import GoogleTranslator
import speech_recognition as sr
from pydub import AudioSegment
import PyPDF2
import time
from flask import Flask, request, abort

# ==================== [ الإعدادات ] ====================
BOT_TOKEN         = "8712136440:AAF0kU5pozYp7uLxjobad-4v1pmzdfO9nYk"
WEBHOOK_URL       = "https://YOUR_APP_NAME.onrender.com"  # غيّر هذا بعد الرفع
CHANNEL_USERNAME  = "@ump2022th"
CHANNEL_ID        = "@ump2022th"
GROUP_INVITE_LINK = "https://t.me/+KyoM7mvMKAJiYjlk"
GROUP_ID          = -5203259826  # غيّر هذا بـ ID المجموعة الصحيح
ADMIN_ID          = 8743242936
SUPPORT_USERNAME  = "@U_MP_7"
BOT_LINK          = "https://t.me/insta_followepbot?start=8743242936"
PORT              = int(os.environ.get("PORT", 8080))

# ==================== [ تهيئة البوت والسيرفر ] ====================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# ==================== [ قاعدة البيانات ] ====================
conn = sqlite3.connect('voice_translate.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    join_date TEXT,
    total_translations INTEGER DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS translations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,
    original_text TEXT,
    translated_text TEXT,
    target_lang TEXT,
    date TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER PRIMARY KEY,
    target_lang TEXT DEFAULT 'en')''')

conn.commit()

# ==================== [ اللغات ] ====================
LANGUAGES = {
    'ar': 'العربية', 'en': 'English', 'fr': 'Français',
    'es': 'Español', 'de': 'Deutsch', 'tr': 'Türkçe',
    'ru': 'Русский', 'zh-cn': '中文', 'it': 'Italiano',
    'ja': '日本語', 'ko': '한국어', 'hi': 'हिन्दी',
    'pt': 'Português', 'nl': 'Nederlands'
}

# ==================== [ الدوال الأساسية ] ====================

def translate_text(text, dest_lang):
    try:
        return GoogleTranslator(source='auto', target=dest_lang).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return None

def check_subscription(user_id):
    try:
        ch = bot.get_chat_member(CHANNEL_ID, user_id)
        if ch.status in ['left', 'kicked']:
            return False, "القناة"
    except:
        return False, "القناة"
    try:
        gr = bot.get_chat_member(GROUP_ID, user_id)
        if gr.status in ['left', 'kicked']:
            return False, "المجموعة"
    except:
        return False, "المجموعة"
    return True, None

def is_admin(user_id):
    return user_id == ADMIN_ID

def get_target_lang(user_id):
    c.execute("SELECT target_lang FROM settings WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 'en'

def save_user(user_id, username, first_name):
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, join_date) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def save_translation(user_id, type_, original, translated, target_lang):
    c.execute("INSERT INTO translations (user_id, type, original_text, translated_text, target_lang, date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, type_, original, translated, target_lang, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("UPDATE users SET total_translations = total_translations + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def transcribe_voice(ogg_path):
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        wav_path = ogg_path.replace('.ogg', '.wav')
        audio.export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
        for lang in ['ar-AR', 'en-US']:
            try:
                text = recognizer.recognize_google(audio_data, language=lang)
                try: os.remove(wav_path)
                except: pass
                return text, lang[:2]
            except:
                continue
        try: os.remove(wav_path)
        except: pass
        return None, None
    except Exception as e:
        print(f"Voice error: {e}")
        return None, None

def extract_pdf_text(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except:
        return ""

# ==================== [ أزرار البوت ] ====================

def main_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🎙️ • ترجمة الصوتيات",    callback_data="voice"),
        types.InlineKeyboardButton("📝 • ترجمة النصوص",       callback_data="text"),
        types.InlineKeyboardButton("📄 • ترجمة ملفات PDF",    callback_data="pdf"),
        types.InlineKeyboardButton("🌍 • تغيير لغة الترجمة",  callback_data="lang_menu"),
        types.InlineKeyboardButton("📊 • إحصائيات الاستخدام", callback_data="stats"),
        types.InlineKeyboardButton("📂 • سجل الترجمات",       callback_data="history"),
        types.InlineKeyboardButton("ℹ️ • معلومات عن البوت",   callback_data="about"),
        types.InlineKeyboardButton("📞 • الدعم الفني", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")
    )
    return keyboard

def back_button():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 • رجوع للقائمة الرئيسية", callback_data="main_menu"))
    return keyboard

def subscription_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📢 • الاشتراك في القناة",  url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"),
        types.InlineKeyboardButton("👥 • الانضمام للمجموعة",   url=GROUP_INVITE_LINK),
        types.InlineKeyboardButton("🤖 • زيارة البوت",         url=BOT_LINK),
        types.InlineKeyboardButton("✅ • تأكيد الاشتراك",      callback_data="check_sub")
    )
    return keyboard

def languages_menu():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    langs = [
        ("🇸🇦 العربية","ar"),  ("🇺🇸 English","en"),
        ("🇫🇷 Français","fr"), ("🇪🇸 Español","es"),
        ("🇩🇪 Deutsch","de"),  ("🇹🇷 Türkçe","tr"),
        ("🇷🇺 Русский","ru"),  ("🇨🇳 中文","zh-cn"),
        ("🇮🇹 Italiano","it"), ("🇯🇵 日本語","ja"),
        ("🇰🇷 한국어","ko"),    ("🇮🇳 हिन्दी","hi"),
        ("🇵🇹 Português","pt"),("🇳🇱 Nederlands","nl"),
    ]
    buttons = [types.InlineKeyboardButton(name, callback_data=f"setlang_{code}") for name, code in langs]
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.add(buttons[i], buttons[i+1])
        else:
            keyboard.add(buttons[i])
    keyboard.add(types.InlineKeyboardButton("🔙 • رجوع", callback_data="main_menu"))
    return keyboard

# ==================== [ الأوامر ] ====================

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id    = message.from_user.id
    first_name = message.from_user.first_name or "مستخدم"
    username   = message.from_user.username or ""
    save_user(user_id, username, first_name)

    if not is_admin(user_id):
        is_sub, where = check_subscription(user_id)
        if not is_sub:
            text = (
                f"╔══════════════════════════╗\n"
                f"║  🎙️ Voice Translate Pro  ║\n"
                f"╚══════════════════════════╝\n\n"
                f"👋 <b>أهلاً بك {first_name}!</b>\n\n"
                f"⚠️ <b>يجب الاشتراك في {where} أولاً</b>\n\n"
                f"📌 <b>الخطوات:</b>\n"
                f"1️⃣ اشترك في القناة\n"
                f"2️⃣ انضم للمجموعة\n"
                f"3️⃣ اضغط تأكيد الاشتراك\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📞 <b>للمساعدة:</b> {SUPPORT_USERNAME}"
            )
            bot.send_message(user_id, text, reply_markup=subscription_keyboard())
            return

    welcome_text = (
        f"╔══════════════════════════╗\n"
        f"║  🎙️ Voice Translate Pro  ║\n"
        f"║     الإصدار الثالث v3.0    ║\n"
        f"╚══════════════════════════╝\n\n"
        f"🌟 <b>مرحباً {first_name}!</b>\n\n"
        f"<b>✨ المميزات:</b>\n"
        f"🎙️ • ترجمة الصوتيات إلى نص\n"
        f"📝 • ترجمة النصوص الفورية\n"
        f"📄 • ترجمة ملفات PDF\n"
        f"🌍 • دعم 14+ لغة\n"
        f"📊 • سجل كامل للترجمات\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>اختر الخدمة المطلوبة:</b>"
    )
    bot.send_message(user_id, welcome_text, reply_markup=main_menu_keyboard())

# ==================== [ الكول باك ] ====================

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    msg_id  = call.message.message_id
    data    = call.data

    if data == "check_sub":
        if not is_admin(user_id):
            is_sub, where = check_subscription(user_id)
            if not is_sub:
                bot.answer_callback_query(call.id, f"❌ لم تشترك في {where} بعد!", show_alert=True)
                return
        bot.answer_callback_query(call.id, "✅ تم التحقق بنجاح!")
        start_handler(call.message)
        return

    elif data == "main_menu":
        bot.edit_message_text("👇 <b>اختر الخدمة المطلوبة:</b>", user_id, msg_id, reply_markup=main_menu_keyboard())

    elif data == "voice":
        bot.edit_message_text(
            "🎙️ <b>أرسل رسالة صوتية الآن وسيتم ترجمتها فوراً!</b>\n\n📌 المدة القصوى: دقيقتان",
            user_id, msg_id, reply_markup=back_button()
        )

    elif data == "text":
        bot.edit_message_text("📝 <b>أرسل النص الذي تريد ترجمته:</b>", user_id, msg_id, reply_markup=back_button())

    elif data == "pdf":
        bot.edit_message_text("📄 <b>أرسل ملف PDF وسيتم استخراج نصه وترجمته!</b>", user_id, msg_id, reply_markup=back_button())

    elif data == "lang_menu":
        target = get_target_lang(user_id)
        bot.edit_message_text(
            f"🌍 <b>اختر لغة الترجمة</b>\n\nاللغة الحالية: <b>{LANGUAGES.get(target, target)}</b>",
            user_id, msg_id, reply_markup=languages_menu()
        )

    elif data.startswith("setlang_"):
        lang = data.replace("setlang_", "")
        c.execute("INSERT OR REPLACE INTO settings (user_id, target_lang) VALUES (?, ?)", (user_id, lang))
        conn.commit()
        bot.answer_callback_query(call.id, f"✅ تم تغيير اللغة إلى {LANGUAGES.get(lang, lang)}")
        bot.edit_message_text(
            f"✅ <b>تم تغيير لغة الترجمة إلى:</b> {LANGUAGES.get(lang, lang)}",
            user_id, msg_id, reply_markup=back_button()
        )

    elif data == "stats":
        c.execute("SELECT total_translations FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        total = row[0] if row else 0
        c.execute("SELECT type, COUNT(*) FROM translations WHERE user_id = ? GROUP BY type", (user_id,))
        by_type = c.fetchall()
        types_text = "\n".join([f"• {t}: {n}" for t, n in by_type]) or "لا يوجد بعد"
        bot.edit_message_text(
            f"📊 <b>إحصائياتك:</b>\n\n🔢 إجمالي الترجمات: <b>{total}</b>\n\n📋 <b>التفاصيل:</b>\n{types_text}",
            user_id, msg_id, reply_markup=back_button()
        )

    elif data == "history":
        c.execute("SELECT type, original_text, translated_text, date FROM translations WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
        rows = c.fetchall()
        if not rows:
            text = "📂 <b>لا يوجد سجل ترجمات بعد!</b>"
        else:
            lines = ["📂 <b>آخر 5 ترجمات:</b>\n━━━━━━━━━━━━━━━━━━━━━"]
            for type_, orig, trans, date in rows:
                lines.append(f"\n🔹 <b>{type_}</b> | {date[:10]}\n📌 {orig[:50]}\n✅ {trans[:50]}")
            text = "\n".join(lines)
        bot.edit_message_text(text, user_id, msg_id, reply_markup=back_button())

    elif data == "about":
        bot.edit_message_text(
            f"ℹ️ <b>Voice Translate Pro v3.0</b>\n\n"
            f"بوت متكامل للترجمة يدعم:\n"
            f"• الرسائل الصوتية 🎙️\n• النصوص 📝\n• ملفات PDF 📄\n\n"
            f"👨‍💻 <b>المطور:</b> {SUPPORT_USERNAME}",
            user_id, msg_id, reply_markup=back_button()
        )

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

# ==================== [ معالجة الصوت ] ====================

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        is_sub, where = check_subscription(user_id)
        if not is_sub:
            bot.send_message(user_id, f"⚠️ يجب الاشتراك في {where} أولاً!", reply_markup=subscription_keyboard())
            return
    try:
        temp_msg = bot.reply_to(message, "🎙️ <b>جاري معالجة الصوت...</b>")
        file_info  = bot.get_file(message.voice.file_id)
        downloaded = bot.download_file(file_info.file_path)
        ogg_path = f"/tmp/voice_{user_id}_{int(time.time())}.ogg"
        with open(ogg_path, 'wb') as f:
            f.write(downloaded)
        bot.edit_message_text("🔍 <b>جاري التعرف على الكلام...</b>", user_id, temp_msg.message_id)
        text, lang = transcribe_voice(ogg_path)
        try: os.remove(ogg_path)
        except: pass
        if not text:
            bot.edit_message_text(
                "❌ <b>لم نتمكن من فهم الصوت!</b>\n\n• تأكد من وضوح التسجيل\n• حاول التحدث بصوت أعلى",
                user_id, temp_msg.message_id, reply_markup=back_button()
            )
            return
        bot.edit_message_text("🌍 <b>جاري الترجمة...</b>", user_id, temp_msg.message_id)
        target     = get_target_lang(user_id)
        translated = translate_text(text, target)
        if not translated:
            bot.edit_message_text("❌ <b>فشل في الترجمة، حاول مرة أخرى.</b>", user_id, temp_msg.message_id, reply_markup=back_button())
            return
        save_translation(user_id, "صوتي", text, translated, target)
        result = (
            f"✅ <b>تمت ترجمة الصوت بنجاح!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎙️ <b>النص المستخرج:</b>\n{text}\n\n"
            f"🌍 <b>الترجمة ({LANGUAGES.get(target, target)}):</b>\n{translated}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_text(result, user_id, temp_msg.message_id, reply_markup=main_menu_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {e}", reply_markup=back_button())

# ==================== [ معالجة النص ] ====================

@bot.message_handler(content_types=['text'])
def text_handler(message):
    user_id = message.from_user.id
    text    = message.text
    if text.startswith('/'):
        return
    if not is_admin(user_id):
        is_sub, where = check_subscription(user_id)
        if not is_sub:
            bot.send_message(user_id, f"⚠️ يجب الاشتراك في {where} أولاً!", reply_markup=subscription_keyboard())
            return
    try:
        temp_msg   = bot.reply_to(message, "🌍 <b>جاري الترجمة...</b>")
        target     = get_target_lang(user_id)
        translated = translate_text(text, target)
        if not translated:
            bot.edit_message_text("❌ <b>فشل في الترجمة، حاول مرة أخرى.</b>", user_id, temp_msg.message_id, reply_markup=back_button())
            return
        save_translation(user_id, "نص", text, translated, target)
        result = (
            f"✅ <b>تمت الترجمة!</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 <b>النص الأصلي:</b>\n{text}\n\n"
            f"🌍 <b>الترجمة ({LANGUAGES.get(target, target)}):</b>\n{translated}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        bot.edit_message_text(result, user_id, temp_msg.message_id, reply_markup=main_menu_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}", reply_markup=back_button())

# ==================== [ معالجة PDF ] ====================

@bot.message_handler(content_types=['document'])
def document_handler(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        is_sub, where = check_subscription(user_id)
        if not is_sub:
            bot.send_message(user_id, f"⚠️ يجب الاشتراك في {where} أولاً!", reply_markup=subscription_keyboard())
            return
    if not message.document.file_name.lower().endswith('.pdf'):
        bot.reply_to(message, "❌ <b>يرجى إرسال ملف PDF فقط!</b>", reply_markup=back_button())
        return
    try:
        temp_msg   = bot.reply_to(message, "📄 <b>جاري معالجة الملف...</b>")
        file_info  = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        pdf_path = f"/tmp/pdf_{user_id}_{int(time.time())}.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(downloaded)
        pdf_text = extract_pdf_text(pdf_path)
        try: os.remove(pdf_path)
        except: pass
        if not pdf_text:
            bot.edit_message_text("❌ <b>لم نتمكن من استخراج نص من الملف!</b>", user_id, temp_msg.message_id, reply_markup=back_button())
            return
        bot.edit_message_text("🌍 <b>جاري ترجمة المحتوى...</b>", user_id, temp_msg.message_id)
        target = get_target_lang(user_id)
        if len(pdf_text) > 4500:
            pdf_text = pdf_text[:4500] + "..."
        translated = translate_text(pdf_text, target)
        if not translated:
            bot.edit_message_text("❌ <b>فشل في الترجمة.</b>", user_id, temp_msg.message_id, reply_markup=back_button())
            return
        save_translation(user_id, "PDF", pdf_text[:100], translated[:100], target)
        bot.edit_message_text("✅ <b>تمت ترجمة الملف!</b>", user_id, temp_msg.message_id)
        if len(translated) > 4000:
            for i in range(0, len(translated), 4000):
                bot.send_message(user_id, translated[i:i+4000])
        else:
            bot.send_message(user_id, f"📄 <b>الترجمة:</b>\n\n{translated}")
        bot.send_message(user_id, "🎯 <b>اختر خدمة أخرى:</b>", reply_markup=main_menu_keyboard())
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}", reply_markup=back_button())

# ==================== [ أوامر الأدمن ] ====================

@bot.message_handler(commands=['admin'])
def admin_handler(message):
    if not is_admin(message.from_user.id):
        return
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM translations")
    total_trans = c.fetchone()[0]
    bot.send_message(
        message.from_user.id,
        f"🔐 <b>لوحة تحكم الأدمن</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>المستخدمين:</b> {total_users}\n"
        f"📝 <b>الترجمات:</b> {total_trans}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📢 /broadcast - رسالة للجميع"
    )

@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.from_user.id, "📢 <b>أرسل الرسالة لإرسالها للجميع:</b>")
    bot.register_next_step_handler(msg, do_broadcast)

def do_broadcast(message):
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    ok, fail = 0, 0
    for (uid,) in users:
        try:
            bot.send_message(uid, message.text)
            ok += 1
        except:
            fail += 1
        time.sleep(0.05)
    bot.reply_to(message, f"✅ <b>تم الإرسال:</b> {ok}\n❌ <b>فشل:</b> {fail}")

# ==================== [ Flask Webhook ] ====================

@app.route('/', methods=['GET'])
def index():
    return "✅ Voice Translate Pro - Server is running!", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    bot.remove_webhook()
    time.sleep(0.5)
    result = bot.set_webhook(url=webhook_url)
    if result:
        return f"✅ Webhook set successfully: {webhook_url}", 200
    return "❌ Failed to set webhook", 500

@app.route('/remove_webhook', methods=['GET'])
def remove_webhook():
    bot.remove_webhook()
    return "✅ Webhook removed", 200

# ==================== [ التشغيل ] ====================

if __name__ == "__main__":
    print("""
╔══════════════════════════════╗
║  🎙️ Voice Translate Pro v3.0 ║
║  🌐 Flask Webhook Server     ║
║  ✅ جاري التشغيل...          ║
╚══════════════════════════════╝
""")
    app.run(host='0.0.0.0', port=PORT, debug=False)
