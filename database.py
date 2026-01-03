import sqlite3
import os
import logging
from dotenv import load_dotenv

load_dotenv()
DATABASE_FILE = os.getenv('DATABASE_FILE', 'monitoring_bot.db')
logger = logging.getLogger(__name__)

def add_column_if_not_exists(db_file, table_name, column_name, column_type):
    """Safely adds a new column to a table if it doesn't already exist."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]
        if column_name not in columns:
            logger.info(f"Adding column '{column_name}' to table '{table_name}'...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            conn.commit()
            logger.info("Column added successfully.")
        else:
            logger.info(f"Column '{column_name}' already exists in '{table_name}'.")

def initialize_db():
    """Initializes the database and creates tables with the new schema."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL UNIQUE,
                country_code TEXT NOT NULL,
                name TEXT NOT NULL,
                last_status TEXT DEFAULT 'UNKNOWN',
                status_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                chat_id INTEGER PRIMARY KEY
            )
        ''')
        conn.commit()

# --- Admin Management Functions ---
def add_admin(chat_id):
    """Adds a new admin session."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (chat_id) VALUES (?)", (chat_id,))
        conn.commit()

def remove_admin(chat_id):
    """Removes an admin session."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE chat_id = ?", (chat_id,))
        conn.commit()

def get_admins():
    """Returns chat_id of all active admins."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM admins")
        return [row[0] for row in cursor.fetchall()]

def get_admin_count():
    """Counts the number of active admin sessions."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM admins")
        return cursor.fetchone()[0]

def is_admin(chat_id):
    """Checks if a user is a logged-in admin."""
    return chat_id in get_admins()
# --- End Admin Management Functions ---

def add_server(ip_address, country_code, name):
    """Adds a server to the database with its custom name."""
    logger.info(f"DATABASE: Attempting to add server. IP: {ip_address}, Country: {country_code}, Name: {name}")
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO servers (ip_address, country_code, name) VALUES (?, ?, ?)",
                (ip_address, country_code, name)
            )
            conn.commit()
            logger.info("DATABASE: Add server successful.")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"DATABASE: IntegrityError. Server with IP {ip_address} already exists.")
            return False
        except Exception as e:
            logger.error(f"DATABASE: An unexpected error occurred in add_server: {e}")
            return False

def count_servers_by_country(country_code: str) -> int:
    """Counts how many servers are already registered for a given country."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM servers WHERE country_code = ?", (country_code,))
        count = cursor.fetchone()[0]
        logger.info(f"DATABASE: Found {count} servers with country_code {country_code}.")
        return count

def get_all_servers():
    """Fetches all servers, including their custom name."""
    logger.info("DATABASE: Getting all servers.")
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address, name, last_status, country_code FROM servers")
        servers = cursor.fetchall()
        logger.info(f"DATABASE: Found {len(servers)} servers: {servers}")
        return servers

def get_server_details(ip_address: str):
    """Fetches details for a specific server, including its custom name."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip_address, name, last_status, country_code FROM servers WHERE ip_address = ?", (ip_address,))
        return cursor.fetchone()

def remove_server(ip_address):
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM servers WHERE ip_address = ?", (ip_address,))
        conn.commit()
        return cursor.rowcount > 0

def update_server_status(ip_address, status):
    """Updates the status of a server."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE servers SET last_status = ?, status_timestamp = CURRENT_TIMESTAMP WHERE ip_address = ?",
            (status, ip_address)
        )
        conn.commit()

if __name__ == '__main__':
    print("Performing database maintenance...")
    initialize_db()
    add_column_if_not_exists(DATABASE_FILE, 'servers', 'name', 'TEXT')
    print("Database maintenance complete.")
