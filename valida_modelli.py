"""
Confronto di validazione: Elo vs Markov vs quote di chiusura.

Metodologia:
  1. Carica i match storici con risultato noto da pro_bets.csv e/o storico ATP
  2. Per ogni match, calcola:
       - Prob Elo   = 1/(1+10^(-(elo_A-elo_B)/400))
       - Prob Markov = calcola_probabilita_markov(elo_A, elo_B, surface)
       - Prob implicita chiusura = 1/quota_chiusura (de-vigorata)
  3. Metriche: Brier Score, Log-Loss, correlazione con esito reale
  4. Stampa la tabella di confronto
"""

import sys
import os
import pandas as pd
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.markov import calcola_probabilita_markov, AVG_ELO_TA
from modules.signals import prob_da_elo
from modules.elo_tennisabstract import carica_elo_aggiornato, trova_giocatore_ta

# ─── Utility ───────────────────────────────────────────────────────────────────

def brier_score(probs, outcomes):
    """Brier Score: ↓ è meglio (0 = perfetto)."""
    return sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / len(probs)


def log_loss(probs, outcomes):
    """Log-Loss: ↓ è meglio."""
    eps = 1e-9
    return -sum(o * math.log(p + eps) + (1 - o) * math.log(1 - p + eps)
                for p, o in zip(probs, outcomes)) / len(probs)


def devig_quota(q1, q2):
    """Rimuove il vig dalla quota e ritorna la probabilità 'vera' di P1."""
    if not q1 or not q2 or q1 <= 1 or q2 <= 1:
        return None
    p1_raw = 1.0 / q1
    p2_raw = 1.0 / q2
    total = p1_raw + p2_raw
    return p1_raw / total  # devigged P(P1 win)


def normalizza_superficie(s):
    mappa = {'clay': 'clay', 'hard': 'hard', 'grass': 'grass',
             'red clay': 'clay', 'clay (red)': 'clay',
             'hardcourt outdoor': 'hard', 'grass (indoor)': 'grass'}
    return mappa.get(str(s).strip().lower(), 'hard')


# ─── Carica dati storici ────────────────────────────────────────────────────────

def carica_value_bets_excel(path="data/value_bets_log.xlsx"):
    """Carica il log delle value bet con quota apertura/chiusura e esito."""
    if not os.path.exists(path):
        print(f"  ⚠️  File non trovato: {path}")
        return pd.DataFrame()
    wb_df = pd.read_excel(path, sheet_name="Value Bets Log")
    return wb_df


def carica_pro_bets(path="data/pro_bets.csv"):
    """Carica le giocate dei Pro per confronto benchmark."""
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


# ─── Funzione principale ────────────────────────────────────────────────────────

def valida(n_righe_max=200):
    print("=" * 70)
    print("  VALIDAZIONE: ELO vs MARKOV vs CLOSING LINE")
    print("=" * 70)

    # Carica Elo
    print("\n⚙️  Caricamento Elo Tennis Abstract (cache)...")
    ratings_ta = carica_elo_aggiornato()
    if not ratings_ta:
        print("  ❌ Impossibile caricare Elo — usa cache locale")
        return

    # Carica storico value bets con esiti
    df_log = carica_value_bets_excel()
    if df_log.empty:
        print("  ⚠️  Nessuna value bet con esito trovata nel log Excel")
        df_log = pd.DataFrame()

    # Filtra solo righe con esito W/L, quota chiusura e dati sufficienti
    col_maps = {
        'player': '🎯 PUNTA SU',
        'opponent': 'Avversario',
        'surface': 'Superficie',
        'quota_apertura': 'Quota Apertura',
        'quota_chiusura': 'Quota Chiusura',
        'esito': 'Esito',
    }

    df_val = pd.DataFrame()
    if not df_log.empty:
        needed = [col_maps['player'], col_maps['opponent'], col_maps['esito'],
                  col_maps['quota_chiusura']]
        missing = [c for c in needed if c not in df_log.columns]
        if not missing:
            mask = df_log[col_maps['esito']].isin(['W', 'L'])
            mask &= df_log[col_maps['quota_chiusura']].notna()
            mask &= df_log[col_maps['quota_chiusura']] != ''
            df_val = df_log[mask].copy().head(n_righe_max)

    # Fallback: usa storico ATP con probabilità sintetica se non ci sono dati reali
    if df_val.empty:
        print("\n  ℹ️  Nessun match con quota chiusura disponibile.")
        print("  Genero confronto sintetico su match simulati (Elo differenziali noti).")
        _valida_sintetico(ratings_ta)
        return

    print(f"\n  📊 Match con esito + quota chiusura: {len(df_val)}\n")

    righe_elo, righe_markov, righe_cl = [], [], []
    esiti, match_labels = [], []

    for _, row in df_val.iterrows():
        player_raw = str(row.get(col_maps['player'], '')).replace('✅ ', '').strip()
        opp_raw = str(row.get(col_maps['opponent'], '')).strip()
        sup = normalizza_superficie(row.get(col_maps['surface'], 'hard'))
        esito = row.get(col_maps['esito'], '')
        q_chiusura = row.get(col_maps['quota_chiusura'], None)
        q_apertura = row.get(col_maps['quota_apertura'], None)

        if esito not in ('W', 'L'):
            continue

        n1, r1 = trova_giocatore_ta(player_raw, ratings_ta)
        n2, r2 = trova_giocatore_ta(opp_raw, ratings_ta)

        if not r1 or not r2:
            continue

        e1 = r1.get(sup, r1['elo'])
        e2 = r2.get(sup, r2['elo'])

        prob_elo = prob_da_elo(e1, e2)
        prob_mkov = calcola_probabilita_markov(e1, e2, sup, best_of=3)
        outcome = 1 if esito == 'W' else 0

        # Prob implicita quota chiusura (devigged se disponibile quota avversario)
        prob_cl = None
        try:
            q_cl = float(q_chiusura)
            # Senza la quota dell'avversario, usa solo 1/q (vigorata)
            prob_cl = 1.0 / q_cl if q_cl > 1 else None
        except (TypeError, ValueError):
            pass

        righe_elo.append(prob_elo)
        righe_markov.append(prob_mkov)
        if prob_cl:
            righe_cl.append(prob_cl)
        esiti.append(outcome)
        match_labels.append(f"{player_raw[:15]:15s} vs {opp_raw[:15]:15s} [{sup}]")

    if not righe_elo:
        print("  ❌ Nessun match con entrambi i giocatori trovati nell'Elo.")
        _valida_sintetico(ratings_ta)
        return

    _stampa_confronto(righe_elo, righe_markov, righe_cl if righe_cl else None,
                      esiti, match_labels)


def _stampa_confronto(probs_elo, probs_mkov, probs_cl, esiti, labels):
    """Stampa tabella dettagliata e metriche aggregate."""
    n = len(probs_elo)
    print(f"{'Match':<35} {'Elo':>6} {'Markov':>8} {'CL':>6} {'Esito':>6} {'Diff':>8}")
    print("-" * 75)
    for i in range(min(n, 30)):  # mostra al più 30 righe
        cl_str = f"{probs_cl[i]:.3f}" if probs_cl else "  N/A"
        diff = probs_mkov[i] - probs_elo[i]
        print(f"{labels[i]:<35} {probs_elo[i]:.3f}   {probs_mkov[i]:.4f}  {cl_str}  "
              f"{'W' if esiti[i] else 'L':>5}   {diff:+.4f}")

    if n > 30:
        print(f"  ... altri {n-30} match ...")

    # Metriche
    bs_elo  = brier_score(probs_elo, esiti)
    bs_mkov = brier_score(probs_mkov, esiti)
    ll_elo  = log_loss(probs_elo, esiti)
    ll_mkov = log_loss(probs_mkov, esiti)

    print("\n" + "=" * 70)
    print(f"  METRICHE SU {n} MATCH")
    print(f"  {'Metrica':<20} {'Elo':>10} {'Markov':>10} {'Δ (Markov-Elo)':>16}")
    print(f"  {'-'*56}")
    print(f"  {'Brier Score':20s} {bs_elo:>10.5f} {bs_mkov:>10.5f} {bs_mkov-bs_elo:>+16.5f}")
    print(f"  {'Log-Loss':20s} {ll_elo:>10.5f} {ll_mkov:>10.5f} {ll_mkov-ll_elo:>+16.5f}")

    win_rate = sum(esiti) / len(esiti)
    print(f"\n  Win rate nel campione: {win_rate:.1%}")

    # Confronto con closing line se disponibile
    if probs_cl and len(probs_cl) == n:
        bs_cl  = brier_score(probs_cl, esiti)
        ll_cl  = log_loss(probs_cl, esiti)
        print(f"\n  {'Closing Line':20s} {bs_cl:>10.5f}   (Log-Loss: {ll_cl:.5f})")
        print(f"\n  Modello più vicino alla CL:")
        diff_elo_cl  = sum(abs(e - c) for e, c in zip(probs_elo, probs_cl)) / n
        diff_mkov_cl = sum(abs(m - c) for m, c in zip(probs_mkov, probs_cl)) / n
        print(f"    MAE Elo  vs CL: {diff_elo_cl:.4f}")
        print(f"    MAE Markov vs CL: {diff_mkov_cl:.4f}")
        winner = "Markov" if diff_mkov_cl < diff_elo_cl else "Elo"
        print(f"\n  ✅ Modello più vicino alla closing line: {winner}")

    print("=" * 70)


def _valida_sintetico(ratings_ta):
    """
    Confronto sintetico su match reali dalla cache Elo
    (senza quote: mostra solo le differenze Elo vs Markov).
    """
    print("\n  📊 CONFRONTO SINTETICO (senza quote reali)")
    print(f"  {'Match':<40} {'Elo':>6} {'Markov':>8} {'Diff':>8} {'Superficie':>10}")
    print(f"  {'-'*76}")

    casi_test = [
        ("Jannik Sinner", "Carlos Alcaraz", "hard"),
        ("Jannik Sinner", "Carlos Alcaraz", "clay"),
        ("Carlos Alcaraz", "Alexander Zverev", "clay"),
        ("Novak Djokovic", "Andy Murray", "grass"),
        ("Jannik Sinner", "Holger Rune", "hard"),
        ("Stefanos Tsitsipas", "Grigor Dimitrov", "clay"),
        ("Casper Ruud", "Taylor Fritz", "clay"),
        ("Carlos Alcaraz", "Daniil Medvedev", "grass"),
        ("Aryna Sabalenka", "Iga Swiatek", "hard"),
        ("Iga Swiatek", "Coco Gauff", "clay"),
    ]

    for p1_name, p2_name, surf in casi_test:
        _, r1 = trova_giocatore_ta(p1_name, ratings_ta)
        _, r2 = trova_giocatore_ta(p2_name, ratings_ta)
        if not r1 or not r2:
            print(f"  ⚠️  Non trovati: {p1_name} / {p2_name}")
            continue
        e1 = r1.get(surf, r1['elo'])
        e2 = r2.get(surf, r2['elo'])
        p_elo  = prob_da_elo(e1, e2)
        p_mkov = calcola_probabilita_markov(e1, e2, surf, best_of=3)
        diff = p_mkov - p_elo
        label = f"{p1_name[:18]} vs {p2_name[:18]}"
        print(f"  {label:<40} {p_elo:.3f}   {p_mkov:.4f}  {diff:>+8.4f}  {surf:>10}")

    print("\n  ℹ️  Per confronto con closing line: popola le colonne")
    print("      'Quota Chiusura' nel file data/value_bets_log.xlsx")
    print("      e ri-esegui questo script.")


if __name__ == "__main__":
    valida()
