from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
import logging
from datetime import datetime
import threading
import time
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 7602989003
LANG_FILE = 'langs.txt'

class BotHandlers:

    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = str(update.message.from_user.id)
        lang = BotHandlers.get_user_language(user_id)
        if lang == 'ru':
            await BotHandlers.send_russian_rules(update.message)
        elif lang == 'en':
            await BotHandlers.send_english_rules(update.message)
        else:
            keyboard = [
                [InlineKeyboardButton("Русский", callback_data=f'lang_ru')],
                [InlineKeyboardButton("English", callback_data=f'lang_en')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("Выберите язык / Choose your language", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error in start handler: {e}")

    @staticmethod
    async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user_id = str(query.from_user.id)
        await query.answer()
        try:
            if query.data == 'lang_ru':
                BotHandlers.set_user_language(user_id, 'ru')
                await query.delete_message()
                await BotHandlers.send_russian_rules(query.message)
            elif query.data == 'lang_en':
                BotHandlers.set_user_language(user_id, 'en')
                await query.delete_message()
                await BotHandlers.send_english_rules(query.message)
        except Exception as e:
            logger.error(f"Error in language selection: {e}")

    @staticmethod
    async def send_russian_rules(message) -> None:
        rules_text = """Здравствуйте, уважаемый игрок. Напишите вашу жалобу по форме ниже, а также ознакомьтесь с правилами. Администрация ответит как можно быстрее!❤️

Правила подачи жалоб в бота:
1. Писать строго по форме ниже, нету формы - идет сначала предупреждение от администратора, потом отказ

*Форма подачи жалобы:*
1. Ник нарушителя
2. Дата нарушения
3. Доказательства (скриншот либо рек)

*Приметка:* если у вас жалоба связанная с чатом, у вас обязательно должен быть мод на время в чате - __ChatTime__ или __When Was That Again__

2. Оффтоп в этом боте карается баном на _1 день_
Оффтоп - например вы написали сюда не по поводу жалобы на игрока сервера.

3. Шутки/рофлы в сторону администрации бота карается баном на _5-15 дней_ (на усмотрение администратора)

4. Оскорбление администратора, его семьи или даже простое затрагивание родных карается баном на _20-40 дней_

5. Угрозы доксом сватом карается баном _навсегда_
"""
        try:
            await message.reply_text(rules_text, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            logger.error(f"Error sending Russian rules: {e}")

    @staticmethod
    async def send_english_rules(message) -> None:
        rules_text = """Hello, dear player. Please submit your complaint using the form below and read the rules. The administration will respond as soon as possible!❤️

Rules for submitting complaints to the bot:
1. You must follow the form below. No form — first a warning from the admin, then a refusal.

*Complaint submission form:*
1. Offender's nickname
2. Date of violation
3. Evidence (screenshot or recording)

*Note:* If your complaint is related to chat messages, you must have a time display mod like __ChatTime__ or __When Was That Again__

2. Off-topic messages in this bot will result in a _1-day ban_
Off-topic = anything not related to complaints about server players.

3. Jokes/trolling toward the bot administration will result in a _5–15 day ban_ (admin's discretion)

4. Insulting the administrator or their family, or even mentioning them, will result in a _20–40 day ban_

5. Threats of doxing or swatting will result in a _permanent ban_
"""
        try:
            await message.reply_text(rules_text, parse_mode='Markdown', reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            logger.error(f"Error sending English rules: {e}")

    @staticmethod
    async def forward_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            user = update.message.from_user
            user_info = f"Жалоба от @{user.username if user.username else 'N/A'} (ID: {user.id})"
            reply_text = "Ожидайте, с вами скоро свяжутся!\nС уважением, администратор SpidiBoost!"
            await update.message.reply_text(reply_text, reply_to_message_id=update.message.message_id)
            await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            await context.bot.send_message(chat_id=ADMIN_ID, text=user_info)
        except Exception as e:
            logger.error(f"Error forwarding complaint: {e}")

    @staticmethod
    def get_user_language(user_id: str) -> str:
        if not os.path.exists(LANG_FILE):
            return None
        with open(LANG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{user_id},"):
                    return line.split(',')[1]
        return None

    @staticmethod
    def set_user_language(user_id: str, lang: str) -> None:
        existing = []
        if os.path.exists(LANG_FILE):
            with open(LANG_FILE, 'r', encoding='utf-8') as f:
                existing = f.readlines()
        updated = False
        with open(LANG_FILE, 'w', encoding='utf-8') as f:
            for line in existing:
                if line.startswith(f"{user_id},"):
                    f.write(f"{user_id},{lang}\n")
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f"{user_id},{lang}\n")

def bot_status_monitor():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Бот работает...")
            time.sleep(60)
        except Exception as e:
            print(f"Error in status monitor: {e}")
            time.sleep(60)

async def main():
    try:
        status_thread = threading.Thread(target=bot_status_monitor, daemon=True)
        status_thread.start()

        app = ApplicationBuilder().token("7970063304:AAGfEoubfJgzVJ-ZmFp7Kwilaoh_TItDF1s").build()

        app.add_handler(CommandHandler("start", BotHandlers.start))
        app.add_handler(CallbackQueryHandler(BotHandlers.handle_language_selection))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, BotHandlers.forward_complaint))

        logger.info("Бот успешно запущен")
        await app.run_polling()
    except Exception as e:
        logger.error(f"Fatal error in bot startup: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
