
# --- Constants and Configuration ---

GRACEFIELD_GOLD = "#C7A64F"
GRACEFIELD_DARK = "#2C3E50"
GRACEFIELD_GREEN = "#166347"
GRACEFIELD_SKY = "#4A90E2"
GRACEFIELD_ORANGE = "#E67E22"

BRAND_COLORS = [GRACEFIELD_GREEN, GRACEFIELD_GOLD, GRACEFIELD_DARK, GRACEFIELD_SKY, GRACEFIELD_ORANGE]

MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

SUBSCRIBER_LOCATIONS = [
    'Tuck-shop', 'HELIUM', 'NBIC 1', 'NBIC 2', 'Gravitas Canteen',
    'Cedar A', 'Cedar B', 'Rosewood A', 'Rosewood B', 'DIC', 'Western Lodge'
]

GRAVITAS_REVENUE_SOURCES = [
    'Gravitas New Meter', 'Engineering Yard', 'Providus', '9mobile'
]

METER_TO_NAME = {
    23220035721: "Rosewood A",
    23220035788: "Rosewood B",
    4293684496:  "Cedar A",
    4293682284:  "Cedar B",
    4293683936:  "NBIC 1",
    4293682789:  "NBIC 2",
    4293682193:  "Head Office",
    4293683571:  "Engineering Yard",
    4293683993:  "HELIUM",
    4293682201:  "DIC",
    120230672145: "Tuckshop Water",
    4293684066: "Tuck-shop"
}

# Weekday mapping: 0=Monday, 1=Tuesday, ... 6=Sunday
DAILY_SCHEDULE = {
    0: {"80kva": 11, "55kva": 12},
    1: {"80kva": 11, "55kva": 12},
    2: {"80kva": 11, "55kva": 12},
    3: {"80kva": 11, "55kva": 12},
    4: {"80kva": 11, "55kva": 19.5},
    5: {"55kva": 12},
    6: {"200kva": 7, "55kva": 12}
}
