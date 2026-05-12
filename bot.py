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

def save_blacklist(blacklist):
    save_json(BLACKLIST_FILE, blacklist)

load_data()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Найти собеседника", "🚪 Завершить чат"],
        ["❓ Помощь"]
    ], resize_keyboard=True)

def get_chat_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Предложить контакт", callback_data="request_contact")],
        [InlineKeyboardButton("⚠️ Пожаловаться", callback_data="report_start")]
    ])

def get_confirm_keyboard(user_id):
    """Кнопки подтверждения отправки контакта"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, отправить", callback_data=f"confirm_yes_{user_id}"),
            InlineKeyboardButton("❌ Нет, отмена", callback_data="confirm_no")
        ]
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
        "• Общайся анонимно\n\n"
        "📞 По вопросам: @Ofrigo"
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
        "• 🔥 Предложить контакт — отправить свой username (с подтверждением)\n"
        "• ⚠️ Пожаловаться — на нарушителя\n\n"
        "📌 *Правила:*\n"
        "• Запрещены оскорбления\n"
        "• После 3 жалоб — блокировка\n\n"
        "📞 По вопросам: @Ofrigo"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Единый обработчик всех сообщений"""
    user_id = str(update.effective_user.id)
    
    # Проверка на бан
    if user_id in load_blacklist():
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
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
        else:
            await update.message.reply_text("❌ Этот тип сообщений не поддерживается.")
    else:
        # Не в чате
        if update.message.text:
            await update.message.reply_text(
                "🤫 Нажмите «🔍 Найти собеседника» чтобы начать общение\n\n"
                "📞 По вопросам: @Ofrigo",
                reply_markup=get_main_keyboard()
            )

# ========== КНОПКИ ==========

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    
    # Подтверждение отправки контакта
    if data.startswith("request_contact"):
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        partner_id = ACTIVE_CHATS[user_id]
        
        # Показываем подтверждение
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, отправить", callback_data=f"confirm_send_{partner_id}"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_send")
            ]
        ])
        
        await query.edit_message_text(
            "⚠️ *Внимание!*\n\n"
            "Вы собираетесь отправить свой username собеседнику.\n"
            "После этого он сможет написать вам в личные сообщения.\n\n"
            "*Отправить username?*",
            reply_markup=confirm_keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Подтверждение отправки
    elif data.startswith("confirm_send_"):
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        partner_id = data.split("_")[2]
        username = update.effective_user.username
        
        if username:
            await context.bot.send_message(
                chat_id=int(partner_id),
                text=f"🔥 *Собеседник хочет поделиться контактом!*\n\n👤 @{username}\n\n_Вы можете написать ему в личные сообщения._",
                parse_mode="Markdown"
            )
            await query.edit_message_text("✅ Username отправлен собеседнику!")
        else:
            await query.edit_message_text("❌ У вас нет username. Установите его в настройках Telegram.")
    
    # Отмена отправки
    elif data in ["cancel_send", "confirm_no"]:
        await query.edit_message_text("❌ Отправка контакта отменена.")
    
    # Жалоба
    elif data == "report_start":
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("😤 Оскорбления", callback_data="report_insult")],
            [InlineKeyboardButton("📨 Спам", callback_data="report_spam")],
            [InlineKeyboardButton("🔞 18+", callback_data="report_adult")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
        ])
        await query.edit_message_text("⚠️ *Причина жалобы:*", reply_markup=keyboard, parse_mode="Markdown")
    
    elif data.startswith("report_"):
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        reason_key = data.split("_")[1]
        partner_id = ACTIVE_CHATS[user_id]
        reason_text = {
            "insult": "Оскорбления",
            "spam": "Спам",
            "adult": "18+"
        }.get(reason_key, "Другое")
        
        reports = load_json("reports.json", [])
        reports.append({
            "from": user_id,
            "on": partner_id,
            "reason": reason_text,
            "time": str(datetime.now())
        })
        save_json("reports.json", reports)
        
        await query.edit_message_text(f"⚠️ *Жалоба отправлена!*\nПричина: {reason_text}\n\nСпасибо!", parse_mode="Markdown")
    
    elif data == "cancel_report":
        await query.edit_message_text("❌ Жалоба отменена.")

# ========== БАН ==========

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Блокировка пользователя (только админ)"""
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("⛔ Нет прав.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Использование: /block ID_пользователя")
        return
    
    target_id = args[0]
    blacklist = load_blacklist()
    
    if target_id not in blacklist:
        blacklist.append(target_id)
        save_blacklist(blacklist)
        await update.message.reply_text(f"✅ Пользователь {target_id} заблокирован.")
    else:
        await update.message.reply_text(f"⚠️ Пользователь уже в чёрном списке.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤫 Анонимный чат запущен! Баги исправлены!")
    app.run_polling()

if __name__ == "__main__":
    main()
