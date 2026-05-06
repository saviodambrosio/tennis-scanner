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
EV_MINIMO = 0.09         # Vantaggio minimo richiesto (5%)
EV_MAX = None             # Soglia massima EV (es. 0.60 esclude EV > 60%); None = nessun filtro
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

# --- NOTIFICHE TELEGRAM ---
TELEGRAM_BOT_TOKEN = ""      # legacy alias (non usato dai nuovi moduli)
TELEGRAM_TOKEN = "8711682098:AAGlH3f9IBjjduy2Nt5NvUWyWM6IZ9xoI4s"           # token del bot (da inserire per attivare)
TELEGRAM_CHAT_ID = "483228005"         # chat_id destinatario
TELEGRAM_ABILITATO = True    # interruttore master: True = invia, False = solo console

# --- SCHEDULER ---
SCHEDULER_ORA_MATTINA = "08:30"   # orario scansione mattutina
SCHEDULER_ORA_SERA    = "21:00"   # orario scansione serale
SCHEDULER_ABILITATO   = False     # interruttore master: True = attiva loop scheduler

# --- DATI STORICI GRATUITI (Jeff Sackmann GitHub) ---
# Questi vengono scaricati automaticamente da data_loader.py
ATP_DATA_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{year}.csv"
WTA_DATA_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{year}.csv"
ANNI_STORICI = list(range(2020, 2026))  # Anni da scaricare per il backtest
