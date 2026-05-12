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
REPORTS_FILE = "reports.json"
BLACKLIST_FILE = "blacklist.json"
CHATS_FILE = "chats.json"

REPORT_REASONS = {
    "insult": "😤 Мат / Оскорбления",
    "spam": "📨 Спам / Реклама",
    "adult": "🔞 18+ контент",
    "other": "❓ Другое"
}

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

def load_reports():
    return load_json(REPORTS_FILE, [])

def save_reports(reports):
    save_json(REPORTS_FILE, reports)

def load_blacklist():
    return load_json(BLACKLIST_FILE, [])

def save_blacklist(blacklist):
    save_json(BLACKLIST_FILE, blacklist)

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
        "🔹 *Как пользоваться:*\n"
        "• Нажми «🔍 Найти собеседника»\n"
        "• Жди пока кто-то подключится\n"
        "• Общайся анонимно\n\n"
        "📞 *Есть проблема?* Нажми «Поддержка»"
    )
    
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
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
    """Связь с администратором - простой режим"""
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name
    
    # Просто отправляем сообщение админу с кнопкой
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ответить", callback_data=f"reply_to_{user_id}")]
    ])
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📞 *ЗАПРОС ПОДДЕРЖКИ*\n\n"
             f"Пользователь: {user_name}\n"
             f"ID: `{user_id}`\n\n"
             f"Напишите ответ и нажмите кнопку ниже:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    
    await update.message.reply_text(
        "📞 *Сообщение отправлено администратору!*\n\n"
        "Ответ придёт в этот чат в течение нескольких минут.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Если пользователь в активном чате
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    
    # Ответ админа на запрос поддержки
    if data.startswith("reply_to_"):
        target_id = data.split("_")[2]
        context.user_data["reply_target"] = target_id
        await query.edit_message_text(
            text=query.message.text + "\n\n✏️ *Теперь напишите ваш ответ:*",
            parse_mode="Markdown"
        )
        await query.message.reply_text("Введите текст ответа:")
        return
    
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
                text=f"🔥 *Собеседник хочет поделиться контактом!*\n\n"
                     f"👤 @{username}",
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
            
            reports = load_reports()
            reports.append({
                "from": user_id,
                "on": partner_id,
                "reason": reason_text,
                "time": str(datetime.now())
            })
            save_reports(reports)
            
            await query.edit_message_text(f"⚠️ *Жалоба отправлена!*\nПричина: {reason_text}", parse_mode="Markdown")
    
    elif data == "cancel_report":
        await query.edit_message_text("❌ Отменено.")

# Обработка ответа админа на поддержку
async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return
    
    if "reply_target" in context.user_data:
        target_id = context.user_data["reply_target"]
        reply_text = update.message.text
        
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"📞 *Ответ поддержки:*\n\n{reply_text}\n\n━━━━━━━━━━━━━━━━━━━\n_Чтобы написать снова — нажмите «Поддержка»_",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {target_id}")
        del context.user_data["reply_target"]

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤫 Анонимный чат запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
