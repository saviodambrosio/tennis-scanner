# modules/odds_apiio.py
# =====================================================
# MODULO QUOTE - Odds-API.io
# Recupera quote reali da Bet365, Betano, Bwin IT, Eurobet IT
# =====================================================

import requests
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime, timezone, timedelta

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

        pairs = []  # (home_odds, away_odds) per bookmaker, solo se entrambe valide

        for bk_name, mercati in bookmakers.items():
            for mercato in mercati:
                if mercato.get("name") == "ML":
                    odds = mercato.get("odds", [])
                    if odds and len(odds) > 0:
                        try:
                            qh = float(odds[0].get("home", 0))
                            qa = float(odds[0].get("away", 0))
                            if qh > 1.0 and qa > 1.0:
                                pairs.append((qh, qa))
                        except:
                            pass

        if not pairs:
            return None, None

        # In tennis non esiste vero home/away: bookmaker diversi possono
        # invertire la convenzione per lo stesso evento. Esempio: Bet365
        # mette Nava come "home" e Bwin mette Vacherot come "home".
        # Correzione: determina la convenzione di maggioranza e normalizza
        # le coppie di minoranza prima di aggregare.
        home_favored_count = sum(1 for qh, qa in pairs if qh < qa)
        majority_home_is_favorite = home_favored_count > len(pairs) / 2

        quote_home = []
        quote_away = []
        for qh, qa in pairs:
            if (qh < qa) != majority_home_is_favorite:
                qh, qa = qa, qh  # bookmaker con home/away invertito
            quote_home.append(qh)
            quote_away.append(qa)

        q1 = round(max(quote_home), 3)
        q2 = round(max(quote_away), 3)
        return q1, q2

    except Exception as e:
        print(f"❌ odds-api.io quote errore: {e}")
        return None, None

def get_partite_con_quote_oggi():
    """
    Recupera tutte le partite tennis dei prossimi 1-4 giorni (domani fino a oggi+4).
    Restituisce lista di dict pronti per lo scanner.
    """
    ora_utc = datetime.now(timezone.utc)

    def converti_nome(nome_raw):
        if "," in nome_raw:
            parti = nome_raw.split(",", 1)
            return f"{parti[1].strip()} {parti[0].strip()}"
        return nome_raw.strip()

    partite = []
    ids_visti = set()

    for delta in range(1, 5):
        giorno = ora_utc + timedelta(days=delta)
        inizio = giorno.replace(hour=0, minute=0, second=0, microsecond=0)
        fine = giorno.replace(hour=23, minute=59, second=59, microsecond=0)

        params = {
            "apiKey": ODDS_API_IO_KEY,
            "sport": "tennis",
            "status": "pending",
            "commenceTimeFrom": inizio.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "commenceTimeTo": fine.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        try:
            resp = requests.get(f"{BASE_URL}/events", params=params, timeout=10)
            if resp.status_code != 200:
                print(f"⚠️  odds-api.io giorno+{delta}: {resp.status_code} - {resp.text[:100]}")
                continue
            eventi = resp.json()
        except Exception as e:
            print(f"❌ odds-api.io errore giorno+{delta}: {e}")
            continue

        data_label = inizio.strftime("%Y-%m-%d")
        trovate_giorno = 0

        for e in eventi:
            event_id = e.get("id")
            if event_id in ids_visti:
                continue

            league = e.get("league", {}).get("name", "")
            if "Doubles" in league or "doubles" in league:
                continue
            if "ITF" in league:
                continue

            home_raw = e.get("home", "")
            away_raw = e.get("away", "")
            p1 = converti_nome(home_raw)
            p2 = converti_nome(away_raw)

            if p1 and p2:
                ids_visti.add(event_id)
                trovate_giorno += 1
                partite.append({
                    "id": event_id,
                    "p1": p1,
                    "p2": p2,
                    "torneo": league,
                    "superficie": "",
                    "source": "odds-api.io",
                    "data_partita": data_label,
                })

        print(f"  [+] {data_label}: {trovate_giorno} partite trovate")

    return partite

def get_quote_handicap_evento(event_id):
    """
    Recupera le quote handicap games (spreads) per un evento.
    Restituisce lista di {handicap: float, quota_home: float, quota_away: float}
    dove handicap è il valore assegnato alla home (es. -3.5 per il favorito home).
    """
    params = {
        "apiKey": ODDS_API_IO_KEY,
        "eventId": event_id,
        "bookmakers": BOOKMAKERS,
        "market": "spreads",
    }

    try:
        resp = requests.get(f"{BASE_URL}/odds", params=params, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        bookmakers = data.get("bookmakers", {})

        # Accumula per linea: handicap_home -> [(q_home, q_away), ...]
        linee: dict = {}

        NOMI_MERCATO = {"spreads", "ah", "handicap", "spread", "spread (games)", "asian handicap"}

        for bk_name, mercati in bookmakers.items():
            for mercato in mercati:
                if str(mercato.get("name", "")).lower() not in NOMI_MERCATO:
                    continue
                odds = mercato.get("odds", [])
                if not odds:
                    continue

                # Formato 1: [{handicap: -3.5, home: 1.85, away: 1.95}, ...]
                if isinstance(odds[0], dict) and ("home" in odds[0] or "away" in odds[0]):
                    for o in odds:
                        h_val = o.get("hdp", o.get("handicap", o.get("point", o.get("line", o.get("spread")))))
                        if h_val is None:
                            continue
                        try:
                            h = float(h_val)
                            qh = float(o.get("home", 0))
                            qa = float(o.get("away", 0))
                            if qh > 1.0 and qa > 1.0:
                                linee.setdefault(h, []).append((qh, qa))
                        except (TypeError, ValueError):
                            pass

                # Formato 2: [{"side": "home", "handicap": -3.5, "value": 1.85}, ...]
                else:
                    home_odds: dict = {}
                    away_odds: dict = {}
                    for o in odds:
                        side = str(o.get("side", o.get("name", ""))).lower()
                        h_val = o.get("handicap", o.get("point", o.get("line")))
                        val = o.get("value", o.get("odds", o.get("price")))
                        if h_val is None or val is None:
                            continue
                        try:
                            h = float(h_val)
                            q = float(val)
                            if q <= 1.0:
                                continue
                            if "home" in side or side == "1":
                                home_odds[h] = q
                            elif "away" in side or side == "2":
                                away_odds[h] = q
                        except (TypeError, ValueError):
                            pass
                    for h, qh in home_odds.items():
                        # away usa -h come handicap speculare
                        qa = away_odds.get(-h)
                        if qa:
                            linee.setdefault(h, []).append((qh, qa))

        if not linee:
            return []

        result = []
        for h, pairs in linee.items():
            q_home = max(qh for qh, _ in pairs)
            q_away = max(qa for _, qa in pairs)
            result.append({
                "handicap": h,
                "quota_home": round(q_home, 3),
                "quota_away": round(q_away, 3),
            })

        return sorted(result, key=lambda x: x["handicap"])

    except Exception as e:
        print(f"❌ odds-api.io handicap errore: {e}")
        return []


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