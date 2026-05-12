import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8903396597:AAEI3buQrnojm-k4ltqz3uZ3IdDiP6zakAk"
ADMIN_ID = 8117717482

# ========== ДАННЫЕ ==========
WAITING_LIST = []
ACTIVE_CHATS = {}
SUPPORT_MODE = {}  # {user_id: True} - пользователь в режиме поддержки
REPORTS_FILE = "reports.json"
BLACKLIST_FILE = "blacklist.json"
CHATS_FILE = "chats.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, 'r') as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

def load_data():
    global WAITING_LIST, ACTIVE_CHATS
    data = load_json(CHATS_FILE, {"waiting": [], "active": {}})
    WAITING_LIST = data.get("waiting", [])
    ACTIVE_CHATS = data.get("active", {})

def save_data():
    save_json(CHATS_FILE, {"waiting": WAITING_LIST, "active": ACTIVE_CHATS})

def load_blacklist():
    return load_json(BLACKLIST_FILE, [])

load_data()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Найти собеседника", "🚪 Завершить чат"],
        ["❓ Помощь", "📞 Поддержка"]
    ], resize_keyboard=True)

def get_chat_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Предложить контакт", callback_data="request_contact")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data="report_start")]
    ])

# ========== КОМАНДЫ ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if str(user.id) in load_blacklist():
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!* ✨\n\n"
        "🤫 *Анонимный чат 1 на 1*\n\n"
        "• Нажми «🔍 Найти собеседника»\n"
        "• Общайся анонимно\n"
        "• Нажми «📞 Поддержка» если проблема"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = str(update.effective_user.id)
    
    # Выходим из режима поддержки если был
    if user_id in SUPPORT_MODE:
        del SUPPORT_MODE[user_id]
    
    if "🔍 Найти собеседника" in text:
        await find(update, context)
    elif "🚪 Завершить чат" in text:
        await stop(update, context)
    elif "❓ Помощь" in text:
        await help_command(update, context)
    elif "📞 Поддержка" in text:
        await contact_admin(update, context)

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in load_blacklist():
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
    if user_id in ACTIVE_CHATS:
        await update.message.reply_text("❌ Вы уже в чате. Нажмите «🚪 Завершить чат».")
        return
    
    if user_id in WAITING_LIST:
        await update.message.reply_text("⏳ Вы уже в очереди.")
        return
    
    WAITING_LIST.append(user_id)
    save_data()
    await update.message.reply_text("🔍 *Ищем собеседника...*", parse_mode="Markdown")
    
    if len(WAITING_LIST) >= 2:
        user1 = WAITING_LIST.pop(0)
        user2 = WAITING_LIST.pop(0)
        
        ACTIVE_CHATS[user1] = user2
        ACTIVE_CHATS[user2] = user1
        save_data()
        
        for uid in [user1, user2]:
            await context.bot.send_message(
                chat_id=int(uid),
                text="✅ *Собеседник найден!*\n\nМожете общаться анонимно.",
                reply_markup=get_chat_keyboard(),
                parse_mode="Markdown"
            )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in WAITING_LIST:
        WAITING_LIST.remove(user_id)
        save_data()
        await update.message.reply_text("❌ Поиск отменён.", reply_markup=get_main_keyboard())
        return
    
    if user_id in ACTIVE_CHATS:
        partner_id = ACTIVE_CHATS[user_id]
        del ACTIVE_CHATS[user_id]
        if partner_id in ACTIVE_CHATS:
            del ACTIVE_CHATS[partner_id]
        save_data()
        
        await context.bot.send_message(
            chat_id=int(partner_id),
            text="🚪 *Собеседник покинул чат.*",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
        await update.message.reply_text("🚪 *Чат завершён.*", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        return
    
    await update.message.reply_text("❌ Вы не в чате.", reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "❓ *Помощь*\n\n"
        "• «🔍 Найти собеседника» — начать поиск\n"
        "• «🚪 Завершить чат» — выйти из диалога\n"
        "• «📞 Поддержка» — написать администратору\n\n"
        "📌 *Правила:*\n"
        "• Запрещены оскорбления\n"
        "• После 3 жалоб — блокировка"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включение режима поддержки"""
    user_id = str(update.effective_user.id)
    
    # Включаем режим поддержки
    SUPPORT_MODE[user_id] = True
    
    await update.message.reply_text(
        "📞 *Режим поддержки*\n\n"
        "Напишите ваше сообщение. Администратор ответит вам.\n\n"
        "✏️ *Введите сообщение:*",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений в режиме поддержки"""
    user_id = str(update.effective_user.id)
    
    if user_id not in SUPPORT_MODE:
        return
    
    text = update.message.text
    user_name = update.effective_user.first_name
    
    # Отправляем админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📞 *ПОДДЕРЖКА*\n\n"
             f"👤 {user_name}\n"
             f"🆔 `{user_id}`\n"
             f"📝 {text}",
        parse_mode="Markdown"
    )
    
    # Выходим из режима поддержки
    del SUPPORT_MODE[user_id]
    
    await update.message.reply_text(
        "✅ *Сообщение отправлено!*\n\n"
        "Администратор ответит вам в этот чат.\n"
        "Ожидайте...",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ответ администратора пользователю"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Нажмите «Ответить» на сообщение пользователя")
        return
    
    original = update.message.reply_to_message
    reply_text = update.message.text
    
    # Ищем ID пользователя в оригинальном сообщении
    for line in original.text.split("\n"):
        if "🆔" in line or "ID" in line:
            # Извлекаем цифры
            import re
            numbers = re.findall(r'\d+', line)
            if numbers:
                target_id = numbers[0]
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"📞 *Ответ поддержки:*\n\n{reply_text}",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
                return
    
    await update.message.reply_text("❌ Не удалось найти ID пользователя в сообщении")

async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обычные сообщения в чате"""
    user_id = str(update.effective_user.id)
    
    # Если в режиме поддержки — пропускаем
    if user_id in SUPPORT_MODE:
        return
    
    # Если в активном чате
    if user_id in ACTIVE_CHATS:
        partner_id = ACTIVE_CHATS[user_id]
        
        if update.message.text:
            await context.bot.send_message(
                chat_id=int(partner_id),
                text=f"💬 *Аноним:* {update.message.text}",
                parse_mode="Markdown"
            )
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=int(partner_id),
                photo=update.message.photo[-1].file_id,
                caption="📸 *Аноним отправил фото*",
                parse_mode="Markdown"
            )
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=int(partner_id),
                sticker=update.message.sticker.file_id
            )
    else:
        # Не в чате и не в режиме поддержки
        if not user_id in SUPPORT_MODE:
            await update.message.reply_text(
                "🤫 Нажмите «🔍 Найти собеседника» чтобы начать общение\n\n"
                "Или «📞 Поддержка» если есть вопрос",
                reply_markup=get_main_keyboard()
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    
    # Предложение контакта
    if data == "request_contact":
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        partner_id = ACTIVE_CHATS[user_id]
        username = update.effective_user.username
        
        if username:
            await context.bot.send_message(
                chat_id=int(partner_id),
                text=f"🔥 *Собеседник хочет поделиться контактом!*\n\n👤 @{username}",
                parse_mode="Markdown"
            )
            await query.edit_message_text("✅ Username отправлен.")
        else:
            await query.edit_message_text("❌ Установите username в настройках Telegram.")
    
    # Жалоба
    elif data == "report_start":
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        partner_id = ACTIVE_CHATS[user_id]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("😤 Оскорбления", callback_data=f"report_insult_{partner_id}")],
            [InlineKeyboardButton("📨 Спам", callback_data=f"report_spam_{partner_id}")],
            [InlineKeyboardButton("🔞 18+", callback_data=f"report_adult_{partner_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
        ])
        await query.edit_message_text("⚠️ *Причина жалобы:*", reply_markup=keyboard, parse_mode="Markdown")
    
    elif data.startswith("report_"):
        parts = data.split("_")
        if len(parts) >= 3:
            reason_key = parts[1]
            partner_id = parts[2]
            reason_text = {
                "insult": "Оскорбления",
                "spam": "Спам",
                "adult": "18+"
            }.get(reason_key, "Другое")
            
            await query.edit_message_text(f"⚠️ *Жалоба отправлена!*\nПричина: {reason_text}", parse_mode="Markdown")
    
    elif data == "cancel_report":
        await query.edit_message_text("❌ Отменено.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_reply))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_chat_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤫 Анонимный чат запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
