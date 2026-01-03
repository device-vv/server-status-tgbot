import asyncio
import logging
from database import get_all_servers, update_server_status, get_admins
from ping import do_ping
from countries import get_country_name_by_code, get_flag_emoji

logger = logging.getLogger(__name__)

async def check_and_notify(app, ip_address, name, country_code, last_status):
    """Checks a single server and sends a notification if the status changes."""
    try:
        ping_result = await do_ping(ip_address)
        current_status = ping_result.status

        if current_status != last_status:
            logger.info(f"Status change for {name} ({ip_address}): {last_status} -> {current_status}")
            
            # Use asyncio.to_thread to run blocking DB call in a separate thread
            await asyncio.to_thread(update_server_status, ip_address, current_status)
            
            flag_emoji = get_flag_emoji(country_code)
            status_text = '✅ В сети' if current_status == 'UP' else '❌ Не в сети'
            
            message = (
                f"🚨 *Изменение статуса сервера* 🚨\n\n"
                f"{flag_emoji} *{name}*\n"
                f"Сервер: `{ip_address}`\n"
                f"Новый статус: *{status_text}*"
            )
            
            # Get admins within the async context
            admin_ids = await asyncio.to_thread(get_admins)
            
            notification_tasks = []
            for chat_id in admin_ids:
                notification_tasks.append(
                    app.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                )
            await asyncio.gather(*notification_tasks, return_exceptions=True)

    except Exception as e:
        logger.error(f"Error while checking server {ip_address}: {e}")

async def run_monitoring_cycle(app):
    """
    A single cycle of the monitoring job. Runs all server checks concurrently.
    """
    logger.info("Starting concurrent monitoring cycle...")
    
    # Run blocking DB call in a separate thread
    servers_to_check = await asyncio.to_thread(get_all_servers)
    
    if not servers_to_check:
        logger.info("No servers to check.")
        logger.info("Monitoring cycle finished.")
        return

    # Create a task for each server check
    tasks = []
    for ip, name, last_status, country_code in servers_to_check:
        tasks.append(check_and_notify(app, ip, name, country_code, last_status))

    # Run all checks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Monitoring cycle finished.")
