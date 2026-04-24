# config.py
# =====================================================
# TENNIS QUANTITATIVE SCANNER - Configurazione Centrale
# =====================================================
# Modifica qui tutti i parametri senza toccare il codice

# --- API KEYS (da inserire quando le attivi) ---
ODDS_API_KEY = ""         # The Odds API - piano PRO
RAPIDAPI_KEY = ""         # RapidAPI - Tennis stats
BETFAIR_API_KEY = "rKaJW3IAXqecVcUf"      # Betfair Exchange API key
BETFAIR_USERNAME = "djpannocchia2@gmail.com"     # Username account Betfair amico
BETFAIR_PASSWORD = "Patong2013%"     # Password account Betfair amico
ODDS_API_IO_KEY = "97d4118388bad3aca1519306bcadbdf54fa4084eaacf97699c667b6e9986ed4a"

# --- SOGLIE ALGORITMO ---
EV_MINIMO = 0.05          # Vantaggio minimo richiesto (5%)
ODDS_MIN = 1.40           # Quota minima accettata (filtra le certezze)
ODDS_MAX = 6.00           # Quota massima accettata (filtra i longshot)

# --- FILTRI MATCH ---
SOLO_SINGOLARI = True     # Se True, esclude doppi dal live scanner
TOUR_ACCETTATI = [        # Tornei che vogliamo analizzare
    "ATP",
    "WTA",
    "ATP Challenger",
    "WTA 125k",
]

# --- BACKTESTING ---
PRO_BETS_FILE = "data/pro_bets.csv"
MATCH_RATE_TARGET = 0.80  # Soglia minima di coincidenza con i Pro (80%)

# --- NOTIFICHE (da configurare nella fase live) ---
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# --- DATI STORICI GRATUITI (Jeff Sackmann GitHub) ---
# Questi vengono scaricati automaticamente da data_loader.py
ATP_DATA_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"
WTA_DATA_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv"
ANNI_STORICI = list(range(2020, 2026))  # Anni da scaricare per il backtest
