#!/bin/bash
echo "--- Настройка бота для мониторинга серверов ---"

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

VENV_PYTHON="./venv/bin/python3"
VENV_PIP="./venv/bin/pip"

# Check if python3 is available
if ! command -v python3 &> /dev/null
then
    echo "ОШИБКА: python3 не найден. Пожалуйста, установите Python 3."
    exit
fi

# Setting up virtual environment
echo "[1/4] Настройка виртуального окружения Python..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ОШИБКА: Не удалось создать виртуальное окружение. Убедитесь, что 'python3-venv' установлен."
    echo "Попробуйте выполнить: sudo apt-get install python3-venv"
    exit 1
fi

# Installing dependencies
echo "[2/4] Установка зависимостей из requirements.txt..."
"$VENV_PIP" install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ОШИБКА: Не удалось установить зависимости."
    exit 1
fi

# Initializing database
echo "[3/4] Инициализация базы данных..."
"$VENV_PYTHON" database.py
if [ $? -ne 0 ]; then
    echo "ОШИБКА: Не удалось инициализировать базу данных."
    exit 1
fi

echo "[4/4] Запуск бота..."

PID_FILE="bot.pid"

if [ -f "$PID_FILE" ]; then
    echo "ОШИБКА: Бот уже запущен. Сначала выполните ./stop.sh"
    exit 1
fi

echo "Чтобы остановить бота, выполните ./stop.sh в другом терминале."
echo "---"
nohup "$VENV_PYTHON" main.py > bot.log 2>&1 &
echo $! > bot.pid
echo "Бот запущен в фоновом режиме. Логи пишутся в bot.log"
