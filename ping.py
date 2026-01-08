import asyncio
import re
import logging
from collections import namedtuple
from localization import get_translation

logger = logging.getLogger(__name__)
PingResult = namedtuple('PingResult', ['status', 'packet_loss', 'min_rtt', 'avg_rtt', 'max_rtt'])

async def do_ping(ip_address: str) -> PingResult:
    """
    Performs a system ping command and parses its output.
    Increased timeout to 5 seconds for more reliability.
    """
    command = f"ping -c 4 -W 5 {ip_address}"
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    output = stdout.decode('utf-8')
    
    if process.returncode == 0:
        status = 'UP'
    else:
        return PingResult(status='DOWN', packet_loss=100.0, min_rtt=0, avg_rtt=0, max_rtt=0)

    loss_match = re.search(r"(\d+(\.\d+)?)% packet loss", output)
    packet_loss = float(loss_match.group(1)) if loss_match else 100.0

    rtt_match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output)
    if rtt_match:
        min_rtt = float(rtt_match.group(1))
        avg_rtt = float(rtt_match.group(2))
        max_rtt = float(rtt_match.group(3))
    else:
        min_rtt, avg_rtt, max_rtt = 0, 0, 0

    return PingResult(
        status=status,
        packet_loss=packet_loss,
        min_rtt=min_rtt,
        avg_rtt=avg_rtt,
        max_rtt=max_rtt
    )

async def get_beautiful_report(ip_address: str, country_name: str, flag_emoji: str, lang: str = 'ru') -> str:
    """
    Performs a ping and generates a beautiful, localized text report.
    """
    try:
        result = await do_ping(ip_address)

        header = get_translation(lang, 'ping_report_title', flag=flag_emoji, name=country_name, ip=ip_address)

        if result.status == 'UP':
            status_line = get_translation(lang, 'ping_status_online')
            report = (
                f"{header}\n\n"
                f"{status_line}\n\n"
                f"{get_translation(lang, 'ping_rtt_title')}\n"
                f"{get_translation(lang, 'ping_rtt_min', ms=result.min_rtt)}\n"
                f"{get_translation(lang, 'ping_rtt_avg', ms=result.avg_rtt)}\n"
                f"{get_translation(lang, 'ping_rtt_max', ms=result.max_rtt)}\n\n"
                f"{get_translation(lang, 'ping_packet_loss', loss=result.packet_loss)}"
            )
        else:
            status_line = get_translation(lang, 'ping_status_offline')
            report = (
                f"{header}\n\n"
                f"{status_line}\n\n"
                f"{get_translation(lang, 'ping_offline_reason')}"
            )
        
        return report

    except Exception as e:
        logger.error(f"Error creating report for {ip_address}: {e}")
        return get_translation(lang, 'ping_error', ip=ip_address)

if __name__ == '__main__':
    # Example usage
    async def test_ping():
        ip_to_test = "192.0.2.1" # Test IP - should be offline
        country_name_test = "Example (Offline)"
        flag_test = "🏳️"
        
        print("--- Testing Offline (RU) ---")
        report_ru_offline = await get_beautiful_report(ip_to_test, country_name_test, flag_test, 'ru')
        print(report_ru_offline)

        print("\n--- Testing Offline (EN) ---")
        report_en_offline = await get_beautiful_report(ip_to_test, country_name_test, flag_test, 'en')
        print(report_en_offline)
        
        print("\n" + "="*30 + "\n")

        ip_to_test_up = "8.8.8.8"
        country_name_up = "Google DNS"
        flag_up = "🇺🇸"

        print("--- Testing Online (RU) ---")
        report_ru_online = await get_beautiful_report(ip_to_test_up, country_name_up, flag_up, 'ru')
        print(report_ru_online)

        print("\n--- Testing Online (EN) ---")
        report_en_online = await get_beautiful_report(ip_to_test_up, country_name_up, flag_up, 'en')
        print(report_en_online)

    asyncio.run(test_ping())
