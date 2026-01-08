# Бот для Мониторинга Серверов и Конвертации VLESS

Этот Telegram-бот предназначен для мониторинга доступности серверов по ICMP (ping) и конвертации ссылок-подписок VLESS.

***

# VLESS Server Monitoring and Conversion Bot

This Telegram bot is designed to monitor server availability via ICMP (ping) and convert VLESS subscription links.

## 🚀 Key Features

- **Server Monitoring:** Periodically checks server availability.
- **Notifications:** Instant Telegram alerts when a server's status changes (UP/DOWN).
- **Manual Check:** Ability to check a specific server's status at any time.
- **Server Management:** Conveniently add and remove servers for monitoring.
- **Automatic Naming:** If you add multiple servers from the same country, the bot will automatically assign them unique names (e.g., `Russia-1`, `Russia-2`).
- **VLESS Converter:** A utility to extract keys from a VLESS subscription link.
- **Customizable Interval:** Ability to change the frequency of monitoring checks.
- **Access Control:** Key commands are protected by an administrator password.
- **Multi-language Support:** Supports Russian and English.

## 🛠️ Installation and Launch

### 1. Clone the repository
```bash
git clone <your repository URL>
cd <project folder>
```

### 2. Set up the environment
Create a `.env` file in the root of the project by copying the contents from `.env.example`, and fill it with your data.

```env
# Your Telegram bot token (get it from @BotFather)
TELEGRAM_TOKEN=YOUR_TELEGRAM_TOKEN

# Password for access to admin commands
ADMIN_PASSWORD=YOUR_SECRET_PASSWORD

# Maximum number of concurrent admin sessions (optional, default is 3)
MAX_SESSIONS=3

# Database file name (optional, default is monitoring_bot.db)
DATABASE_FILE=monitoring_bot.db
```

### 3. Launch the bot
For the first launch and to automatically install all dependencies, use the `start.sh` script.

```bash
chmod +x start.sh
./start.sh
```
The script will create a virtual environment, install the necessary libraries, initialize the database, and run the bot in the background. All logs will be written to `bot.log`.

### 4. Stop the bot
To stop the bot, use the `stop.sh` script.

```bash
chmod +x stop.sh
./stop.sh
```

## 🤖 Usage

After launching the bot, start a conversation with it in Telegram.

### Main Commands
- `/start` - Show welcome message.
- `/login <password>` - Log in as an administrator.
- `/logout` - Log out.
- `/addserver` - Start the dialog to add a new server for monitoring.
- `/removeserver` - Remove a server from the monitoring list.
- `/listservers` - Show the list of all monitored servers and their status.
- `/check` - Start the dialog for an instant server status check.
- `/convert` - Convert a VLESS subscription link.
- `/interval` - Change the monitoring check interval.
- `/language` - Select the interface language.

## 💻 Tech Stack

- **Python 3**
- **python-telegram-bot** - The main library for working with the Telegram Bot API.
- **SQLite** - Built-in database for storing the list of servers and administrators.
- **asyncio** - For asynchronous task processing and non-blocking monitoring.
