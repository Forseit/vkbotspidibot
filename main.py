import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio
from datetime import datetime, timedelta
import os
import re
import pytz

# Конфигурация
BOT_TOKEN = "7970063304:AAGfEoubfJgzVJ-ZmFp7Kwilaoh_TItDF1s"
ADMIN_ID = 7602989003  # Ваш ID
GROUP_ID = -1002441905675  # ID группы, куда пересылать сообщения
BLOCK_FILE = "blocks.txt"
LANG_FILE = "lang.txt"
MOSCOW_TZ = pytz.timezone('Europe/Moscow')  # Московский часовой пояс

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Клавиатура выбора языка
def get_lang_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Русский", callback_data="ru"),
            InlineKeyboardButton("English", callback_data="en"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Сообщения для языков
MESSAGES = {
    "ru": {
        "welcome": "Здравствуйте, уважаемый игрок. Напишите вашу жалобу по форме ниже, а также ознакомьтесь с правилами. Администрация ответит как можно быстрее!❤️\n\n"
        "**Правила подачи жалоб в бота:**\n"
        "1. Писать строго по форме ниже, нету формы - идет сначала предупреждение от администратора, потом отказ\n\n"
        "*Форма подачи жалобы:*\n"
        "```\n"
        "1. Ник нарушителя\n"
        "2. Дата нарушения\n"
        "3. Доказательства (скриншот либо рек)\n"
        "```\n"
        "*Приметка:* если у вас жалоба связанная с чатом, у вас обязательно должен быть мод на время в чате - __ChatTime__ или __When Was That Again__\n"
        "2. Оффтоп в этом боте карается баном на _1 день_\n"
        "Оффтоп - например вы написали сюда не по поводу жалобы на игрока сервера.\n"
        "3. Шутки/рофлы в сторону администрации бота карается баном на _5-15 дней_ (на усмотрение администратора)\n"
        "4. Оскорбление администратора, его семьи или даже простое затрагивание родных карается баном на _20-40 дней_\n"
        "5. Угрозы доксом сватом карается баном _навсегда_",
        "blocked": "```\nВы в Черном Списке бота.\nПричина: {reason}\nЗаканчивается в {time}```\n",
        "blocked_perm": "```\nВы в Черном Списке бота.\nПричина: {reason}\nЗаканчивается никогда```\n",
        "no_permission": "⛔ У вас недостаточно прав для выполнения этой команды",
        "user_not_found": "❌ Пользователь не найден",
    },
    "en": {
        "welcome": "Hello dear player. Please write your complaint according to the form below and read the rules. Administration will respond as soon as possible!❤️\n\n"
        "**Complaint Rules:**\n"
        "1. Write strictly according to the form below. If there is no form - first warning, then refusal.\n\n"
        "*Complaint form:*\n"
        "```\n"
        "1. Nickname of violator\n"
        "2. Date of violation\n"
        "3. Evidence (screenshot or video)\n"
        "```\n"
        "*Note:* if your complaint is related to chat, you must have a mod showing time in chat - __ChatTime__ or __When Was That Again__\n"
        "2. Off-topic messages here result in a _1 day ban_\n"
        "Off-topic - for example, you wrote here not about a complaint about a player of the server.\n"
        "3. Jokes/insults towards administration result in a _5-15 days ban_\n"
        "4. Insulting administration's family results in a _20-40 days ban_\n"
        "5. Threats of doxing or swatting result in a _permanent ban_",
        "blocked": "```\nYou are in the bot's Blacklist.\nReason: {reason}\nEnds at {time} MSK```\n",
        "blocked_perm": "```\nYou are in the bot's Blacklist.\nReason: {reason}\nEnds never```\n",
        "no_permission": "⛔ You don't have permission to use this command",
        "user_not_found": "❌ User not found",
    },
}

# Получение текущего времени по Москве
def get_moscow_time():
    return datetime.now(MOSCOW_TZ)

# Форматирование времени для вывода
def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " по Мск"

# Проверка прав администратора
def is_admin(user_id):
    return user_id == ADMIN_ID

# Проверка блокировки
def is_blocked(user_id):
    if not os.path.exists(BLOCK_FILE):
        return False

    current_time = get_moscow_time()
    with open(BLOCK_FILE, "r") as f:
        for line in f.readlines():
            if not line.strip():
                continue

            parts = line.strip().split(",")
            if len(parts) >= 2 and int(parts[0]) == user_id:
                if parts[1] == "permament":
                    return True
                else:
                    try:
                        end_time = datetime.strptime(parts[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW_TZ)
                        return current_time < end_time
                    except:
                        return True
    return False

# Получение информации о блокировке
def get_block_info(user_id):
    if not os.path.exists(BLOCK_FILE):
        return None

    with open(BLOCK_FILE, "r") as f:
        for line in f.readlines():
            if not line.strip():
                continue

            parts = line.strip().split(",")
            if len(parts) >= 2 and int(parts[0]) == user_id:
                return {
                    "reason": parts[2] if len(parts) > 2 else "Нарушение правил",
                    "end_time": parts[1] if parts[1] != "permament" else None
                }
    return None

# Парсинг времени блокировки
def parse_time(time_str):
    if time_str.lower() == "permament":
        return "permament"

    time_dict = {
        'd': 86400,  # дни
        'h': 3600,   # часы
        'm': 60,     # минуты
        's': 1,      # секунды
        'y': 31536000  # годы (примерно)
    }

    total_seconds = 0
    matches = re.findall(r'(\d+)([dhmsy])', time_str.lower())

    if not matches:
        return None

    for amount, unit in matches:
        total_seconds += int(amount) * time_dict[unit]

    if total_seconds <= 0:
        return None

    end_time = get_moscow_time() + timedelta(seconds=total_seconds)
    return end_time.strftime("%Y-%m-%d %H:%M:%S")

# Получение языка пользователя
def get_user_lang(user_id):
    if not os.path.exists(LANG_FILE):
        return None
    with open(LANG_FILE, "r") as f:
        for line in f.readlines():
            parts = line.strip().split(",")
            if len(parts) == 2 and int(parts[0]) == user_id:
                return parts[1]
    return None

# Сохранение языка пользователя
def save_user_lang(user_id, lang):
    entries = []
    if os.path.exists(LANG_FILE):
        with open(LANG_FILE, "r") as f:
            entries = [line.strip() for line in f.readlines() if line.strip()]

    # Удаляем старую запись, если есть
    entries = [e for e in entries if not e.startswith(f"{user_id},")]
    entries.append(f"{user_id},{lang}")

    with open(LANG_FILE, "w") as f:
        f.write("\n".join(entries))

# Обновление файла блокировок
def update_block_file():
    if not os.path.exists(BLOCK_FILE):
        return

    current_time = get_moscow_time()
    updated_lines = []

    with open(BLOCK_FILE, "r") as f:
        for line in f.readlines():
            if not line.strip():
                continue

            parts = line.strip().split(",")
            if len(parts) >= 2:
                if parts[1] != "permament":
                    try:
                        end_time = datetime.strptime(parts[1], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW_TZ)
                        if current_time < end_time:
                            updated_lines.append(line.strip())
                    except:
                        pass
                else:
                    updated_lines.append(line.strip())

    with open(BLOCK_FILE, "w") as f:
        f.write("\n".join(updated_lines))

# Обработчик команды /id
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        lang = get_user_lang(update.effective_user.id) or "ru"
        await update.message.reply_text(MESSAGES[lang]["no_permission"])
        return

    if not context.args:
        await update.message.reply_text("Использование: /id @username")
        return

    username = context.args[0].lstrip('@')
    try:
        # Пробуем получить пользователя по username
        user = await context.bot.get_chat(f"@{username}")
        await update.message.reply_text(f"ID у {user.full_name or 'N/A'} (@{user.username or 'N/A'}): {user.id}")
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        # Если не получилось по username, пробуем по ID (если ввели число)
        if username.isdigit():
            try:
                user = await context.bot.get_chat(int(username))
                await update.message.reply_text(f"ID у {user.full_name or 'N/A'} (@{user.username or 'N/A'}): {user.id}")
            except Exception as e:
                logger.error(f"Error getting user by ID: {e}")
                lang = get_user_lang(update.effective_user.id) or "ru"
                await update.message.reply_text(MESSAGES[lang]["user_not_found"])
        else:
            lang = get_user_lang(update.effective_user.id) or "ru"
            await update.message.reply_text(MESSAGES[lang]["user_not_found"])

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_blocked(user_id):
        block_info = get_block_info(user_id)
        lang = get_user_lang(user_id) or "ru"

        if block_info["end_time"] is None:
            blocked_msg = MESSAGES[lang]["blocked_perm"].format(reason=block_info["reason"])
        else:
            try:
                dt = datetime.strptime(block_info["end_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW_TZ)
                time_str = format_time(dt)
            except:
                time_str = block_info["end_time"]

            blocked_msg = MESSAGES[lang]["blocked"].format(
                reason=block_info["reason"],
                time=time_str
            )
        await update.message.reply_text(blocked_msg, parse_mode="Markdown")
        return

    lang = get_user_lang(user_id)
    if lang:
        await update.message.reply_text(MESSAGES[lang]["welcome"], parse_mode="Markdown")
    else:
        await update.message.reply_text("Выберите язык / Choose language", reply_markup=get_lang_keyboard())

# Обработчик нажатия кнопки языка
async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = query.data

    save_user_lang(user_id, lang)
    await query.edit_message_text(MESSAGES[lang]["welcome"], parse_mode="Markdown")

# Обработчик сообщений от пользователя
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_blocked(user_id):
        block_info = get_block_info(user_id)
        lang = get_user_lang(user_id) or "ru"

        if block_info["end_time"] is None:
            blocked_msg = MESSAGES[lang]["blocked_perm"].format(reason=block_info["reason"])
        else:
            try:
                dt = datetime.strptime(block_info["end_time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW_TZ)
                time_str = format_time(dt)
            except:
                time_str = block_info["end_time"]

            blocked_msg = MESSAGES[lang]["blocked"].format(
                reason=block_info["reason"],
                time=time_str
            )
        await update.message.reply_text(blocked_msg, parse_mode="Markdown")
        return

    # Пересылка сообщения в группу
    if update.message.chat.type == "private" and GROUP_ID:
        # Сохраняем связь между сообщением в группе и пользователем
        forwarded_msg = await context.bot.forward_message(
            chat_id=GROUP_ID,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
        # Сохраняем информацию о пересылке в контексте
        context.chat_data[forwarded_msg.message_id] = user_id

# Обработчик ответа админа
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not update.message.reply_to_message:
        return

    # Получаем ID пользователя из сохраненных данных
    user_id = context.chat_data.get(update.message.reply_to_message.message_id)

    if not user_id:
        # Если не нашли по message_id, пробуем получить из пересланного сообщения
        if update.message.reply_to_message.forward_from:
            user_id = update.message.reply_to_message.forward_from.id
        else:
            return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=update.message.text
        )
    except Exception as e:
        logger.error(f"Error sending message to user {user_id}: {e}")
        await update.message.reply_text("❌ Не удалось отправить сообщение пользователю")

# Команда /block
async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        lang = get_user_lang(update.effective_user.id) or "ru"
        await update.message.reply_text(MESSAGES[lang]["no_permission"])
        return

    if not context.args:
        await update.message.reply_text("Использование:\n/block add/rem id время(1h5m/permament) причина")
        return

    action = context.args[0].lower()
    if action not in ["add", "rem", "list"]:
        await update.message.reply_text("Неизвестное действие. Используйте add, rem или list")
        return

    if action == "list":
        update_block_file()

        if not os.path.exists(BLOCK_FILE):
            await update.message.reply_text("Черный список пуст.")
            return

        with open(BLOCK_FILE, "r") as f:
            blocked_users = []
            for line in f.readlines():
                if not line.strip():
                    continue

                parts = line.strip().split(",")
                if len(parts) >= 3:
                    blocked_users.append({
                        "id": parts[0],
                        "time": parts[1],
                        "reason": parts[2]
                    })

        if not blocked_users:
            await update.message.reply_text("Черный список пуст.")
            return

        response = "**Черный список:**\n"
        for i, user in enumerate(blocked_users, 1):
            if user["time"] == "permament":
                response += f"{i}. ID {user['id']} - навсегда, причина: {user['reason']}\n"
            else:
                try:
                    dt = datetime.strptime(user["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MOSCOW_TZ)
                    response += f"{i}. ID {user['id']} - до {format_time(dt)}, причина: {user['reason']}\n"
                except:
                    response += f"{i}. ID {user['id']} - до {user['time']}, причина: {user['reason']}\n"

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Укажите ID пользователя.")
        return

    try:
        target_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Неверный ID пользователя.")
        return

    if action == "add":
        if len(context.args) < 4:
            await update.message.reply_text("Укажите время (например 1h5m или permament) и причину.")
            return

        time_arg = context.args[2].lower()
        reason = " ".join(context.args[3:])

        # Парсим время
        if time_arg == "permament":
            end_time = "permament"
        else:
            end_time = parse_time(time_arg)
            if not end_time:
                await update.message.reply_text("Неверный формат времени. Пример: 1h5m (1 час 5 минут)")
                return

        # Проверяем, не заблокирован ли уже пользователь
        if is_blocked(target_id):
            await update.message.reply_text(f"Пользователь {target_id} уже в черном списке.")
            return

        # Добавляем в файл
        with open(BLOCK_FILE, "a") as f:
            f.write(f"{target_id},{end_time},{reason}\n")

        await update.message.reply_text(f"Пользователь {target_id} добавлен в черный список. Причина: {reason}")

    elif action == "rem":
        update_block_file()

        if not os.path.exists(BLOCK_FILE):
            await update.message.reply_text("Черный список пуст.")
            return

        with open(BLOCK_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        updated_lines = []
        removed = False

        for line in lines:
            parts = line.split(",")
            if parts[0] == str(target_id):
                removed = True
            else:
                updated_lines.append(line)

        if not removed:
            await update.message.reply_text(f"Пользователь {target_id} не в черном списке.")
            return

        with open(BLOCK_FILE, "w") as f:
            f.write("\n".join(updated_lines))

        await update.message.reply_text(f"Пользователь {target_id} удален из черного списка.")

# Функция для периодического сообщения в консоль
async def print_status(context: ContextTypes.DEFAULT_TYPE):
    while True:
        logger.info(f"[{get_moscow_time().strftime('%H:%M:%S')}] Бот работает...")
        await asyncio.sleep(60)

# Функция для обновления времени блокировок
async def update_block_times(context: ContextTypes.DEFAULT_TYPE):
    while True:
        update_block_file()
        await asyncio.sleep(60)

def main():
    # Создаем Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CallbackQueryHandler(lang_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.REPLY & filters.Chat(GROUP_ID), handle_admin_reply))
    application.add_handler(CommandHandler("block", block_command))

    # Запускаем бота
    application.job_queue.run_repeating(print_status, interval=60, first=0)
    application.job_queue.run_repeating(update_block_times, interval=60, first=0)
    application.run_polling()

if __name__ == "__main__":
    main()
