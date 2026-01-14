import os
import logging
import io
import re
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
from localization import get_user_language, get_translation

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
            lang = get_user_language(update, context)
            await update.message.reply_text(
                get_translation(lang, 'access_denied'),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# --- Language Selection ---
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a language selection menu."""
    lang = get_user_language(update, context)
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
    ]
    await update.message.reply_text(
        get_translation(lang, 'language_select'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles language selection and saves it to DB for admins."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    lang_code = query.data.split('_')[1]
    context.user_data['language'] = lang_code

    # If the user is an admin, save the preference to the database
    if db.is_admin(user_id):
        db.set_admin_language(user_id, lang_code)
    
    await query.edit_message_text(
        text=get_translation(lang_code, 'language_selected'),
        parse_mode=ParseMode.MARKDOWN
    )


# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message."""
    lang = get_user_language(update, context)
    await update.message.reply_text(
        get_translation(lang, 'welcome'),
        parse_mode=ParseMode.MARKDOWN
    )

async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the login process."""
    user_id = update.effective_user.id
    lang = get_user_language(update, context)
    logger.info(f"LOGIN: User {user_id} attempted login.")

    if db.is_admin(user_id):
        logger.info(f"LOGIN: User {user_id} is already logged in as admin.")
        await update.message.reply_text(get_translation(lang, 'already_logged_in'), parse_mode=ParseMode.MARKDOWN)
        return

    admin_count = db.get_admin_count()
    logger.info(f"LOGIN: Current admin count: {admin_count}, MAX_SESSIONS: {MAX_SESSIONS}")
    if admin_count >= MAX_SESSIONS:
        logger.warning(f"LOGIN: MAX_SESSIONS reached for user {user_id}. Blocking login.")
        await update.message.reply_text(get_translation(lang, 'max_sessions_reached'), parse_mode=ParseMode.MARKDOWN)
        return

    args = context.args
    logger.info(f"LOGIN: Args received: {args}")
    
    password_match = False
    if len(args) == 1:
        password_match = (args[0] == ADMIN_PASSWORD)
    logger.info(f"LOGIN: Password match: {password_match}")

    if password_match:
        db.add_admin(user_id, language=lang) # Save language on login
        logger.info(f"LOGIN: User {user_id} successfully logged in.")
        await update.message.reply_text(get_translation(lang, 'login_success'))
    else:
        logger.warning(f"LOGIN: User {user_id} failed login attempt with incorrect password.")
        await update.message.reply_text(get_translation(lang, 'login_failed'), parse_mode=ParseMode.MARKDOWN)


@admin_only
async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logs out an admin."""
    user_id = update.effective_user.id
    lang = get_user_language(update, context)
    db.remove_admin(user_id)
    await update.message.reply_text(get_translation(lang, 'logout_success'), parse_mode=ParseMode.MARKDOWN)


# --- Interval Settings ---
@admin_only
async def interval_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the interval selection conversation."""
    lang = get_user_language(update, context)
    current_interval = settings.get_interval()
    
    text = get_translation(lang, 'interval_settings_title', interval=current_interval)
    
    keyboard = [
        [InlineKeyboardButton(get_translation(lang, 'interval_frequent'), callback_data="interval_frequent")],
        [InlineKeyboardButton(get_translation(lang, 'interval_medium'), callback_data="interval_medium")],
        [InlineKeyboardButton(get_translation(lang, 'interval_slow'), callback_data="interval_slow")],
    ]
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return INTERVAL_SELECT

async def interval_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles interval selection."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update, context)
    
    preset = query.data.split('_')[1]
    
    try:
        new_interval = settings.set_interval(preset)
        
        job_queue = context.job_queue
        current_jobs = job_queue.get_jobs_by_name("monitoring_job")
        for job in current_jobs:
            job.schedule_removal()
        
        job_queue.run_repeating(run_monitoring_cycle, interval=new_interval, first=5, name="monitoring_job")
        
        await query.edit_message_text(
            text=get_translation(lang, 'interval_updated', interval=new_interval),
            parse_mode=ParseMode.MARKDOWN
        )
        
    except (ValueError, Exception) as e:
        logger.error(f"Error changing interval: {e}")
        await query.edit_message_text(
            text=get_translation(lang, 'interval_update_error'),
            parse_mode=ParseMode.MARKDOWN
        )

    return ConversationHandler.END


# --- Converter (Conversation Handler) ---
@admin_only
async def convert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the converter conversation."""
    lang = get_user_language(update, context)
    await update.message.reply_text(get_translation(lang, 'convert_prompt'))
    return CONVERT_GET_URL

async def convert_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the subscription URL and processes it."""
    lang = get_user_language(update, context)
    sub_url = update.message.text.strip()
    if not sub_url.startswith('http'):
        await update.message.reply_text(get_translation(lang, 'convert_invalid_url'))
        return CONVERT_GET_URL

    await update.message.reply_text(get_translation(lang, 'convert_starting'), parse_mode=ParseMode.MARKDOWN)

    try:
        converter = RemnavaveSubscriptionConverter(sub_url, verbose=False)
        vless_keys = converter.convert_and_get_keys()

        if not vless_keys:
            await update.message.reply_text(get_translation(lang, 'convert_no_keys'), parse_mode=ParseMode.MARKDOWN)
            return ConversationHandler.END
        
        await update.message.reply_text(get_translation(lang, 'convert_success', count=len(vless_keys)), parse_mode=ParseMode.MARKDOWN)

        keys_text = "\n\n".join(vless_keys)

        if len(keys_text) > 4000:
            with io.BytesIO(keys_text.encode('utf-8')) as f:
                f.name = 'vless_keys.txt'
                await update.message.reply_document(
                    document=f,
                    caption=get_translation(lang, 'convert_too_large')
                )
        else:
            await update.message.reply_text(f"```{keys_text}```", parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        await update.message.reply_text(get_translation(lang, 'convert_error'))

    return ConversationHandler.END


# --- Server Management (Conversation Handlers) ---

# Add Server
@admin_only
async def add_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the add server conversation by asking for a country name."""
    lang = get_user_language(update, context)
    await update.message.reply_text(get_translation(lang, 'add_server_country_prompt'))
    return ADD_SERVER_COUNTRY_PROMPT

async def add_server_country_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's text input for the country name."""
    lang = get_user_language(update, context)
    country_query = update.message.text
    
    matches = find_countries(country_query)

    if not matches:
        await update.message.reply_text(get_translation(lang, 'add_server_country_not_found', query=country_query))
        return ADD_SERVER_COUNTRY_PROMPT

    if len(matches) == 1:
        country = matches[0]
        country_code = country["code"]
        context.user_data['selected_country'] = country_code
        
        country_name = get_country_name_by_code(country_code, lang=lang)
        flag_emoji = get_flag_emoji(country_code)
        
        await update.message.reply_text(
            get_translation(lang, 'add_server_ip_prompt', flag=flag_emoji, country_name=country_name),
            parse_mode=ParseMode.MARKDOWN
        )
        return ADD_SERVER_IP
    
    if len(matches) > 5:
        await update.message.reply_text(get_translation(lang, 'add_server_country_too_many'))
        return ADD_SERVER_COUNTRY_PROMPT

    keyboard = []
    for country in matches:
        country_code = country["code"]
        country_name = country.get(lang, country['ru']) # Fallback to 'ru' if lang key not present
        flag_emoji = get_flag_emoji(country_code)
        keyboard.append([
            InlineKeyboardButton(
                f"{flag_emoji} {country_name}",
                callback_data=f"country_{country_code}"
            )
        ])
    
    await update.message.reply_text(
        get_translation(lang, 'add_server_country_clarify'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADD_SERVER_COUNTRY_SELECT


async def add_server_country_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's selection from the clarification keyboard."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update, context)
    
    country_code = query.data.split('_')[1]
    context.user_data['selected_country'] = country_code
    
    country_name = get_country_name_by_code(country_code, lang=lang)
    flag_emoji = get_flag_emoji(country_code)
    
    await query.edit_message_text(
        text=get_translation(lang, 'add_server_ip_prompt', flag=flag_emoji, country_name=country_name),
        parse_mode=ParseMode.MARKDOWN
    )
    return ADD_SERVER_IP

async def add_server_ip_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_language(update, context)
    ip_address = update.message.text.strip()
    country_code = context.user_data.get('selected_country')

    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_address):
        await update.message.reply_text(get_translation(lang, 'add_server_invalid_ip'), parse_mode=ParseMode.MARKDOWN)
        return ADD_SERVER_IP

    base_name = get_country_name_by_code(country_code, 'ru') # Use 'ru' for consistent naming
    existing_count = db.count_servers_by_country(country_code)
    
    new_name = f"{base_name}-{existing_count + 1}" if existing_count > 0 else base_name
    
    logger.info(f"ADD_SERVER: Received IP: {ip_address}. Determined name: '{new_name}'")

    if db.add_server(ip_address, country_code, new_name):
        await update.message.reply_text(get_translation(lang, 'add_server_success', name=new_name, ip=ip_address), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(get_translation(lang, 'add_server_already_exists', ip=ip_address), parse_mode=ParseMode.MARKDOWN)

    context.user_data.pop('selected_country', None)
    return ConversationHandler.END

# Remove Server
@admin_only
async def remove_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_language(update, context)
    logger.info("REMOVE_SERVER: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("REMOVE_SERVER: No servers found in DB.")
        await update.message.reply_text(get_translation(lang, 'remove_server_no_servers'), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    keyboard = []
    for ip, name, _, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        label = f"{flag_emoji} {name} ({ip})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"remove_{ip}")])

    await update.message.reply_text(
        get_translation(lang, 'remove_server_prompt'),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return REMOVE_SERVER_SELECT

async def remove_server_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update, context)
    
    ip_to_remove = query.data.split('_')[1]
    logger.info(f"REMOVE_SERVER: Attempting to remove IP: {ip_to_remove}")
    
    if db.remove_server(ip_to_remove):
        await query.edit_message_text(text=get_translation(lang, 'remove_server_success', ip=ip_to_remove), parse_mode=ParseMode.MARKDOWN)
    else:
        await query.edit_message_text(text=get_translation(lang, 'remove_server_not_found', ip=ip_to_remove), parse_mode=ParseMode.MARKDOWN)
        
    return ConversationHandler.END

# Check Server
@admin_only
async def check_server_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = get_user_language(update, context)
    logger.info("CHECK_SERVER: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("CHECK_SERVER: No servers found in DB.")
        await update.message.reply_text(get_translation(lang, 'check_server_no_servers'), parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END

    keyboard = []
    for ip, name, _, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        label = f"{flag_emoji} {name} ({ip})"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"check_{ip}")])

    await update.message.reply_text(
        get_translation(lang, 'check_server_prompt'),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return CHECK_SERVER_SELECT

async def check_server_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the server check, with extensive logging for debugging."""
    query = update.callback_query
    await query.answer()
    lang = get_user_language(update, context)
    
    ip_to_check = query.data.split('_')[1]
    logger.info(f"--- CHECK COMMAND DIAGNOSTICS for IP: {ip_to_check} ---")
    
    await query.edit_message_text(text=get_translation(lang, 'check_server_checking', ip=ip_to_check), parse_mode=ParseMode.MARKDOWN)
    
    server_details = db.get_server_details(ip_to_check)
    logger.info(f"1. Raw server_details from DB: {server_details}")
    
    display_name = "Unknown"
    flag_emoji = "🏳️"

    if server_details:
        _, name, _, country_code = server_details
        logger.info(f"2. Extracted details -> Name: '{name}', Country Code: '{country_code}'")
        display_name = name
        flag_emoji = get_flag_emoji(country_code)
    else:
        logger.warning("1a. server_details from DB is None.")

    logger.info(f"5. Final values for report -> IP: {ip_to_check}, Name: {display_name}, Flag: {flag_emoji}")
    report = await get_beautiful_report(ip_to_check, display_name, flag_emoji, lang)
    logger.info(f"6. Generated report string:\n{report}")
    logger.info("--- END CHECK COMMAND DIAGNOSTICS ---")

    await query.edit_message_text(text=report, parse_mode=ParseMode.MARKDOWN)
        
    return ConversationHandler.END


@admin_only
async def list_servers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists all monitored servers and their status."""
    lang = get_user_language(update, context)
    logger.info("LIST_SERVERS: Getting server list.")
    servers = db.get_all_servers()
    if not servers:
        logger.warning("LIST_SERVERS: No servers found in DB.")
        await update.message.reply_text(get_translation(lang, 'list_servers_no_servers'), parse_mode=ParseMode.MARKDOWN)
        return

    message = get_translation(lang, 'list_servers_title')
    status_translation = {
        'UP': get_translation(lang, 'status_up'),
        'DOWN': get_translation(lang, 'status_down'),
        'UNKNOWN': get_translation(lang, 'status_unknown')
    }
    status_emojis = {'UP': '✅', 'DOWN': '❌', 'UNKNOWN': '❓'}

    for ip, name, status, country_code in servers:
        flag_emoji = get_flag_emoji(country_code)
        status_text = status_translation.get(status, status)
        status_emoji = status_emojis.get(status, '❓')
        
        message += f"{flag_emoji} *{name}* (`{ip}`)\n"
        message += get_translation(lang, 'list_servers_status', emoji=status_emoji, status_text=status_text) + "\n\n"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the current conversation, preserving language settings."""
    lang = get_user_language(update, context)
    await update.message.reply_text(get_translation(lang, 'operation_cancelled'))
    # Clear only conversation-specific data, not the whole user_data
    context.user_data.pop('selected_country', None)
    return ConversationHandler.END

async def post_init(application: Application):
    """Post-initialization function to set bot commands."""
    commands = [
        BotCommand("start", "▶️ Start the bot"),
        BotCommand("login", "🔑 Login as admin"),
        BotCommand("logout", "🚪 Logout"),
        BotCommand("addserver", "➕ Add a server"),
        BotCommand("removeserver", "➖ Remove a server"),
        BotCommand("listservers", "📋 List servers"),
        BotCommand("check", "🔎 Check a server"),
        BotCommand("convert", "🔄 Convert subscription"),
        BotCommand("interval", "⚙️ Set interval"),
        BotCommand("language", "🌐 Select language"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Run the bot."""
    try:
        # Initialize DB
        db.initialize_db()
        
        # Get the initial interval from settings
        initial_interval = settings.get_interval()
        logger.info(f"Starting with monitoring interval: {initial_interval} seconds.")

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
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation),
            ],
            allow_reentry=True,
        )

        remove_server_conv = ConversationHandler(
            entry_points=[CommandHandler("removeserver", remove_server_start)],
            states={
                REMOVE_SERVER_SELECT: [CallbackQueryHandler(remove_server_selected, pattern="^remove_")],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation),
            ],
            allow_reentry=True,
        )

        check_server_conv = ConversationHandler(
            entry_points=[CommandHandler("check", check_server_start)],
            states={
                CHECK_SERVER_SELECT: [CallbackQueryHandler(check_server_selected, pattern="^check_")],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation),
            ],
            allow_reentry=True,
        )

        convert_conv = ConversationHandler(
            entry_points=[CommandHandler("convert", convert_start)],
            states={
                CONVERT_GET_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_url_received)]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation),
            ],
            allow_reentry=True,
        )
        
        interval_conv = ConversationHandler(
            entry_points=[CommandHandler("interval", interval_start)],
            states={
                INTERVAL_SELECT: [CallbackQueryHandler(interval_selected, pattern="^interval_")]
            },
            fallbacks=[
                CommandHandler("cancel", cancel_conversation),
                MessageHandler(filters.COMMAND, cancel_conversation),
            ],
            allow_reentry=True,
        )

        # --- Command Handlers ---
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("login", login_command))
        application.add_handler(CommandHandler("logout", logout_command))
        application.add_handler(CommandHandler("listservers", list_servers_command))
        application.add_handler(CommandHandler("language", language_command))
        application.add_handler(CallbackQueryHandler(language_selected, pattern="^lang_"))
        
        # Add conversation handlers
        application.add_handler(add_server_conv)
        application.add_handler(remove_server_conv)
        application.add_handler(check_server_conv)
        application.add_handler(convert_conv)
        application.add_handler(interval_conv)

        # Run the bot until the user presses Ctrl-C
        logger.info("Bot is starting...")
        application.run_polling()
        
    except Exception as e:
        import traceback
        with open("crash.log", "w") as f:
            f.write(f"Startup Error: {e}\n")
            f.write(traceback.format_exc())
        logger.critical(f"A critical error occurred during startup: {e}", exc_info=True)

if __name__ == "__main__":
    main()
