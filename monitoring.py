import asyncio
import logging
from database import get_all_servers, update_server_status, get_admins
from ping import do_ping
from countries import get_country_name_by_code, get_flag_emoji
from localization import get_translation

logger = logging.getLogger(__name__)

async def check_and_notify(app, ip_address, name, country_code, last_status):
    """Checks a single server and sends a notification if the status changes."""
    try:
        ping_result = await do_ping(ip_address)
        current_status = ping_result.status

        if current_status != last_status:
            logger.info(f"Status change for {name} ({ip_address}): {last_status} -> {current_status}")
            
            await asyncio.to_thread(update_server_status, ip_address, current_status)
            
            admin_list = await asyncio.to_thread(get_admins)
            if not admin_list:
                return

            notification_tasks = []
            for chat_id, lang in admin_list:
                flag_emoji = get_flag_emoji(country_code)
                status_text_key = 'status_up' if current_status == 'UP' else 'status_down'
                status_text = get_translation(lang, status_text_key)
                
                title = get_translation(lang, 'monitoring_status_change_title')
                server_name_line = get_translation(lang, 'monitoring_server_name', flag=flag_emoji, name=name)
                server_ip_line = get_translation(lang, 'monitoring_server_ip', ip=ip_address)
                new_status_line = get_translation(lang, 'monitoring_new_status', status_text=status_text)

                message = f"{title}\n\n{server_name_line}\n{server_ip_line}\n{new_status_line}"
                
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
    
    servers_to_check = await asyncio.to_thread(get_all_servers)
    
    if not servers_to_check:
        logger.info("No servers to check.")
        logger.info("Monitoring cycle finished.")
        return

    tasks = []
    for ip, name, last_status, country_code in servers_to_check:
        tasks.append(check_and_notify(app, ip, name, country_code, last_status))

    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Monitoring cycle finished.")
