#!/bin/bash

# Проверка на root права
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo)"
    exit 1
fi

BOT_DIR="/root/cap"
VENV_DIR="$BOT_DIR/venv"

# Создание виртуального окружения если его нет
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    $VENV_DIR/bin/pip install -r requirements.txt
fi

# Копирование файла сервиса
cp captcha_bot.service /etc/systemd/system/

# Создание лог файлов
touch /var/log/captcha_bot.log
touch /var/log/captcha_bot_error.log

# Перезагрузка демона и запуск сервиса
systemctl daemon-reload
systemctl enable captcha_bot.service
systemctl start captcha_bot.service

echo "Сервис установлен и запущен!"
echo "Для проверки статуса используйте: systemctl status captcha_bot.service"
echo "Для просмотра логов используйте: tail -f /var/log/captcha_bot.log" 