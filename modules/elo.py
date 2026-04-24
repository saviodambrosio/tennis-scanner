# modules/elo.py
# =====================================================
# MOTORE ELO TENNISTICO v2
# - Elo separato per superficie (clay/hard/grass)
# - Decay temporale (partite recenti pesano di più)
# - K factor variabile per importanza torneo
# - Filtro minimo partite per superficie
# =====================================================

import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- Parametri Elo ---
ELO_INIZIALE = 1500
DATA_RIFERIMENTO = datetime(2026, 4, 22)
DECAY_SEMIVITA_GIORNI = 365
MIN_PARTITE_SUPERFICIE = 10  # minimo partite su superficie per usare Elo specifico

SUPERFICIE_MAP = {
    'clay': 'clay',
    'red clay': 'clay',
    'clay (red)': 'clay',
    'hard': 'hard',
    'hardcourt outdoor': 'hard',
    'hardcourt indoor': 'hard',
    'hard (indoor)': 'hard',
    'grass': 'grass',
    'carpet': 'hard',
}

def normalizza_superficie(s):
    if not s or str(s).lower() in ['nan', '']:
        return 'hard'
    return SUPERFICIE_MAP.get(str(s).strip().lower(), 'hard')

def calcola_expected(elo_a, elo_b):
    return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

def get_k_factor(tourney_level):
    if tourney_level in ['G']:
        return 40
    elif tourney_level in ['M', 'F']:
        return 36
    elif tourney_level in ['A']:
        return 32
    else:
        return 24

def calcola_peso_temporale(data_match, data_riferimento=DATA_RIFERIMENTO):
    if pd.isna(data_match):
        return 0.5
    if isinstance(data_match, pd.Timestamp):
        data_match = data_match.to_pydatetime()
    giorni = max(0, (data_riferimento - data_match).days)
    return 2 ** (-giorni / DECAY_SEMIVITA_GIORNI)

def costruisci_elo_da_csv(percorso_csv):
    df = pd.read_csv(percorso_csv, low_memory=False)

    df['tourney_date'] = pd.to_datetime(
        df['tourney_date'].astype(str), format='%Y%m%d', errors='coerce'
    )
    df = df.sort_values('tourney_date').reset_index(drop=True)

    ratings = {}
    ratings_sup = {}
    contatore_sup = {}   # {nome: {clay: n, hard: n, grass: n}}
    storico = []

    for _, row in df.iterrows():
        winner = row['winner_name']
        loser = row['loser_name']
        level = str(row.get('tourney_level', 'A'))
        superficie_raw = str(row.get('surface', 'Hard'))
        sup = normalizza_superficie(superficie_raw)
        data_match = row['tourney_date']

        for giocatore in [winner, loser]:
            if giocatore not in ratings:
                ratings[giocatore] = ELO_INIZIALE
            if giocatore not in ratings_sup:
                ratings_sup[giocatore] = {
                    'clay': ELO_INIZIALE,
                    'hard': ELO_INIZIALE,
                    'grass': ELO_INIZIALE
                }
            if giocatore not in contatore_sup:
                contatore_sup[giocatore] = {
                    'clay': 0,
                    'hard': 0,
                    'grass': 0
                }

        # --- ELO GENERALE con decay ---
        elo_w = ratings[winner]
        elo_l = ratings[loser]
        exp_w = calcola_expected(elo_w, elo_l)
        k = get_k_factor(level)
        peso = calcola_peso_temporale(data_match)

        ratings[winner] = round(elo_w + k * peso * (1 - exp_w), 1)
        ratings[loser] = round(elo_l + k * peso * (0 - (1 - exp_w)), 1)

        # --- ELO PER SUPERFICIE con decay ---
        elo_w_sup = ratings_sup[winner][sup]
        elo_l_sup = ratings_sup[loser][sup]
        exp_w_sup = calcola_expected(elo_w_sup, elo_l_sup)

        ratings_sup[winner][sup] = round(elo_w_sup + k * peso * (1 - exp_w_sup), 1)
        ratings_sup[loser][sup] = round(elo_l_sup + k * peso * (0 - (1 - exp_w_sup)), 1)

        # Aggiorna contatori
        contatore_sup[winner][sup] += 1
        contatore_sup[loser][sup] += 1

        storico.append({
            'data': data_match,
            'torneo': row.get('tourney_name', ''),
            'superficie': sup,
            'winner': winner,
            'loser': loser,
            'elo_winner_pre': round(elo_w, 1),
            'elo_loser_pre': round(elo_l, 1),
            'elo_winner_post': ratings[winner],
            'elo_loser_post': ratings[loser],
            'prob_attesa_winner': round(exp_w, 3),
            'peso_temporale': round(peso, 3),
        })

    return ratings, ratings_sup, contatore_sup, pd.DataFrame(storico)

def get_top_n(ratings, n=20):
    ordinati = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    return ordinati[:n]

if __name__ == "__main__":
    print("🎾 Costruzione database Elo ATP 2024...")
    file = 'data/storico/atp_2024.csv'

    if not os.path.exists(file):
        print(f"❌ File non trovato: {file}")
    else:
        ratings, ratings_sup, contatore_sup, storico = costruisci_elo_da_csv(file)

        print(f"✅ Processati {len(storico)} match")
        print(f"✅ Giocatori nel database: {len(ratings)}")

        print("\n🏆 TOP 20 ELO ATP (fine 2024):")
        print(f"{'Pos':<4} {'Giocatore':<25} {'Elo':<8} {'Clay':<8} {'Hard':<8} {'Grass':<8}")
        print("-" * 60)
        for i, (nome, elo) in enumerate(get_top_n(ratings, 20), 1):
            sup = ratings_sup.get(nome, {})
            cnt = contatore_sup.get(nome, {})
            print(f"{i:<4} {nome:<25} {elo:<8} "
                  f"{sup.get('clay',0):<8} {sup.get('hard',0):<8} {sup.get('grass',0):<8} "
                  f"(clay:{cnt.get('clay',0)} hard:{cnt.get('hard',0)} grass:{cnt.get('grass',0)})")