# modules/odds_apiio.py
# =====================================================
# MODULO QUOTE - Odds-API.io
# Recupera quote reali da Bet365, Betano, Bwin IT, Eurobet IT
# =====================================================

import requests
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime, timezone

BOOKMAKERS = "Bet365,Betano,Bwin IT,Eurobet IT"

try:
    from config import ODDS_API_IO_KEY
except:
    ODDS_API_IO_KEY = ""

BASE_URL = "https://api.odds-api.io/v3"

def get_eventi_tennis(league_slug=None):
    """
    Recupera tutti gli eventi tennis pending (non ancora giocati).
    Se league_slug è specificato filtra per torneo.
    """
    params = {
        "apiKey": ODDS_API_IO_KEY,
        "sport": "tennis",
        "status": "pending"
    }
    if league_slug:
        params["league"] = league_slug

    try:
        resp = requests.get(f"{BASE_URL}/events", params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️  odds-api.io eventi: {resp.status_code} - {resp.text[:100]}")
            return []
    except Exception as e:
        print(f"❌ odds-api.io errore: {e}")
        return []

def get_quote_evento(event_id):
    """
    Recupera le quote ML (Match Winner) per un evento specifico.
    Restituisce la quota migliore disponibile tra i bookmaker.
    """
    params = {
        "apiKey": ODDS_API_IO_KEY,
        "eventId": event_id,
        "bookmakers": BOOKMAKERS
    }

    try:
        resp = requests.get(f"{BASE_URL}/odds", params=params, timeout=10)
        if resp.status_code != 200:
            return None, None

        data = resp.json()
        bookmakers = data.get("bookmakers", {})

        quote_home = []
        quote_away = []

        for bk_name, mercati in bookmakers.items():
            for mercato in mercati:
                if mercato.get("name") == "ML":
                    odds = mercato.get("odds", [])
                    if odds and len(odds) > 0:
                        try:
                            qh = float(odds[0].get("home", 0))
                            qa = float(odds[0].get("away", 0))
                            if qh > 1.0:
                                quote_home.append(qh)
                            if qa > 1.0:
                                quote_away.append(qa)
                        except:
                            pass

        # Prendi la quota migliore (più alta) disponibile
        q1 = round(max(quote_home), 3) if quote_home else None
        q2 = round(max(quote_away), 3) if quote_away else None

        return q1, q2

    except Exception as e:
        print(f"❌ odds-api.io quote errore: {e}")
        return None, None

def get_partite_con_quote_oggi():
    """
    Recupera tutte le partite tennis di oggi con le quote ML.
    Restituisce lista di dict pronti per lo scanner.
    """
    oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    eventi = get_eventi_tennis()

    partite = []
    for e in eventi:
        # Filtra solo partite di oggi
        data_evento = e.get("date", "")[:10]
        if data_evento != oggi:
            continue

        # Filtra solo singolari pro (escludi doppi)
        league = e.get("league", {}).get("name", "")
        if "Doubles" in league or "doubles" in league:
            continue
        if "ITF" in league:
            continue

        home_raw = e.get("home", "")
        away_raw = e.get("away", "")

        # Converti "Cognome, Nome" -> "Nome Cognome"
        def converti_nome(nome_raw):
            if "," in nome_raw:
                parti = nome_raw.split(",", 1)
                return f"{parti[1].strip()} {parti[0].strip()}"
            return nome_raw.strip()

        p1 = converti_nome(home_raw)
        p2 = converti_nome(away_raw)
        league_name = league
        event_id = e.get("id")

        if p1 and p2:
            partite.append({
                "id": event_id,
                "p1": p1,
                "p2": p2,
                "torneo": league_name,
                "superficie": "",  # odds-api.io non fornisce superficie
                "source": "odds-api.io"
            })

    return partite

if __name__ == "__main__":
    print("🔍 Test odds-api.io...")
    print(f"\n📅 Partite di oggi con quote:")
    partite = get_partite_con_quote_oggi()
    print(f"Trovate {len(partite)} partite\n")

    for p in partite[:5]:
        q1, q2 = get_quote_evento(p['id'])
        print(f"  {p['p1']} vs {p['p2']}")
        print(f"  Torneo: {p['torneo']}")
        print(f"  Quote: {q1} / {q2}")
        print()