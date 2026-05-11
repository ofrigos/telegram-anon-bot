import json
import os
import secrets
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8643886201:AAEuWxq3kjq_5Vb_AIAd62CEIzzvRXZ9I-0"
ADMIN_ID = 8117717482
BOT_USERNAME = "anonimofrigo_bot"

LINKS_FILE = "user_links.json"
DIALOGS_FILE = "active_dialogs.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

user_links = load_json(LINKS_FILE)
dialogs = load_json(DIALOGS_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    args = context.args

    if args and args[0].startswith("ask_"):
        token = args[0][4:]
        target = None
        for uid, t in user_links.items():
            if t == token:
                target = uid
                break
        if target:
            context.user_data["reply_to"] = target
            await update.message.reply_text("🤫 Напишите анонимное сообщение:")
        else:
            await update.message.reply_text("❌ Ссылка недействительна")
        return

    if user_id not in user_links:
        user_links[user_id] = secrets.token_urlsafe(16)
        save_json(LINKS_FILE, user_links)

    link = f"https://t.me/{BOT_USERNAME}?start=ask_{user_links[user_id]}"
    await update.message.reply_text(f"🔗 Ваша ссылка:\n{link}")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if "reply_to" in context.user_data:
        target = context.user_data["reply_to"]
        dialogs[user_id] = target
        dialogs[target] = user_id
        save_json(DIALOGS_FILE, dialogs)
        await context.bot.send_message(int(target), f"🤫 Вопрос: {text}")
        await update.message.reply_text("✅ Отправлено")
        del context.user_data["reply_to"]
    elif user_id in dialogs:
        target = dialogs[user_id]
        await context.bot.send_message(int(target), f"✉️ Ответ: {text}")
        await update.message.reply_text("✅ Ответ отправлен")
    else:
        await update.message.reply_text("❌ Используйте /start")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🤖 Бот запущен")
    app.run_polling()
