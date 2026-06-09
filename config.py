# config.py
# =====================================================
# TENNIS QUANTITATIVE SCANNER - Configurazione Centrale
# =====================================================
# Modifica qui tutti i parametri senza toccare il codice

import os
from dotenv import load_dotenv
load_dotenv()

# --- API KEYS ---
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")         # The Odds API - piano PRO
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")         # RapidAPI - Tennis stats
BETFAIR_API_KEY = os.getenv("BETFAIR_API_KEY", "")   # Betfair Exchange API key
BETFAIR_USERNAME = os.getenv("BETFAIR_USERNAME", "")  # Username account Betfair amico
BETFAIR_PASSWORD = os.getenv("BETFAIR_PASSWORD", "")  # Password account Betfair amico
ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "")

# --- SOGLIE ALGORITMO ---
EV_MINIMO = 0.09         # Vantaggio minimo richiesto (9%)
EV_MAX = None             # Soglia massima EV (es. 0.60 esclude EV > 60%); None = nessun filtro
ODDS_MIN = 1.40           # Quota minima accettata (filtra le certezze)
ODDS_MAX = 6.00           # Quota massima accettata (filtra i longshot)
ODDS_MIN_VALUE = 1.80     # Quota minima per value bet (filtro Pro)
ODDS_MAX_VALUE = 4.00     # Quota massima per value bet (filtro Pro)

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
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN", "")  # legacy alias
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")      # token del bot
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # chat_id destinatario
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

# --- MODELLO DI PROBABILITÀ ---
# "elo"    → formula Elo standard (veloce, semplice, fallback sempre disponibile)
# "markov" → modello Markov point-by-point Barnett-Clarke (più granulare)
MODELLO = "markov"

# --- PARAMETRI MODELLO MARKOV (attivi solo se MODELLO = "markov") ---
# Adjustment contestuali: True = abilitato, False = neutro (delta = 0)
MARKOV_CPI_ABILITATO       = False  # Court Pace Index: nessuna fonte affidabile → off
MARKOV_FATICA_ESTESA       = True   # Fatica 14 giorni di set (invece dei soli 2gg)
MARKOV_TIMEZONE_ABILITATO  = False  # Penalità fuso orario: richiede dati geo torneo
MARKOV_ETA_SUPERFICIE      = True   # Over-33 penalità erba

# Court Pace Index per superficie (0 = neutro; +0.01 = +1% SPW su campi veloci).
# Lasciare a 0 finché non si trova una fonte CPI affidabile e validata.
MARKOV_CPI = {
    'hard':  0.0,
    'clay':  0.0,
    'grass': 0.0,
}
