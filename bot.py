import json
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ===== НАСТРОЙКИ (ЗАМЕНИТЕ НА СВОИ) =====
TOKEN = "8643886201:AAEuWxq3kjq_5Vb_AIAd62CEIzzvRXZ9I-0"              # Токен от @BotFather
ADMIN_ID = 8117717482             # Ваш ID от @userinfobot
BOT_USERNAME = "anonimofrigo_bot"  # Username бота (без @)
# =========================================

# Файлы для хранения данных
LINKS_FILE = "user_links.json"
DIALOGS_FILE = "active_dialogs.json"
USERS_FILE = "all_users.json"

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Загружаем данные
user_links = load_json(LINKS_FILE)
dialogs = load_json(DIALOGS_FILE)
all_users = load_json(USERS_FILE)
admin_reply_buffer = {}

# ==================== КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    first_name = update.effective_user.first_name
    args = context.args

    # Сохраняем пользователя
    if user_id not in all_users:
        all_users[user_id] = first_name
        save_json(USERS_FILE, all_users)

    # Если перешли по ссылке для вопроса
    if args and args[0].startswith("ask_"):
        token = args[0][4:]
        target = None
        for uid, t in user_links.items():
            if t == token:
                target = uid
                break
        if target:
            context.user_data["reply_to"] = target
            await update.message.reply_text(
                "🤫 *Анонимный вопрос*\n\n"
                "Напишите ваше сообщение. Администратор получит его анонимно.\n\n"
                "📌 Ответ придёт в этот же чат.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Ссылка недействительна или устарела.")
        return

    # Генерируем ссылку для пользователя
    if user_id not in user_links:
        user_links[user_id] = secrets.token_urlsafe(16)
        save_json(LINKS_FILE, user_links)

    token = user_links[user_id]
    link = f"https://t.me/{BOT_USERNAME}?start=ask_{token}"

    # Красивое приветствие
    welcome_text = (
        f"👋 *Привет, {first_name}!*\n\n"
        f"Я бот для анонимных вопросов и ответов.\n\n"
        f"🔗 *Твоя персональная ссылка:*\n"
        f"`{link}`\n\n"
        f"📤 *Как использовать:*\n"
        f"• Отправь ссылку кому угодно\n"
        f"• Человек задаст вопрос анонимно\n"
        f"• Ты получишь уведомление с кнопкой «Ответить»\n\n"
        f"🤫 *Полная анонимность*\n"
        f"• Твой ID и username не видны\n"
        f"• Ответы тоже приходят анонимно\n\n"
        f"📊 *Команды:*\n"
        f"/start — показать ссылку\n"
        f"/info — о боте\n"
        f"/help — помощь\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 *Создатель:* @Ofrigo"
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "ℹ️ *О боте*\n\n"
        "🤫 *Анонимный бот для вопросов*\n"
        "Позволяет получать вопросы от任何人都 анонимно.\n\n"
        "📌 *Возможности:*\n"
        "• Персональная ссылка для каждого\n"
        "• Анонимные вопросы\n"
        "• Ответы через удобную кнопку\n"
        "• Никто не видит твой ID\n\n"
        "🛠 *Технологии:*\n"
        "• Python + python-telegram-bot\n"
        "• Хостинг на Render.com\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👨‍💻 *Создатель:* @Ofrigo\n"
        "⭐ *Поддержать:* не обязательно, но приятно\n\n"
        "_Бот создан с любовью и трудом_ ❤️"
    )
    await update.message.reply_text(info_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ *Как пользоваться ботом*\n\n"
        "🔹 *Для получения вопросов:*\n"
        "1. Отправь /start\n"
        "2. Скопируй свою ссылку\n"
        "3. Отправь ссылку друзьям\n\n"
        "🔹 *Чтобы задать вопрос:*\n"
        "1. Перейди по ссылке друга\n"
        "2. Напиши сообщение\n"
        "3. Друг получит вопрос анонимно\n\n"
        "🔹 *Чтобы ответить:*\n"
        "1. Нажми кнопку «Ответить» под вопросом\n"
        "2. Напиши ответ\n"
        "3. Ответ уйдёт анонимно\n\n"
        "📌 *Команды:*\n"
        "/start — получить ссылку\n"
        "/info — о боте\n"
        "/help — эта справка\n\n"
        "👨‍💻 *Создатель:* @Ofrigo"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id != str(ADMIN_ID):
        await update.message.reply_text("⛔ У вас нет прав для этой команды.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📢 *Как отправить рассылку:*\n\n"
            "`/broadcast Текст сообщения`\n\n"
            "Пример:\n`/broadcast Всем привет! Бот обновлён.`",
            parse_mode="Markdown"
        )
        return

    message_text = " ".join(args)
    start_msg = await update.message.reply_text("📨 Начинаю рассылку...")

    sent = 0
    failed = 0

    for uid, name in all_users.items():
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *Массовое уведомление:*\n\n{message_text}",
                parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1

    await start_msg.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"👥 Всего пользователей: {len(all_users)}",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id != str(ADMIN_ID):
        await update.message.reply_text("⛔ Нет прав.")
        return

    await update.message.reply_text(
        f"📊 *Статистика бота:*\n\n"
        f"👥 Всего пользователей: {len(all_users)}\n"
        f"🔗 Активных ссылок: {len(user_links)}\n"
        f"💬 Активных диалогов: {len(dialogs)//2}",
        parse_mode="Markdown"
    )

# ==================== ОСНОВНАЯ ЛОГИКА ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = str(update.effective_user.id)
    text = update.message.text

    # Сохраняем пользователя
    if sender_id not in all_users:
        all_users[sender_id] = update.effective_user.first_name
        save_json(USERS_FILE, all_users)

    # Если есть активный диалог
    if sender_id in dialogs:
        target_id = dialogs[sender_id]
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"✉️ *Ответ:*\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Ответ отправлен.")
        return

    # Если новый вопрос через ссылку
    if "reply_to" in context.user_data:
        target_id = context.user_data["reply_to"]

        dialogs[sender_id] = target_id
        dialogs[target_id] = sender_id
        save_json(DIALOGS_FILE, dialogs)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Ответить на вопрос", callback_data=f"answer_{sender_id}")]
        ])

        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"🤫 *Новый анонимный вопрос:*\n\n{text}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Вопрос отправлен анонимно.")
        del context.user_data["reply_to"]
        return

    # Если ничего из вышеперечисленного
    await update.message.reply_text(
        "📩 Отправьте /start, чтобы получить свою ссылку для анонимных вопросов."
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = str(update.effective_user.id)

    if data.startswith("answer_"):
        questioner_id = data.split("_")[1]
        admin_reply_buffer[user_id] = questioner_id

        await query.edit_message_text(
            text=query.message.text + "\n\n✏️ *Напишите ваш ответ ниже:*",
            parse_mode="Markdown"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text="💬 Введите текст ответа. Он будет отправлен анонимно."
        )

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id in admin_reply_buffer:
        questioner_id = admin_reply_buffer[user_id]

        await context.bot.send_message(
            chat_id=int(questioner_id),
            text=f"✉️ *Ответ:*\n\n{text}",
            parse_mode="Markdown"
        )

        await update.message.reply_text("✅ Ответ отправлен анонимно.")
        del admin_reply_buffer[user_id]
    elif user_id == str(ADMIN_ID) and user_id in dialogs:
        target_id = dialogs[user_id]
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"✉️ *Сообщение:*\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Отправлено.")

# ==================== ЗАПУСК ====================

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_ID), admin_reply))

    print("🤫 Анонимный бот успешно запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
