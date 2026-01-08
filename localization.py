# localization.py
import database as db
from telegram import Update
from telegram.ext import ContextTypes

# Default language if the user's language is not set or not supported
DEFAULT_LANGUAGE = 'ru'

translations = {
    'en': {
        # General
        'welcome': "🤖 *Welcome to the Server Monitoring Bot!*\n\n"
                   "I can monitor the status of your servers and convert VLESS subscription links.\n\n"
                   "To get started, you need to log in as an administrator using the `/login` command with a password.",
        'access_denied': "⛔️ *Access denied.*\nPlease log in first using the /login command.",
        'already_logged_in': "✅ *You are already logged in.*",
        'max_sessions_reached': "⚠️ *Maximum number of administrator sessions reached.*\nTry again later.",
        'login_success': "✅ *Login successful!*\nYou now have access to administrator commands.",
        'login_failed': "❌ *Incorrect password.*\nPlease try again.",
        'logout_success': "✅ *You have been logged out.*",
        'operation_cancelled': "Operation cancelled.",
        
        # Interval
        'interval_settings_title': "⚙️ *Interval Settings*\n\nCurrent interval: *{interval} seconds*.\n\nSelect a new check frequency:",
        'interval_frequent': "Frequent (1 minute)",
        'interval_medium': "Medium (5 minutes)",
        'interval_slow': "Slow (15 minutes)",
        'interval_updated': "✅ *Check interval updated to {interval} seconds.*",
        'interval_update_error': "❌ *An error occurred while changing the interval.*",

        # Converter
        'convert_prompt': "Please send me the VLESS subscription link you want to convert.",
        'convert_invalid_url': "❌ This doesn't look like a valid link. Please send a correct URL.",
        'convert_starting': "⏳ *Starting conversion...*\nThis may take up to a minute.",
        'convert_no_keys': "❌ *Failed to extract VLESS keys from this subscription.*\nCheck the link or try again later.",
        'convert_success': "✅ *Successfully found {count} keys!*",
        'convert_too_large': "Keys are in the text file as there are too many of them.",
        'convert_error': "An internal error occurred during conversion. Please try again later.",

        # Add Server
        'add_server_country_prompt': "Enter the name of the country where the server is located (e.g., 'Germany' or 'Finland').",
        'add_server_country_not_found': "😕 Country not found for query '{query}'. Please try again.",
        'add_server_country_too_many': "Too many matches found. Please specify your query.",
        'add_server_country_clarify': "Several matches found. Please choose one of the options:",
        'add_server_ip_prompt': "Selected country: {flag} *{country_name}*\n\nNow enter the server's IP address:",
        'add_server_invalid_ip': "❌ *Invalid IP address format.*\nPlease enter a valid IPv4 address.",
        'add_server_success': "✅ Server '{name}' (`{ip}`) added successfully!",
        'add_server_already_exists': "⚠️ A server with the IP `{ip}` is already being monitored.",

        # Remove Server
        'remove_server_no_servers': "*No servers to remove.*",
        'remove_server_prompt': "*Select a server to remove:*",
        'remove_server_success': "✅ Server `{ip}` has been removed.",
        'remove_server_not_found': "⚠️ Could not find server `{ip}`. It might have been already removed.",

        # Check Server
        'check_server_no_servers': "*No servers to check.*",
        'check_server_prompt': "*Select a server for an instant check:*",
        'check_server_checking': "*Checking* `{ip}`...",

        # List Servers
        'list_servers_no_servers': "*There are currently no monitored servers.*",
        'list_servers_title': "📋 *Monitored servers:*\n\n",
        'list_servers_status': "*Status:* {emoji} {status_text}",
        'status_up': "Online",
        'status_down': "Offline",
        'status_unknown': "Unknown",

        # Language
        'language_select': "Please select your language:",
        'language_selected': "✅ Language has been set to English.",
        
        # Monitoring status change
        'monitoring_status_change_title': "🚨 *Server Status Change* 🚨",
        'monitoring_new_status': "New status: *{status_text}*",
        'monitoring_server_name': "{flag} *{name}*",
        'monitoring_server_ip': "Server: `{ip}`",

        # Ping Report
        'ping_report_title': "📊 *Check result for* {flag} *{name}* (`{ip}`)",
        'ping_status_online': "✅ *Status:* `ONLINE`",
        'ping_status_offline': "❌ *Status:* `OFFLINE`",
        'ping_rtt_title': "🌍 *Ping (RTT)*:",
        'ping_rtt_min': "   - Min: `{ms:.3f} ms`",
        'ping_rtt_avg': "   - Avg: `{ms:.3f} ms`",
        'ping_rtt_max': "   - Max: `{ms:.3f} ms`",
        'ping_packet_loss': "📉 *Packet loss:* `{loss}%`",
        'ping_offline_reason': "Reason: Server does not respond to ICMP (ping) requests.",
        'ping_error': "An error occurred while checking `{ip}`.",
    },
    'ru': {
        # General
        'welcome': "🤖 *Добро пожаловать в бот для мониторинга серверов!*\n\n"
                   "Я могу следить за состоянием ваших серверов, а также конвертировать ссылки подписок VLESS.\n\n"
                   "Для начала работы вам необходимо войти как администратор, используя команду `/login` с паролем.",
        'access_denied': "⛔️ *Доступ запрещен.*\nПожалуйста, сначала войдите с помощью команды /login.",
        'already_logged_in': "✅ *Вы уже вошли в систему.*",
        'max_sessions_reached': "⚠️ *Достигнуто максимальное количество сессий администраторов.*\nПопробуйте позже.",
        'login_success': "✅ *Вход выполнен успешно!*\nТеперь у вас есть доступ к командам администратора.",
        'login_failed': "❌ *Неверный пароль.*\nПожалуйста, попробуйте еще раз.",
        'logout_success': "✅ *Вы вышли из системы.*",
        'operation_cancelled': "Операция отменена.",

        # Interval
        'interval_settings_title': "⚙️ *Настройка интервала проверки*\n\nТекущий интервал: *{interval} секунд*.\n\nВыберите новую частоту проверки:",
        'interval_frequent': "Частая (1 минута)",
        'interval_medium': "Средняя (5 минут)",
        'interval_slow': "Медленная (15 минут)",
        'interval_updated': "✅ *Интервал проверки обновлен до {interval} секунд.*",
        'interval_update_error': "❌ *Произошла ошибка при смене интервала.*",
        
        # Converter
        'convert_prompt': "Пожалуйста, отправьте мне ссылку на подписку VLESS, которую вы хотите конвертировать.",
        'convert_invalid_url': "❌ Похоже, это недействительная ссылка. Пожалуйста, отправьте корректный URL.",
        'convert_starting': "⏳ *Начинаю конвертацию...*\nЭто может занять до минуты.",
        'convert_no_keys': "❌ *Не удалось извлечь ключи VLESS из этой подписки.*\nПроверьте ссылку или попробуйте позже.",
        'convert_success': "✅ *Успешно найдено {count} ключей!*",
        'convert_too_large': "Ключи в текстовом файле, так как их слишком много.",
        'convert_error': "Произошла внутренняя ошибка при конвертации. Пожалуйста, попробуйте позже.",
        
        # Add Server
        'add_server_country_prompt': "Введите название страны, в которой находится сервер (например, 'Германия' или 'Finland').",
        'add_server_country_not_found': "😕 Страна по запросу '{query}' не найдена. Попробуйте еще раз.",
        'add_server_country_too_many': "Найдено слишком много совпадений. Пожалуйста, уточните ваш запрос.",
        'add_server_country_clarify': "Найдено несколько совпадений. Пожалуйста, выберите один из вариантов:",
        'add_server_ip_prompt': "Выбрана страна: {flag} *{country_name}*\n\nТеперь введите IP-адрес сервера:",
        'add_server_invalid_ip': "❌ *Неверный формат IP-адреса.*\nПожалуйста, введите действительный IPv4-адрес.",
        'add_server_success': "✅ Сервер '{name}' (`{ip}`) успешно добавлен!",
        'add_server_already_exists': "⚠️ Сервер с IP `{ip}` уже отслеживается.",

        # Remove Server
        'remove_server_no_servers': "*Нет серверов для удаления.*",
        'remove_server_prompt': "*Выберите сервер для удаления:*",
        'remove_server_success': "✅ Сервер `{ip}` был удален.",
        'remove_server_not_found': "⚠️ Не удалось найти сервер `{ip}`. Возможно, он уже был удален.",

        # Check Server
        'check_server_no_servers': "*Нет серверов для проверки.*",
        'check_server_prompt': "*Выберите сервер для мгновенной проверки:*",
        'check_server_checking': "*Проверяю* `{ip}`...",
        
        # List Servers
        'list_servers_no_servers': "*На данный момент нет отслеживаемых серверов.*",
        'list_servers_title': "📋 *Отслеживаемые серверы:*\n\n",
        'list_servers_status': "*Статус:* {emoji} {status_text}",
        'status_up': "В сети",
        'status_down': "Не в сети",
        'status_unknown': "Неизвестно",

        # Language
        'language_select': "Пожалуйста, выберите ваш язык:",
        'language_selected': "✅ Язык был изменен на русский.",

        # Monitoring status change
        'monitoring_status_change_title': "🚨 *Изменение статуса сервера* 🚨",
        'monitoring_new_status': "Новый статус: *{status_text}*",
        'monitoring_server_name': "{flag} *{name}*",
        'monitoring_server_ip': "Сервер: `{ip}`",

        # Ping Report
        'ping_report_title': "📊 *Результат проверки для* {flag} *{name}* (`{ip}`)",
        'ping_status_online': "✅ *Статус:* `ОНЛАЙН`",
        'ping_status_offline': "❌ *Статус:* `ОФФЛАЙН`",
        'ping_rtt_title': "🌍 *Пинг (RTT)*:",
        'ping_rtt_min': "   - Мин: `{ms:.3f} мс`",
        'ping_rtt_avg': "   - Сред: `{ms:.3f} мс`",
        'ping_rtt_max': "   - Макс: `{ms:.3f} мс`",
        'ping_packet_loss': "📉 *Потеря пакетов:* `{loss}%`",
        'ping_offline_reason': "Причина: Сервер не отвечает на ICMP-запросы (пинг).",
        'ping_error': "Произошла ошибка при проверке `{ip}`.",
    }
}

def get_user_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Get the user's selected language.
    Priority:
    1. From the database if the user is a logged-in admin.
    2. From the temporary context.user_data.
    3. Default language.
    """
    user = update.effective_user
    if user:
        user_id = user.id
        if db.is_admin(user_id):
            return db.get_admin_language(user_id)

    return context.user_data.get('language', DEFAULT_LANGUAGE)


def get_translation(lang, key, **kwargs):
    """
    Get a translated string for a given language and key.
    - lang: The language code (e.g., 'en', 'ru')
    - key: The key for the string (e.g., 'welcome')
    - **kwargs: Values to format the string with.
    """
    # Fallback to default language if the key is not in the selected language
    translation = translations.get(lang, translations[DEFAULT_LANGUAGE]).get(key, f"_{key}_")
    
    # Format the string with any provided arguments
    if kwargs:
        return translation.format(**kwargs)
    
    return translation
