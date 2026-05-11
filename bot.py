import json
import os
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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

# Временное хранилище для ответов админа
admin_reply_buffer = {}

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
            await update.message.reply_text(
                "🤫 *Анонимный вопрос*\n\n"
                "Напишите ваше сообщение. Оно будет отправлено анонимно.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Ссылка недействительна")
        return

    if user_id not in user_links:
        user_links[user_id] = secrets.token_urlsafe(16)
        save_json(LINKS_FILE, user_links)

    token = user_links[user_id]
    link = f"https://t.me/{BOT_USERNAME}?start=ask_{token}"

    await update.message.reply_text(
        f"🔗 *Ваша ссылка для анонимных вопросов:*\n\n"
        f"`{link}`\n\n"
        f"Отправьте её кому угодно. Они смогут задать вам вопрос.",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = str(update.effective_user.id)
    text = update.message.text

    # Если пользователь отвечает админу (обычный ответ)
    if sender_id in dialogs:
        target_id = dialogs[sender_id]
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"✉️ *Ответ:*\n\n{text}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Ответ отправлен.")
        return

    # Если пользователь задаёт новый вопрос через ссылку
    if "reply_to" in context.user_data:
        target_id = context.user_data["reply_to"]
        
        # Сохраняем диалог
        dialogs[sender_id] = target_id
        dialogs[target_id] = sender_id
        save_json(DIALOGS_FILE, dialogs)
        
        # Создаём кнопку для ответа
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

    # Если неизвестный отправитель
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
        
        # Сохраняем, кому нужно ответить
        admin_reply_buffer[user_id] = questioner_id
        
        # Редактируем сообщение, убираем кнопку
        await query.edit_message_text(
            text=query.message.text + "\n\n✏️ *Напишите ваш ответ ниже:*",
            parse_mode="Markdown"
        )
        
        # Отправляем отдельное сообщение-подсказку
        await context.bot.send_message(
            chat_id=user_id,
            text="💬 Введите текст ответа. Он будет отправлен анонимно."
        )
    
    elif data.startswith("close_"):
        await query.edit_message_text(
            text=query.message.text + "\n\n✅ *Диалог закрыт*",
            parse_mode="Markdown"
        )

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответа администратора на кнопку"""
    user_id = str(update.effective_user.id)
    text = update.message.text
    
    if user_id in admin_reply_buffer:
        questioner_id = admin_reply_buffer[user_id]
        
        # Отправляем ответ пользователю
        await context.bot.send_message(
            chat_id=int(questioner_id),
            text=f"✉️ *Ответ:*\n\n{text}",
            parse_mode="Markdown"
        )
        
        # Подтверждение админу
        await update.message.reply_text("✅ Ответ отправлен анонимно.")
        
        # Удаляем из буфера
        del admin_reply_buffer[user_id]
    else:
        # Обычное сообщение от админа (не через кнопку)
        if user_id == str(ADMIN_ID) and user_id in dialogs:
            target_id = dialogs[user_id]
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f"✉️ *Сообщение:*\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("✅ Отправлено.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_ID), admin_reply))
    
    print("🤖 Бот с кнопками запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
