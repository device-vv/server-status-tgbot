import json
import os

SETTINGS_FILE = 'settings.json'

# Preset intervals in seconds
INTERVAL_PRESETS = {
    'frequent': 60,    # 1 минута
    'medium': 300,     # 5 минут
    'slow': 900,       # 15 минут
}

DEFAULT_INTERVAL = INTERVAL_PRESETS['frequent']

def get_settings():
    """Загружает настройки из файла settings.json."""
    if not os.path.exists(SETTINGS_FILE):
        return {'interval': DEFAULT_INTERVAL}
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {'interval': DEFAULT_INTERVAL}

def save_settings(settings):
    """Сохраняет настройки в файл settings.json."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Ошибка при сохранении настроек: {e}")

def get_interval() -> int:
    """Возвращает текущий интервал проверки из настроек."""
    settings = get_settings()
    # Убедимся, что сохраненное значение валидно, иначе вернем значение по-умолчанию
    if settings.get('interval') in INTERVAL_PRESETS.values():
        return settings.get('interval', DEFAULT_INTERVAL)
    return DEFAULT_INTERVAL

def set_interval(preset: str) -> int:
    """
    Устанавливает новый интервал проверки и сохраняет его.
    Возвращает новое значение интервала в секундах.
    """
    if preset not in INTERVAL_PRESETS:
        raise ValueError(f"Недопустимый пресет интервала: {preset}")
    
    new_interval = INTERVAL_PRESETS[preset]
    settings = get_settings()
    settings['interval'] = new_interval
    save_settings(settings)
    return new_interval

if __name__ == '__main__':
    print(f"Текущий интервал: {get_interval()} секунд")
    
    print("Установка 'medium' (300)...")
    set_interval('medium')
    print(f"Новый интервал: {get_interval()} секунд")

    print("Установка 'frequent' (60)...")
    set_interval('frequent')
    print(f"Новый интервал: {get_interval()} секунд")
