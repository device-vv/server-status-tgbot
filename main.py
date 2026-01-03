import os
import logging
import io
from dotenv import load_dotenv
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, InputFile
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import database as db
import settings
from countries import find_countries, get_country_name_by_code, get_flag_emoji
from monitoring import run_monitoring_cycle
from converter import RemnavaveSubscriptionConverter
from ping import get_beautiful_report

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
MAX_SESSIONS = int(os.getenv('MAX_SESSIONS', 3))

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    LOGIN_PASSWORD,
    ADD_SERVER_COUNTRY_PROMPT,
    ADD_SERVER_COUNTRY_SELECT,
    ADD_SERVER_IP,
    REMOVE_SERVER_SELECT,
    CONVERT_GET_URL,
    CHECK_SERVER_SELECT,
    INTERVAL_SELECT,
) = range(8)


# --- Admin Authentication Decorator ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not db.is_admin(user_id):
            await update.message.reply_text(
                "⛔️ *Доступ запрещен.*\nПожалуйста, сначала войдите с помощью команды /login.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    await update.message.reply_text(
        "🤖 *Добро пожаловать в бот для мониторинга серверов!*\n\n"
        "Я могу следить за состоянием ваших серверов, а также конвертировать ссылки подписок VLESS.\n\n"
        "Для начала работы вам необходимо войти как администратор, используя команду `/login` с паролем.",
        parse_mode=ParseMode.MARKDOWN
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the login process."""
    user_id = update.effective_user.id
    logger.info(f"LOGIN: User {user_id} attempted login.")

    if db.is_admin(user_id):
        logger.info(f"LOGIN: User {user_id} is already logged in as admin.")
        await update.message.reply_text("✅ *Вы уже вошли в систему.*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    admin_count = db.get_admin_count()
    logger.info(f"LOGIN: Current admin count: {admin_count}, MAX_SESSIONS: {MAX_SESSIONS}")
    if admin_count >= MAX_SESSIONS:
        logger.warning(f"LOGIN: MAX_SESSIONS reached for user {user_id}. Blocking login.")
        await update.message.reply_text("⚠️ *Достигнуто максимальное количество сессий администраторов.*\nПопробуйте позже.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    args = context.args
    logger.info(f"LOGIN: Args received: {args}")
    # Compare the provided password with the ADMIN_PASSWORD from environment variables
    # Only compare if args is not empty to prevent IndexError
    password_match = False
    if len(args) == 1:
        password_match = (args[0] == ADMIN_PASSWORD)
    logger.info(f"LOGIN: Password match: {password_match}")

    if password_match:
        db.add_admin(user_id)
        logger.info(f"LOGIN: User {user_id} successfully logged in.")
        await update.message.reply_text(
            "✅ *Вход выполнен успешно!*\nТеперь у вас есть доступ к командам администратора."
        )
        return ConversationHandler.END
    else:
        logger.warning(f"LOGIN: User {user_id} failed login attempt with incorrect password.")
        await update.message.reply_text("❌ *Неверный пароль.*\nПожалуйста, попробуйте еще раз.", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

@admin_only
async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs out an admin."""
    user_id = update.effective_user.id
    db.remove_admin(user_id)
    await update.message.reply_text("✅ *Вы вышли из системы.*", parse_mode=ParseMode.MARKDOWN)


# --- Interval Settings ---
@admin_only
async def interval_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the interval selection conversation."""
    current_interval = settings.get_interval()
    
    text = f"⚙️ *Настройка интервала проверки*\n\n" \
           f"Текущий интервал: *{current_interval} секунд*.\n\n" \
           f"Выберите новую частоту проверки:"
    
    keyboard = [
        [InlineKeyboardButton("Частая (1 минута)", callback_data="interval_frequent")],
        [InlineKeyboardButton("Средняя (5 минут)", callback_data="interval_medium")],
        [InlineKeyboardButton("Медленная (15 минут)", callback_data="interval_slow")],
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return INTERVAL_SELECT

async def interval_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles interval selection."""
    query = update.callback_query
    await query.answer()
    
    preset = query.data.split('_')[1] # frequent, medium, or slow
    
    try:
        new_interval = settings.set_interval(preset)
        
        # Reschedule the job
        job_queue = context.job_queue
        # Remove old job(s)
        current_jobs = job_queue.get_jobs_by_name("monitoring_job")
        for job in current_jobs:
            job.schedule_removal()
        
        # Add new job with the new interval
        job_queue.run_repeating(run_monitoring_cycle, interval=new_interval, first=5, name="monitoring_job")
        
        await query.edit_message_text(
            text=f"✅ *Интервал проверки обновлен до {new_interval} секунд.*",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except (ValueError, Exception) as e:
        logger.error(f"Ошибка при смене интервала: {e}")
        await query.edit_message_text(
            text="❌ *Произошла ошибка при смене интервала.*",
            parse_mode=ParseMode.MARKDOWN
        )

    return ConversationHandler.END


# --- Converter (Conversation Handler) ---
@admin_only
async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the converter conversation."""
    await update.message.reply_text(
        "Пожалуйста, отправьте мне ссылку на подписку VLESS, которую вы хотите конвертировать."
    )
    return CONVERT_GET_URL

async def convert_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the subscription URL and processes it."""
    sub_url = update.message.text.strip()
    if not sub_url.startswith('http'):
        await update.message.reply_text("❌ Похоже, это недействительная ссылка. Пожалуйста, отправьте корректный URL.")
        return CONVERT_GET_URL

    await update.message.reply_text("⏳ *Начинаю конвертацию...*\nЭто может занять до минуты.", parse_mode=ParseMode.MARKDOWN)

    try:
        converter = RemnavaveSubscriptionConverter(sub_url, verbose=False)
        vless_keys = converter.convert_and_get_keys()

        if not vless_keys:
            await update.message.reply_text("❌ *Не удалось извлечь ключи VLESS из этой подписки.*\nПроверьте ссылку или попробуйте позже.", parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END
        
        await update.message.reply_text(f"✅ *Успешно найдено {len(vless_keys)} ключей!*", parse_mode=ParseMode.MARKDOWN)

        keys_text = "\n\n".join(vless_keys)

        if len(keys_text) > 4000:
            with io.BytesIO(keys_text.encode('utf-8')) as f:
                f.name = 'vless_keys.txt'
                await update.message.reply_document(
                    document=f,
                    caption="Ключи в текстовом файле, так как их слишком много."
                )
        else:
            await update.message.reply_text(f"```{keys_text}```", parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"Ошибка при конвертации: {e}")
        await update.message.reply_text("Произошла внутренняя ошибка при конвертации. Пожалуйста, попробуйте позже.")

    return ConversationHandler.END


# --- Server Management (Conversation Handlers) ---

# Add Server
@admin_only
async def add_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the add server conversation by asking for a country name."""
    await update.message.reply_text(
        "Введите название страны, в которой находится сервер (например, 'Германия' или 'Finland')."
    )
    return ADD_SERVER_COUNTRY_PROMPT

async def add_server_country_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's text input for the country name."""
    country_query = update.message.text
    
    matches = find_countries(country_query)

    if not matches:
        await update.message.reply_text(
            f"😕 Страна по запросу '{country_query}' не найдена. Попробуйте еще раз."
        )
        return ADD_SERVER_COUNTRY_PROMPT

    if len(matches) == 1:
        country = matches[0]
        country_code = country["code"]
        context.user_data['selected_country'] = country_code
        
        country_name = get_country_name_by_code(country_code, lang='ru')
        flag_emoji = get_flag_emoji(country_code)
        
        await update.message.reply_text(
            f"Выбрана страна: {flag_emoji} *{country_name}*\n\n"
            f"Теперь введите IP-адрес сервера:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ADD_SERVER_IP
    
    if len(matches) > 5:
        await update.message.reply_text(
            "Найдено слишком много совпадений. Пожалуйста, уточните ваш запрос."
        )
        return ADD_SERVER_COUNTRY_PROMPT

    # 2 to 5 matches, ask user to clarify
    keyboard = []
    for country in matches:
        country_code = country["code"]
        country_name = country["ru"]
        flag_emoji = get_flag_emoji(country_code)
        keyboard.append([
            InlineKeyboardButton(
                f"{flag_emoji} {country_name}",
                callback_data=f"country_{country_code}"
            )
        ])
    
    await update.message.reply_text(
        "Найдено несколько совпадений. Пожалуйста, выберите один из вариантов:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_SERVER_COUNTRY_SELECT


async def add_server_country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's selection from the clarification keyboard."""
    query = update.callback_query
    await query.answer()
    
    country_code = query.data.split('_')[1]
    context.user_data['selected_country'] = country_code
    
    country_name = get_country_name_by_code(country_code, lang='ru')
    flag_emoji = get_flag_emoji(country_code)
    
    await query.edit_message_text(
        text=f"Выбрана страна: {flag_emoji} *{country_name}*\n\n"
             f"Теперь введите IP-адрес сервера:",
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_SERVER_IP

async def add_server_ip_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ip_address = update.message.text.strip()
    country_code = context.user_data.get('selected_country')

    import re
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
        await update.message.reply_text("❌ *Неверный формат IP-адреса.*\nПожалуйста, введите действительный IPv4-адрес.", parse_mode=ParseMode.MARKDOWN)
        return ADD_SERVER_IP

    # --- New Naming Logic ---
    base_name = get_country_name_by_code(country_code, 'ru')
    existing_count = db.count_servers_by_country(country_code)
    
    if existing_count > 0:
        new_name = f"{base_name}-{existing_count + 1}"
    else:
        new_name = base_name
    
    logger.info(f"ADD_SERVER: Received IP: {ip_address}. Determined name: '{new_name}'")

    if db.add_server(ip_address, country_code, new_name):
        await update.message.reply_text(f"✅ Сервер '{new_name}' (`{ip_address}`) успешно добавлен!", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ Сервер с IP `{ip_address}` уже отслеживается.", parse_mode=ParseMode.MARKDOWN)

    context.user_data.clear()
    return ConversationHandler.END

# Remove Server
@admin_only
async def remove_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("REMOVE_SERVER: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("REMOVE_SERVER: No servers found in DB.")
        await update.message.reply_text("*Нет серверов для удаления.*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    keyboard = []
    for ip, name, _, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        label = f"{flag_emoji} {name} ({ip})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"remove_{ip}")])

    await update.message.reply_text(
        "*Выберите сервер для удаления:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return REMOVE_SERVER_SELECT

async def remove_server_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    ip_to_remove = query.data.split('_')[1]
    logger.info(f"REMOVE_SERVER: Attempting to remove IP: {ip_to_remove}")
    
    if db.remove_server(ip_to_remove):
        await query.edit_message_text(text=f"✅ Сервер `{ip_to_remove}` был удален.", parse_mode=ParseMode.MARKDOWN)
    else:
        await query.edit_message_text(text=f"⚠️ Не удалось найти сервер `{ip_to_remove}`. Возможно, он уже был удален.", parse_mode=ParseMode.MARKDOWN)
        
    return ConversationHandler.END

# Check Server
@admin_only
async def check_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("CHECK_SERVER: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("CHECK_SERVER: No servers found in DB.")
        await update.message.reply_text("*Нет серверов для проверки.*", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    keyboard = []
    for ip, name, _, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        label = f"{flag_emoji} {name} ({ip})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"check_{ip}")])

    await update.message.reply_text(
        "*Выберите сервер для мгновенной проверки:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return CHECK_SERVER_SELECT

async def check_server_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the server check, with extensive logging for debugging."""
    query = update.callback_query
    await query.answer()
    
    ip_to_check = query.data.split('_')[1]
    logger.info(f"--- CHECK COMMAND DIAGNOSTICS for IP: {ip_to_check} ---")
    
    await query.edit_message_text(text=f"*Проверяю* `{ip_to_check}`...", parse_mode=ParseMode.MARKDOWN)
    
    server_details = db.get_server_details(ip_to_check)
    logger.info(f"1. Raw server_details from DB: {server_details}")
    
    display_name = "Неизвестно"
    flag_emoji = "🏳️"

    if server_details:
        ip, name, status, country_code = server_details
        logger.info(f"2. Extracted details -> Name: '{name}', Country Code: '{country_code}'")
        display_name = name # Use the unique name from the DB
        flag_emoji = get_flag_emoji(country_code)
    else:
        logger.warning("1a. server_details from DB is None.")

    logger.info(f"5. Final values for report -> IP: {ip_to_check}, Name: {display_name}, Flag: {flag_emoji}")
    report = await get_beautiful_report(ip_to_check, display_name, flag_emoji)
    logger.info(f"6. Generated report string:\n{report}")
    logger.info("--- END CHECK COMMAND DIAGNOSTICS ---")

    await query.edit_message_text(text=report, parse_mode=ParseMode.MARKDOWN)
        
    return ConversationHandler.END


@admin_only
async def list_servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all monitored servers and their status."""
    logger.info("LIST_SERVERS: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("LIST_SERVERS: No servers found in DB.")
        await update.message.reply_text("*На данный момент нет отслеживаемых серверов.*", parse_mode=ParseMode.MARKDOWN)
        return

    message = "📋 *Отслеживаемые серверы:*\n\n"
    for ip, name, status, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        
        status_translation = {'UP': 'В сети', 'DOWN': 'Не в сети', 'UNKNOWN': 'Неизвестно'}
        status_text = status_translation.get(status, status)
        status_emoji = {'UP': '✅', 'DOWN': '❌', 'UNKNOWN': '❓'}.get(status, '❓')
        message += f"{flag_emoji} *{name}* (`{ip}`)\n*Статус:* {status_emoji} {status_text}\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the current conversation."""
    await update.message.reply_text("Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END

async def post_init(application: Application):
    """Post-initialization function to set bot commands."""
    commands = [
        BotCommand("start", "▶️ Запустить бота"),
        BotCommand("login", "🔑 Войти в систему"),
        BotCommand("logout", "🚪 Выйти"),
        BotCommand("addserver", "➕ Добавить сервер"),
        BotCommand("removeserver", "➖ Удалить сервер"),
        BotCommand("listservers", "📋 Список серверов"),
        BotCommand("check", "🔎 Проверить сервер"),
        BotCommand("convert", "🔄 Конвертировать подписку"),
        BotCommand("interval", "⚙️ Настроить интервал"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Run the bot."""
    # Initialize DB
    db.initialize_db()
    
    # Get the initial interval from settings
    initial_interval = settings.get_interval()
    logger.info(f"Запуск с интервалом мониторинга: {initial_interval} секунд.")

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # --- Job Queue for Monitoring ---
    job_queue = application.job_queue
    job_queue.run_repeating(run_monitoring_cycle, interval=initial_interval, first=5, name="monitoring_job")

    # --- Conversation Handlers ---
    add_server_conv = ConversationHandler(
        entry_points=[CommandHandler("addserver", add_server_start)],
        states={
            ADD_SERVER_COUNTRY_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_country_received)],
            ADD_SERVER_COUNTRY_SELECT: [CallbackQueryHandler(add_server_country_selected, pattern="^country_")],
            ADD_SERVER_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_server_ip_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True
    )

    remove_server_conv = ConversationHandler(
        entry_points=[CommandHandler("removeserver", remove_server_start)],
        states={
            REMOVE_SERVER_SELECT: [CallbackQueryHandler(remove_server_selected, pattern="^remove_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    check_server_conv = ConversationHandler(
        entry_points=[CommandHandler("check", check_server_start)],
        states={
            CHECK_SERVER_SELECT: [CallbackQueryHandler(check_server_selected, pattern="^check_")],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    convert_conv = ConversationHandler(
        entry_points=[CommandHandler("convert", convert_start)],
        states={
            CONVERT_GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_url_received)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    
    interval_conv = ConversationHandler(
        entry_points=[CommandHandler("interval", interval_start)],
        states={
            INTERVAL_SELECT: [CallbackQueryHandler(interval_selected, pattern="^interval_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("listservers", list_servers_command))
    
    # Add conversation handlers
    application.add_handler(add_server_conv)
    application.add_handler(remove_server_conv)
    application.add_handler(check_server_conv)
    application.add_handler(convert_conv)
    application.add_handler(interval_conv)

    # Run the bot until the user presses Ctrl-C
    logger.info("Бот запускается...")
    application.run_polling()

if __name__ == "__main__":
    main()
