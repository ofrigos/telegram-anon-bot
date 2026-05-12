import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8903396597:AAEI3buQrnojm-k4ltqz3uZ3IdDiP6zakAk"
ADMIN_ID = 8117717482

WAITING_LIST = []
ACTIVE_CHATS = {}
CHATS_FILE = "chats.json"

def save_chats():
    with open(CHATS_FILE, "w") as f:
        json.dump({"waiting": WAITING_LIST, "active": ACTIVE_CHATS}, f)

def load_chats():
    global WAITING_LIST, ACTIVE_CHATS
    if os.path.exists(CHATS_FILE):
        with open(CHATS_FILE, "r") as f:
            data = json.load(f)
            WAITING_LIST = data.get("waiting", [])
            ACTIVE_CHATS = data.get("active", {})

load_chats()

def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["🔍 Найти собеседника", "🚪 Завершить чат"],
        ["❓ Помощь"]
    ], resize_keyboard=True)

def get_chat_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Предложить контакт", callback_data="request_contact")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤫 *Анонимный чат*\n\n• Найди собеседника\n• Общайся анонимно\n• Предложи контакт если хочешь",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if not update.message:
        return
    
    text = update.message.text

    # ПОМОЩЬ
    if text == "❓ Помощь":
        await update.message.reply_text(
            "❓ *Помощь*\n\n"
            "• «🔍 Найти собеседника» — начать поиск\n"
            "• «🚪 Завершить чат» — выйти из диалога\n"
            "• 🔥 Предложить контакт — отправить свой username\n\n"
            "📞 По вопросам: @Ofrigo",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    # НАЙТИ СОБЕСЕДНИКА
    if text == "🔍 Найти собеседника":
        if user_id in ACTIVE_CHATS:
            await update.message.reply_text("❌ Вы уже в чате.")
            return
        if user_id in WAITING_LIST:
            await update.message.reply_text("⏳ Вы уже в очереди.")
            return
        
        WAITING_LIST.append(user_id)
        save_chats()
        await update.message.reply_text("🔍 Ищу собеседника...")
        
        if len(WAITING_LIST) >= 2:
            u1 = WAITING_LIST.pop(0)
            u2 = WAITING_LIST.pop(0)
            ACTIVE_CHATS[u1] = u2
            ACTIVE_CHATS[u2] = u1
            save_chats()
            
            await context.bot.send_message(int(u1), "✅ Собеседник найден!", reply_markup=get_chat_keyboard())
            await context.bot.send_message(int(u2), "✅ Собеседник найден!", reply_markup=get_chat_keyboard())
        return

    # ЗАВЕРШИТЬ ЧАТ
    if text == "🚪 Завершить чат":
        if user_id in WAITING_LIST:
            WAITING_LIST.remove(user_id)
            save_chats()
            await update.message.reply_text("❌ Поиск отменён.")
            return
        
        if user_id in ACTIVE_CHATS:
            partner = ACTIVE_CHATS[user_id]
            del ACTIVE_CHATS[user_id]
            if partner in ACTIVE_CHATS:
                del ACTIVE_CHATS[partner]
            save_chats()
            
            await context.bot.send_message(int(partner), "🚪 Собеседник покинул чат.")
            await update.message.reply_text("🚪 Чат завершён.")
            return
        
        await update.message.reply_text("❌ Вы не в чате.")
        return

    # ОБЫЧНОЕ СООБЩЕНИЕ
    if user_id in ACTIVE_CHATS:
        partner = ACTIVE_CHATS[user_id]
        try:
            if update.message.text:
                await context.bot.send_message(int(partner), update.message.text)
            elif update.message.photo:
                await context.bot.send_photo(int(partner), update.message.photo[-1].file_id)
            elif update.message.sticker:
                await context.bot.send_sticker(int(partner), update.message.sticker.file_id)
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {e}")
    else:
        await update.message.reply_text(
            "🤫 Нажмите «🔍 Найти собеседника»",
            reply_markup=get_main_keyboard()
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data
    
    # Запрос на отправку контакта
    if data == "request_contact":
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        # Показываем подтверждение
        confirm_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, отправить", callback_data="confirm_contact"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="cancel_contact")
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
    if data == "confirm_contact":
        if user_id not in ACTIVE_CHATS:
            await query.edit_message_text("❌ Вы не в чате.")
            return
        
        partner = ACTIVE_CHATS[user_id]
        username = update.effective_user.username
        
        if username:
            await context.bot.send_message(
                int(partner),
                f"🔥 *Собеседник хочет поделиться контактом!*\n\n👤 @{username}",
                parse_mode="Markdown"
            )
            await query.edit_message_text("✅ Username отправлен собеседнику!")
        else:
            await query.edit_message_text("❌ У вас нет username. Установите его в настройках Telegram.")
        return
    
    # Отмена
    if data == "cancel_contact":
        await query.edit_message_text("❌ Отправка отменена.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all))
    app.add_handler(MessageHandler(filters.PHOTO | filters.STICKER, handle_all))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🤫 Анонимный чат с подтверждением контакта запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
