import logging

logger = logging.getLogger(__name__)

# This is a static but comprehensive list to ensure reliability.
# It avoids the pitfalls of locale-dependent libraries in minimal environments.
COUNTRIES_DB = [
    {"code": "AF", "en": "Afghanistan", "ru": "Афганистан"},
    {"code": "AL", "en": "Albania", "ru": "Албания"},
    {"code": "DZ", "en": "Algeria", "ru": "Алжир"},
    {"code": "AD", "en": "Andorra", "ru": "Андорра"},
    {"code": "AO", "en": "Angola", "ru": "Ангола"},
    {"code": "AR", "en": "Argentina", "ru": "Аргентина"},
    {"code": "AM", "en": "Armenia", "ru": "Армения"},
    {"code": "AU", "en": "Australia", "ru": "Австралия"},
    {"code": "AT", "en": "Austria", "ru": "Австрия"},
    {"code": "AZ", "en": "Azerbaijan", "ru": "Азербайджан"},
    {"code": "BY", "en": "Belarus", "ru": "Беларусь"},
    {"code": "BE", "en": "Belgium", "ru": "Бельгия"},
    {"code": "BR", "en": "Brazil", "ru": "Бразилия"},
    {"code": "BG", "en": "Bulgaria", "ru": "Болгария"},
    {"code": "CA", "en": "Canada", "ru": "Канада"},
    {"code": "CL", "en": "Chile", "ru": "Чили"},
    {"code": "CN", "en": "China", "ru": "Китай"},
    {"code": "CO", "en": "Colombia", "ru": "Колумбия"},
    {"code": "HR", "en": "Croatia", "ru": "Хорватия"},
    {"code": "CU", "en": "Cuba", "ru": "Куба"},
    {"code": "CY", "en": "Cyprus", "ru": "Кипр"},
    {"code": "CZ", "en": "Czech Republic", "ru": "Чехия"},
    {"code": "DK", "en": "Denmark", "ru": "Дания"},
    {"code": "EG", "en": "Egypt", "ru": "Египет"},
    {"code": "EE", "en": "Estonia", "ru": "Эстония"},
    {"code": "FI", "en": "Finland", "ru": "Финляндия"},
    {"code": "FR", "en": "France", "ru": "Франция"},
    {"code": "GE", "en": "Georgia", "ru": "Грузия"},
    {"code": "DE", "en": "Germany", "ru": "Германия"},
    {"code": "GR", "en": "Greece", "ru": "Греция"},
    {"code": "HU", "en": "Hungary", "ru": "Венгрия"},
    {"code": "IS", "en": "Iceland", "ru": "Исландия"},
    {"code": "IN", "en": "India", "ru": "Индия"},
    {"code": "ID", "en": "Indonesia", "ru": "Индонезия"},
    {"code": "IR", "en": "Iran", "ru": "Иран"},
    {"code": "IQ", "en": "Iraq", "ru": "Ирак"},
    {"code": "IE", "en": "Ireland", "ru": "Ирландия"},
    {"code": "IL", "en": "Israel", "ru": "Израиль"},
    {"code": "IT", "en": "Italy", "ru": "Италия"},
    {"code": "JP", "en": "Japan", "ru": "Япония"},
    {"code": "KZ", "en": "Kazakhstan", "ru": "Казахстан"},
    {"code": "KR", "en": "South Korea", "ru": "Южная Корея"},
    {"code": "LV", "en": "Latvia", "ru": "Латвия"},
    {"code": "LT", "en": "Lithuania", "ru": "Литва"},
    {"code": "LU", "en": "Luxembourg", "ru": "Люксембург"},
    {"code": "MY", "en": "Malaysia", "ru": "Малайзия"},
    {"code": "MX", "en": "Mexico", "ru": "Мексика"},
    {"code": "MD", "en": "Moldova", "ru": "Молдова"},
    {"code": "MC", "en": "Monaco", "ru": "Монако"},
    {"code": "MN", "en": "Mongolia", "ru": "Монголия"},
    {"code": "NL", "en": "Netherlands", "ru": "Нидерланды"},
    {"code": "NZ", "en": "New Zealand", "ru": "Новая Зеландия"},
    {"code": "NG", "en": "Nigeria", "ru": "Нигерия"},
    {"code": "NO", "en": "Norway", "ru": "Норвегия"},
    {"code": "PL", "en": "Poland", "ru": "Польша"},
    {"code": "PT", "en": "Portugal", "ru": "Португалия"},
    {"code": "RO", "en": "Romania", "ru": "Румыния"},
    {"code": "RU", "en": "Russia", "ru": "Россия"},
    {"code": "SA", "en": "Saudi Arabia", "ru": "Саудовская Аравия"},
    {"code": "RS", "en": "Serbia", "ru": "Сербия"},
    {"code": "SG", "en": "Singapore", "ru": "Сингапур"},
    {"code": "SK", "en": "Slovakia", "ru": "Словакия"},
    {"code": "SI", "en": "Slovenia", "ru": "Словения"},
    {"code": "ZA", "en": "South Africa", "ru": "ЮАР"},
    {"code": "ES", "en": "Spain", "ru": "Испания"},
    {"code": "SE", "en": "Sweden", "ru": "Швеция"},
    {"code": "CH", "en": "Switzerland", "ru": "Швейцария"},
    {"code": "TW", "en": "Taiwan", "ru": "Тайвань"},
    {"code": "TH", "en": "Thailand", "ru": "Таиланд"},
    {"code": "TR", "en": "Turkey", "ru": "Турция"},
    {"code": "UA", "en": "Ukraine", "ru": "Украина"},
    {"code": "AE", "en": "United Arab Emirates", "ru": "ОАЭ"},
    {"code": "GB", "en": "United Kingdom", "ru": "Великобритания"},
    {"code": "US", "en": "United States", "ru": "США"},
    {"code": "UZ", "en": "Uzbekistan", "ru": "Узбекистан"},
    {"code": "VN", "en": "Vietnam", "ru": "Вьетнам"},
]

# Regional Indicator Symbols for creating flag emojis
REGIONAL_INDICATORS = {
    'A': '🇦', 'B': '🇧', 'C': '🇨', 'D': '🇩', 'E': '🇪', 'F': '🇫', 'G': '🇬', 'H': '🇭', 'I': '🇮',
    'J': '🇯', 'K': '🇰', 'L': '🇱', 'M': '🇲', 'N': '🇳', 'O': '🇴', 'P': '🇵', 'Q': '🇶', 'R': '🇷',
    'S': '🇸', 'T': '🇹', 'U': '🇺', 'V': '🇻', 'W': '🇼', 'X': '🇽', 'Y': '🇾', 'Z': '🇿'
}

def get_flag_emoji(country_code):
    """Converts a two-letter country code to its flag emoji."""
    if not country_code or len(country_code) != 2:
        return '🏳️'
    char1, char2 = country_code[0].upper(), country_code[1].upper()
    if char1 in REGIONAL_INDICATORS and char2 in REGIONAL_INDICATORS:
        return REGIONAL_INDICATORS[char1] + REGIONAL_INDICATORS[char2]
    return '🏳️'

def find_countries(query: str):
    """
    A robust, manual search for countries from our static DB.
    """
    matches = []
    query_lower = query.lower()
    for country in COUNTRIES_DB:
        if query_lower in country["ru"].lower() or query_lower in country["en"].lower():
            matches.append(country)
    return matches

def get_country_by_code(code):
    """Gets a country dict by its official alpha_2 code."""
    for country in COUNTRIES_DB:
        if country["code"] == code:
            return country
    return None

def get_country_name_by_code(code, lang='ru'):
    """Retrieves a country name by its code."""
    country = get_country_by_code(code)
    if not country:
        return 'Неизвестная страна'
    
    if lang == 'ru':
        return country["ru"]
    return country["en"]
