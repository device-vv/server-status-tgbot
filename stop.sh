#!/bin/bash
echo "--- Остановка бота для мониторинга серверов ---"
PID_FILE="bot.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if [ -z "$PID" ]; then
        echo "Файл PID пуст. Невозможно остановить бота."
        exit 1
    fi

    echo "Найден PID: $PID. Остановка процесса..."
    kill "$PID"
    rm "$PID_FILE"
    echo "Бот остановлен."
else
    echo "Файл bot.pid не найден. Бот не запущен или был остановлен ранее."
fi
echo "---"