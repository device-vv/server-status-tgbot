import asyncio
import re
from collections import namedtuple

PingResult = namedtuple('PingResult', ['status', 'packet_loss', 'min_rtt', 'avg_rtt', 'max_rtt'])

async def do_ping(ip_address: str) -> PingResult:
    """
    Выполняет системную команду ping и парсит ее вывод.
    Увеличено время ожидания до 5 секунд для большей надежности.
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

async def get_beautiful_report(ip_address: str, country_name: str, flag_emoji: str) -> str:
    """
    Выполняет пинг и генерирует красивый текстовый отчет.
    """
    try:
        result = await do_ping(ip_address)

        header = f"📊 *Результат проверки для* {flag_emoji} *{country_name}* (`{ip_address}`)\n\n"

        if result.status == 'UP':
            status_line = f"✅ *Статус:* `ОНЛАЙН`"
            report = (
                f"{header}"
                f"{status_line}\n\n"
                f"🌍 *Пинг (RTT)*:\n"
                f"   - Мин: `{result.min_rtt:.3f} ms`\n"
                f"   - Сред: `{result.avg_rtt:.3f} ms`\n"
                f"   - Макс: `{result.max_rtt:.3f} ms`\n\n"
                f"📉 *Потеря пакетов:* `{result.packet_loss}%`"
            )
        else:
            status_line = f"❌ *Статус:* `ОФФЛАЙН`"
            report = (
                f"{header}"
                f"{status_line}\n\n"
                f"Причина: Сервер не отвечает на ICMP-запросы (пинг)."
            )
        
        return report

    except Exception as e:
        logger.error(f"Ошибка при создании отчета для {ip_address}: {e}")
        return f"Произошла ошибка при проверке `{ip_address}`."

if __name__ == '__main__':
    # Пример использования
    import logging
    logger = logging.getLogger(__name__)
    
    async def test_ping():
        ip_to_test = "192.0.2.1" # Test IP - должен быть оффлайн
        country_name_test = "Пример (Оффлайн)"
        flag_test = "🏳️"
        
        print(f"--- Тестирование {ip_to_test} ---")
        report = await get_beautiful_report(ip_to_test, country_name_test, flag_test)
        print(report.replace('*', '').replace('`', ''))
        
        print("\n" + "="*30 + "\n")

        ip_to_test_up = "8.8.8.8"
        country_name_up = "Google DNS"
        flag_up = "🇺🇸"
        print(f"--- Тестирование {ip_to_test_up} ---")
        report_up = await get_beautiful_report(ip_to_test_up, country_name_up, flag_up)
        print(report_up.replace('*', '').replace('`', ''))

    asyncio.run(test_ping())
