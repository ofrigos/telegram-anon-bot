import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = "8903396597:AAEI3buQrnojm-k4ltqz3uZ3IdDiP6zakAk"
ADMIN_ID = 8117717482

WAITING_LIST = []
ACTIVE_CHATS = {}
REPORTS_FILE = "reports.json"

def save_data():
    with open("chats.json", "w") as f:
        json.dump({"waiting": WAITING_LIST, "active": ACTIVE_CHATS}, f)

def load_data():
    global WAITING_LIST, ACTIVE_CHATS
    if os.path.exists("chats.json"):
        with open("chats.json", "r") as f:
            data = json.load(f)
            WAITING_LIST = data.get("waiting", [])
            ACTIVE_CHATS = data.get("active", {})

def load_reports():
    if os.path.exists(REPORTS_FILE):
        with open(REPORTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_reports(reports):
    with open(REPORTS_FILE, "w") as f:
        json.dump(reports, f, indent=2)

load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤫 *Анонимный чат 1 на 1*\n\n"
        "• /find — найти собеседника\n"
        "• /stop — завершить диалог\n"
        "• /skip — найти нового\n"
        "• Во время чата доступны кнопки:\n"
        "   🔥 — запросить контакт\n"
        "   ⚠️ — пожаловаться\n\n"
        "Вы никому не покажете свой ID или имя.",
        parse_mode="Markdown"
    )

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    if user_id in ACTIVE_CHATS:
        await update.message.reply_text("❌ Вы уже в чате. Напишите /stop, чтобы выйти.")
        return

    if user_id in WAITING_LIST:
        await update.message.reply_text("⏳ Вы уже в очереди. Ожидайте...")
        return

    WAITING_LIST.append(user_id)
    save_data()
    await update.message.reply_text("🔍 Ищем собеседника... /stop — отменить.")

    if len(WAITING_LIST) >= 2:
        user1 = WAITING_LIST.pop(0)
        user2 = WAITING_LIST.pop(0)

        ACTIVE_CHATS[user1] = user2
        ACTIVE_CHATS[user2] = user1
        save_data()

        # Кнопки для чата
        chat_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Предложить контакт", callback_data="request_contact")],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data="report")]
        ])

        for uid in [user1, user2]:
            await context.bot.send_message(
                chat_id=int(uid),
                text="✅ *Собеседник найден!*\n\nМожете общаться анонимно.\n/stop — завершить чат.\n\n👇 Кнопки помощи:",
                reply_markup=chat_keyboard,
                parse_mode="Markdown"
            )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in WAITING_LIST:
        WAITING_LIST.remove(user_id)
        save_data()
        await update.message.reply_text("❌ Поиск отменён.")
        return

    if user_id in ACTIVE_CHATS:
        partner_id = ACTIVE_CHATS[user_id]

        del ACTIVE_CHATS[user_id]
        if partner_id in ACTIVE_CHATS:
            del ACTIVE_CHATS[partner_id]
        save_data()

        await context.bot.send_message(
            chat_id=int(partner_id),
            text="🚪 *Собеседник покинул чат.*\n/find — найти нового.",
            parse_mode="Markdown"
        )
        await update.message.reply_text("🚪 Чат завершён. /find — найти нового.")
        return

    await update.message.reply_text("❌ Вы не в чате. /find — начать поиск.")

async def skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in ACTIVE_CHATS:
        await update.message.reply_text("❌ Вы не в чате.")
        return

    partner_id = ACTIVE_CHATS[user_id]

    del ACTIVE_CHATS[user_id]
    if partner_id in ACTIVE_CHATS:
        del ACTIVE_CHATS[partner_id]

    await context.bot.send_message(
        chat_id=int(partner_id),
        text="🚪 *Собеседник ищет нового.*\n/find — найти нового.",
        parse_mode="Markdown"
    )

    WAITING_LIST.append(user_id)
    save_data()
    await update.message.reply_text("🔍 Ищем нового собеседника...")

    if len(WAITING_LIST) >= 2:
        user1 = WAITING_LIST.pop(0)
        user2 = WAITING_LIST.pop(0)

        ACTIVE_CHATS[user1] = user2
        ACTIVE_CHATS[user2] = user1
        save_data()

        chat_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Предложить контакт", callback_data="request_contact")],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data="report")]
        ])

        for uid in [user1, user2]:
            await context.bot.send_message(
                chat_id=int(uid),
                text="✅ *Новый собеседник найден!*",
                reply_markup=chat_keyboard,
                parse_mode="Markdown"
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data

    if user_id not in ACTIVE_CHATS:
        await query.edit_message_text("❌ Вы не в активном чате.")
        return

    partner_id = ACTIVE_CHATS[user_id]

    if data == "request_contact":
        # Запрос на обмен контактами
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, хочу ЛС", callback_data="accept_contact"),
                InlineKeyboardButton("❌ Нет", callback_data="decline_contact")
            ]
        ])

        await context.bot.send_message(
            chat_id=int(partner_id),
            text="🔥 *Собеседник хочет обменяться контактами!*\n\n"
                 "Если согласны — нажмите кнопку. Ваш username будет отправлен.\n"
                 "Если нет — просто проигнорируйте.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await query.edit_message_text("✅ Запрос на обмен контактами отправлен собеседнику.")

    elif data == "accept_contact":
        # Собеседник согласился — отправляем username
        sender = update.effective_user
        username = sender.username if sender.username else "скрыт"

        # Отправляем username тому, кто запросил
        partner = None
        for uid, pid in ACTIVE_CHATS.items():
            if pid == user_id:
                partner = uid
                break

        if partner:
            await context.bot.send_message(
                chat_id=int(partner),
                text=f"🔥 *Собеседник согласился на обмен!*\n\n"
                     f"👤 Его username: @{username}\n\n"
                     f"Можете написать ему в личные сообщения.",
                parse_mode="Markdown"
            )
            await query.edit_message_text(
                "✅ Вы согласились на обмен контактами.\n"
                "Ваш username отправлен собеседнику."
            )

    elif data == "decline_contact":
        # Отказ
        partner = None
        for uid, pid in ACTIVE_CHATS.items():
            if pid == user_id:
                partner = uid
                break

        if partner:
            await context.bot.send_message(
                chat_id=int(partner),
                text="❌ *Собеседник отказался обмениваться контактами.*",
                parse_mode="Markdown"
            )
        await query.edit_message_text("❌ Вы отказались от обмена контактами.")

    elif data == "report":
        # Жалоба на собеседника
        reports = load_reports()
        reports.append({
            "from_user": user_id,
            "on_user": partner_id,
            "reason": "Не указана",
            "time": str(update.effective_message.date)
        })
        save_reports(reports)

        # Уведомление админу
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ *НОВАЯ ЖАЛОБА!*\n\n"
                 f"От: {user_id}\n"
                 f"На: {partner_id}\n"
                 f"Время: {update.effective_message.date}\n\n"
                 f"Всего жалоб: {len(reports)}",
            parse_mode="Markdown"
        )

        await query.edit_message_text(
            "⚠️ *Жалоба отправлена администратору.*\n"
            "Если собеседник нарушает правила — он будет заблокирован.\n\n"
            "Спасибо за бдительность! 🤝",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id in ACTIVE_CHATS:
        partner_id = ACTIVE_CHATS[user_id]

        if update.message.text:
            await context.bot.send_message(
                chat_id=int(partner_id),
                text=f"💬 *Аноним:* {update.message.text}",
                parse_mode="Markdown"
            )
        elif update.message.photo:
            photo = update.message.photo[-1].file_id
            await context.bot.send_photo(
                chat_id=int(partner_id),
                photo=photo,
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
            "🤫 Чтобы начать общение, напишите /find\n\n"
            "Пока вы ни с кем не связаны."
        )

async def report_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        await update.message.reply_text("⛔ Нет прав.")
        return

    reports = load_reports()
    if not reports:
        await update.message.reply_text("📭 Жалоб пока нет.")
        return

    text = "⚠️ *Список жалоб:*\n\n"
    for i, r in enumerate(reports[-10:], 1):
        text += f"{i}. От: {r['from_user']}\n   На: {r['on_user']}\n   Время: {r['time']}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(ADMIN_ID):
        await update.message.reply_text("⛔ Нет прав.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Использование: /block USER_ID")
        return

    target_id = args[0]
    # Добавляем в чёрный список
    blacklist = load_blacklist()
    if target_id not in blacklist:
        blacklist.append(target_id)
        save_blacklist(blacklist)
        await update.message.reply_text(f"✅ Пользователь {target_id} заблокирован.")
    else:
        await update.message.reply_text(f"⚠️ Пользователь уже в чёрном списке.")

def load_blacklist():
    if os.path.exists("blacklist.json"):
        with open("blacklist.json", "r") as f:
            return json.load(f)
    return []

def save_blacklist(blacklist):
    with open("blacklist.json", "w") as f:
        json.dump(blacklist, f)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("skip", skip))
    app.add_handler(CommandHandler("reports", report_list))
    app.add_handler(CommandHandler("block", block_user))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("🤫 Анонимный чат 1 на 1 с жалобами и обменом контактами запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
