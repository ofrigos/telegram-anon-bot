import json
import os
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8903396597:AAEI3buQrnojm-k4ltqz3uZ3IdDiP6zakAk"
ADMIN_ID = 8117717482

# ========== ДАННЫЕ ==========
WAITING_LIST = []
ACTIVE_CHATS = {}
ADMIN_REPLY_BUFFER = {}
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
    user_id = str(user.id)
    
    if user_id in load_blacklist():
        await update.message.reply_text("🚫 Вы заблокированы.")
        return
    
    welcome_text = (
        f"✨ *Привет, {user.first_name}!* ✨\n\n"
        "🤫 *Анонимный чат 1 на 1*\n"
        "Общайся с незнакомцами, не раскрывая личности.\n\n"
        "🔹 *Как пользоваться:*\n"
        "• Нажми «🔍 Найти собеседника»\n"
        "• Жди пока кто-то подключится\n"
        "• Общайся анонимно\n\n"
        "📞 *Есть проблема?* Нажми «Поддержка»"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

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
                text="✅ *Собеседник найден!*\n\nМожете общаться анонимно.\n\n👇 Кнопки под сообщениями:",
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
        "❓ *Помощь по боту*\n\n"
        "🔹 *Как начать:*\n"
        "• Нажми «🔍 Найти собеседника»\n"
        "• Ожидай подключения\n"
        "• Общайся анонимно\n\n"
        "🔹 *Во время чата:*\n"
        "• 🔥 Предложить контакт — отправить свой username\n"
        "• ⚠️ Пожаловаться — на нарушителя\n\n"
        "🔹 *Проблемы:*\n"
        "• Нажми «📞 Поддержка» — напишешь администратору\n\n"
        "📌 *Правила:*\n"
        "• Запрещены оскорбления и 18+\n"
        "• После 3 жалоб — блокировка"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id in ACTIVE_CHATS:
        await update.message.reply_text(
            "❌ Вы сейчас в чате с собеседником.\n"
            "Сначала завершите чат (🚪 Завершить чат).",
            reply_markup=get_main_keyboard()
        )
        return
    
    ADMIN_REPLY_BUFFER[user_id] = True
    
    await update.message.reply_text(
        "📞 *Связь с поддержкой*\n\n"
        "Напишите ваше сообщение. Администратор ответит в этот же чат.\n\n"
        "✏️ *Введите ваше сообщение:*",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Режим поддержки
    if user_id in ADMIN_REPLY_BUFFER:
        text = update.message.text
        if not text:
            return
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📞 *ПОДДЕРЖКА*\n\n"
                 f"👤 {update.effective_user.first_name}\n"
                 f"🆔 ID: `{user_id}`\n"
                 f"📝 {text}",
            parse_mode="Markdown"
        )
        
        del ADMIN_REPLY_BUFFER[user_id]
        
        await update.message.reply_text(
            "✅ *Сообщение отправлено!*\n\nАдминистратор ответит сюда.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Ответ админа
    if user_id == str(ADMIN_ID) and update.message.reply_to_message:
        reply_text = update.message.text
        original = update.message.reply_to_message
        
        if original and "ID:" in original.text:
            match = re.search(r"ID: `(\d+)`", original.text)
            if match:
                target_id = match.group(1)
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"📞 *Ответ поддержки:*\n\n{reply_text}",
                    parse_mode="Markdown",
                    reply_markup=get_main_keyboard()
                )
                await update.message.reply_text(f"✅ Ответ отправлен.")
                return
    
    # Активный чат
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
        await update.message.reply_text(
            "🤫 Нажмите «🔍 Найти собеседника» чтобы начать общение.",
            reply_markup=get_main_keyboard()
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    
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
                     f"👤 @{username}\n\n"
                     f"Можете написать ему в личные сообщения.",
                parse_mode="Markdown"
            )
            await query.edit_message_text("✅ Username отправлен собеседнику.")
        else:
            await query.edit_message_text("❌ У вас нет username.\nУстановите его в настройках Telegram.")
    
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
        await query.edit_message_text(
            "⚠️ *Выберите причину жалобы:*",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    elif data.startswith("report_"):
        parts = data.split("_")
        if len(parts) >= 3:
            reason_key = parts[1]
            partner_id = parts[2]
            reason_text = {
                "insult": "Оскорбления",
                "spam": "Спам",
                "adult": "18+ контент"
            }.get(reason_key, "Другое")
            
            reports = load_reports()
            reports.append({
                "from": user_id,
                "on": partner_id,
                "reason": reason_text,
                "time": str(datetime.now())
            })
            save_reports(reports)
            
            await query.edit_message_text(
                f"⚠️ *Жалоба отправлена!*\n\nПричина: {reason_text}\nСпасибо за помощь!",
                parse_mode="Markdown"
            )
    
    elif data == "cancel_report":
        await query.edit_message_text("❌ Жалоба отменена.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤫 Анонимный чат запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
