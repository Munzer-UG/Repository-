import telebot
import os
import tempfile
import speech_recognition as sr
from pydub import AudioSegment
from telebot import types
import requests
import json

TOKEN = "8712136440:AAF0kU5pozYp7uLxjobad-4v1pmzdfO9nYk"
CHANNEL_USERNAME = "@sodan249"
SUPPORT_USER = "@U_MP_7"

bot = telebot.TeleBot(TOKEN)

user_languages = {}

LANGUAGES = {
    'ar': 'العربية',
    'en': 'الإنجليزية',
    'fr': 'الفرنسية',
    'de': 'الألمانية',
    'es': 'الإسبانية',
    'ru': 'الروسية',
    'tr': 'التركية'
}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def translate_text(text, target_lang='en'):
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={text}"
        response = requests.get(url)
        data = response.json()
        return data[0][0][0]
    except:
        return "❌ تعذر الترجمة"

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_channel = types.InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        btn_check = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")
        markup.add(btn_channel, btn_check)

        bot.send_message(
            message.chat.id,
            f"👋 أهلاً {user_name}\n"
            "🔒 لاستخدام البوت يجب الاشتراك أولاً في القناة:\n"
            f"📢 {CHANNEL_USERNAME}\n\n"
            "✅ بعد الاشتراك اضغط تحقق",
            reply_markup=markup
        )
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton('🎙 ترجمة صوت'),
        types.KeyboardButton('📝 ترجمة نص'),
        types.KeyboardButton('🌍 تغيير اللغة')
    )
    bot.send_message(
        message.chat.id,
        f"✅ مرحبًا {user_name}!\n"
        "أرسل لي صوت أو نص للترجمة\n\n"
        "لغة الترجمة الحالية: الإنجليزية 🇬🇧",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_sub":
        if check_subscription(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ اشتراكك مفعل!")
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ لم تشترك بعد!", show_alert=True)

@bot.message_handler(func=lambda msg: msg.text == '🌍 تغيير اللغة')
def change_language(message):
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for code, name in LANGUAGES.items():
        buttons.append(types.InlineKeyboardButton(name, callback_data=f"lang_{code}"))
    markup.add(*buttons)
    bot.send_message(message.chat.id, "🌍 اختر لغة الترجمة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_language(call):
    lang_code = call.data.replace('lang_', '')
    user_languages[call.from_user.id] = lang_code
    bot.answer_callback_query(call.id, f"✅ تم تغيير اللغة إلى {LANGUAGES[lang_code]}")
    bot.edit_message_text(
        f"🌍 لغة الترجمة الآن: {LANGUAGES[lang_code]}",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(content_types=['voice', 'audio', 'text'])
def handle_content(message):
    user_id = message.from_user.id

    if not check_subscription(user_id):
        bot.reply_to(message, "⚠️ يجب الاشتراك أولاً!\nاضغط /start")
        return

    dest_lang = user_languages.get(user_id, 'en')

    try:
        text = ""

        if message.voice or message.audio:
            file_info = bot.get_file((message.voice or message.audio).file_id)
            downloaded = bot.download_file(file_info.file_path)

            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
                f.write(downloaded)
                ogg_path = f.name

            wav_path = ogg_path.replace('.ogg', '.wav')
            AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")

            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
                try:
                    text = r.recognize_google(audio, language="ar-SA")
                except:
                    try:
                        text = r.recognize_google(audio, language="en-US")
                    except:
                        text = "❌ تعذر التعرف على الصوت"

            os.unlink(ogg_path)
            os.unlink(wav_path)

        else:
            text = message.text.strip()

        if text.startswith('❌'):
            bot.reply_to(message, text)
            return

        translated = translate_text(text, dest_lang)

        lang_name = LANGUAGES.get(dest_lang, 'الإنجليزية')
        bot.reply_to(
            message,
            f"📝 النص الأصلي:\n{text}\n\n"
            f"🌍 الترجمة ({lang_name}):\n{translated}"
        )

    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {str(e)}\n\n📞 الدعم: {SUPPORT_USER}")

print("🤖 Voice Translate Pro (No Markdown) يعمل...")
bot.polling(none_stop=True)