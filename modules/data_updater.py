# modules/data_updater.py
# =====================================================
# SCARICA RISULTATI STORICI DA ODDS-API.IO
# Costruisce CSV compatibili formato Sackmann
# per ATP e WTA 2025/2026
# =====================================================

import requests
import pandas as pd
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import ODDS_API_IO_KEY
except:
    ODDS_API_IO_KEY = ""

BASE_URL = "https://api.odds-api.io/v3"

# League slug -> info torneo (livello, superficie)
LEAGUE_MAP = {
    # ATP
    "atp-atp-australian-open-men-singles":          {"level": "G", "surface": "Hard"},
    "atp-atp-roland-garros-men-singles":            {"level": "G", "surface": "Clay"},
    "atp-atp-wimbledon-men-singles":                {"level": "G", "surface": "Grass"},
    "atp-atp-us-open-men-singles":                  {"level": "G", "surface": "Hard"},
    "atp-atp-indian-wells-men-singles":             {"level": "M", "surface": "Hard"},
    "atp-atp-miami-open-men-singles":               {"level": "M", "surface": "Hard"},
    "atp-atp-monte-carlo-men-singles":              {"level": "M", "surface": "Clay"},
    "atp-atp-madrid-spain-men-singles":             {"level": "M", "surface": "Clay"},
    "atp-atp-rome-men-singles":                     {"level": "M", "surface": "Clay"},
    "atp-atp-canada-men-singles":                   {"level": "M", "surface": "Hard"},
    "atp-atp-cincinnati-men-singles":               {"level": "M", "surface": "Hard"},
    "atp-atp-shanghai-men-singles":                 {"level": "M", "surface": "Hard"},
    "atp-atp-paris-men-singles":                    {"level": "M", "surface": "Hard"},
    "atp-atp-dubai-men-singles":                    {"level": "A", "surface": "Hard"},
    "atp-atp-rotterdam-men-singles":                {"level": "A", "surface": "Hard"},
    "atp-atp-barcelona-men-singles":                {"level": "A", "surface": "Clay"},
    "atp-atp-hamburg-men-singles":                  {"level": "A", "surface": "Clay"},
    "atp-atp-halle-men-singles":                    {"level": "A", "surface": "Grass"},
    "atp-atp-queens-club-men-singles":              {"level": "A", "surface": "Grass"},
    "atp-atp-washington-men-singles":               {"level": "A", "surface": "Hard"},
    "atp-atp-vienna-men-singles":                   {"level": "A", "surface": "Hard"},
    "atp-atp-basel-men-singles":                    {"level": "A", "surface": "Hard"},
    # WTA
    "wta-wta-australian-open-women-singles":        {"level": "G", "surface": "Hard"},
    "wta-wta-roland-garros-women-singles":          {"level": "G", "surface": "Clay"},
    "wta-wta-wimbledon-women-singles":              {"level": "G", "surface": "Grass"},
    "wta-wta-us-open-women-singles":                {"level": "G", "surface": "Hard"},
    "wta-wta-indian-wells-women-singles":           {"level": "P", "surface": "Hard"},
    "wta-wta-miami-open-women-singles":             {"level": "P", "surface": "Hard"},
    "wta-wta-madrid-spain-women-singles":           {"level": "P", "surface": "Clay"},
    "wta-wta-rome-women-singles":                   {"level": "P", "surface": "Clay"},
    "wta-wta-canada-women-singles":                 {"level": "P", "surface": "Hard"},
    "wta-wta-cincinnati-women-singles":             {"level": "P", "surface": "Hard"},
    "wta-wta-dubai-women-singles":                  {"level": "A", "surface": "Hard"},
    "wta-wta-doha-women-singles":                   {"level": "A", "surface": "Hard"},
}

def get_eventi_league(league_slug, status="settled"):
    """Scarica tutti gli eventi di una lega."""
    params = {
        "apiKey": ODDS_API_IO_KEY,
        "sport": "tennis",
        "league": league_slug,
        "status": status
    }
    try:
        resp = requests.get(f"{BASE_URL}/events", params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  ⚠️  {league_slug}: {resp.status_code}")
            return []
    except Exception as e:
        print(f"  ❌ {league_slug}: {e}")
        return []

def converti_nome(nome_raw):
    """Converti 'Cognome, Nome' -> 'Nome Cognome'"""
    if not nome_raw:
        return ""
    if "," in nome_raw:
        parti = nome_raw.split(",", 1)
        return f"{parti[1].strip()} {parti[0].strip()}"
    return nome_raw.strip()

def eventi_to_dataframe(eventi, league_info):
    """Converte lista eventi API in DataFrame formato Sackmann."""
    righe = []
    for e in eventi:
        if e.get("status") != "settled":
            continue

        scores = e.get("scores", {})
        home_sets = scores.get("home", 0)
        away_sets = scores.get("away", 0)

        if home_sets == 0 and away_sets == 0:
            continue

        # Determina winner e loser
        if home_sets > away_sets:
            winner = converti_nome(e.get("home", ""))
            loser = converti_nome(e.get("away", ""))
        else:
            winner = converti_nome(e.get("away", ""))
            loser = converti_nome(e.get("home", ""))

        if not winner or not loser:
            continue

        # Data nel formato Sackmann (YYYYMMDD)
        data_raw = e.get("date", "")[:10].replace("-", "")

        # Nome torneo dalla lega
        torneo = e.get("league", {}).get("name", "")

        righe.append({
            "tourney_id": f"api_{e.get('id', '')}",
            "tourney_name": torneo,
            "surface": league_info.get("surface", "Hard"),
            "draw_size": 64,
            "tourney_level": league_info.get("level", "A"),
            "tourney_date": data_raw,
            "match_num": e.get("id", 0),
            "winner_id": 0,
            "winner_seed": "",
            "winner_entry": "",
            "winner_name": winner,
            "winner_hand": "",
            "winner_ht": "",
            "winner_ioc": "",
            "winner_age": "",
            "loser_id": 0,
            "loser_seed": "",
            "loser_entry": "",
            "loser_name": loser,
            "loser_hand": "",
            "loser_ht": "",
            "loser_ioc": "",
            "loser_age": "",
            "score": "",
            "best_of": 3,
            "round": "",
            "minutes": "",
        })

    return pd.DataFrame(righe)

def scarica_storico_anno(anno, output_dir="data/storico"):
    """
    Scarica tutti i risultati ATP e WTA per un anno
    e li salva in CSV formato Sackmann.
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📥 Download risultati {anno}...")
    print(f"{'='*50}")

    tutti_atp = []
    tutti_wta = []

    for slug, info in LEAGUE_MAP.items():
        is_wta = slug.startswith("wta-")
        tipo = "WTA" if is_wta else "ATP"

        print(f"  📡 {tipo} - {slug.split('-', 2)[-1]}...")
        eventi = get_eventi_league(slug)
        time.sleep(0.5)  # rate limit

        if not eventi:
            print(f"     → 0 eventi")
            continue

        # Filtra per anno
        eventi_anno = [
            e for e in eventi
            if e.get("date", "")[:4] == str(anno)
        ]

        if not eventi_anno:
            print(f"     → 0 eventi per {anno}")
            continue

        df = eventi_to_dataframe(eventi_anno, info)
        print(f"     → {len(df)} partite")

        if is_wta:
            tutti_wta.append(df)
        else:
            tutti_atp.append(df)

    # Salva ATP
    if tutti_atp:
        df_atp = pd.concat(tutti_atp, ignore_index=True)
        df_atp = df_atp.sort_values("tourney_date").reset_index(drop=True)
        path_atp = os.path.join(output_dir, f"atp_{anno}_apiio.csv")
        df_atp.to_csv(path_atp, index=False)
        print(f"\n✅ ATP {anno}: {len(df_atp)} partite → {path_atp}")
    else:
        print(f"\n⚠️  ATP {anno}: nessuna partita trovata")

    # Salva WTA
    if tutti_wta:
        df_wta = pd.concat(tutti_wta, ignore_index=True)
        df_wta = df_wta.sort_values("tourney_date").reset_index(drop=True)
        path_wta = os.path.join(output_dir, f"wta_{anno}_apiio.csv")
        df_wta.to_csv(path_wta, index=False)
        print(f"✅ WTA {anno}: {len(df_wta)} partite → {path_wta}")
    else:
        print(f"⚠️  WTA {anno}: nessuna partita trovata")

    return tutti_atp, tutti_wta

if __name__ == "__main__":
    print("🎾 TENNIS DATA UPDATER")
    print("Scarica risultati storici da odds-api.io\n")

    # Scarica 2025 e 2026
    for anno in [2025, 2026]:
        scarica_storico_anno(anno)

    print("\n✅ Download completato!")
    print("Ora aggiorna scanner.py per caricare i nuovi file.")