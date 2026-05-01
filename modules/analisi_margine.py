# modules/analisi_margine.py
import os
import sys
import re
import pandas as pd
from collections import defaultdict

# Forza UTF-8 su Windows per supportare emoji nei moduli importati
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from modules.elo_tennisabstract import carica_elo_aggiornato, trova_giocatore_ta

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'storico')
RISULTATI_RECENTI = os.path.join(DATA_DIR, 'risultati_recenti.csv')
ATP_2025 = os.path.join(DATA_DIR, 'atp_2025_tml.csv')

FASCE = [
    (0,   50,  "0-50"),
    (50,  100, "50-100"),
    (100, 150, "100-150"),
    (150, 200, "150-200"),
    (200, float('inf'), "200+"),
]
ORDINE_FASCE = [label for _, _, label in FASCE]


def _fascia(diff):
    for low, high, label in FASCE:
        if low <= diff < high:
            return label
    return "200+"


def parse_score(score_str):
    """
    Parsa '6-3 6-4' o '6-4 4-6 6-3'.
    Ritorna (games_winner, games_loser, n_set, is_retirement) o None se non parsabile.
    """
    if not isinstance(score_str, str) or not score_str.strip():
        return None

    s = score_str.strip().upper()
    is_ret = bool(re.search(r'\bRET\b|\bDEF\b', s))

    # W/O e simili: nessun game giocato
    if re.search(r'\bW/?O\b|WALKOVER', s):
        return None

    s_clean = re.sub(r'\b(RET|DEF)\b', '', s).strip()
    sets = re.findall(r'(\d+)-(\d+)(?:\(\d+\))?', s_clean)
    if not sets:
        return None

    w_games = sum(int(w) for w, l in sets)
    l_games = sum(int(l) for w, l in sets)
    return w_games, l_games, len(sets), is_ret


def analizza_margine():
    print("=" * 62)
    print("  ANALISI MARGINE GAMES PER FASCIA ELO")
    print("=" * 62)

    # --- Elo ---
    print("\n[ELO] Caricamento ratings Elo...")
    ratings = carica_elo_aggiornato()
    print(f"   {len(ratings)} giocatori in cache")

    # --- Dati partite ---
    print("\n[FILE] Caricamento file partite...")
    df_atp = pd.read_csv(ATP_2025)
    print(f"   atp_2025_tml.csv     : {len(df_atp):>5} partite  (con score)")

    df_rec = pd.read_csv(RISULTATI_RECENTI)
    print(f"   risultati_recenti.csv: {len(df_rec):>5} partite  (senza score - non usate per margine)")

    # --- Loop analisi ---
    print(f"\n[ANALISI] Partite con score su atp_2025_tml.csv...")

    fasce_data = defaultdict(lambda: {
        'n': 0,
        'margini_fav': [],          # signed: positivo se fav vince
        'favorito_vince': 0,
        'n_sets_dist': defaultdict(int),
        'punteggi_str': defaultdict(int),
    })

    cnt_ok = cnt_no_elo = cnt_no_score = cnt_ret = 0

    for _, row in df_atp.iterrows():
        winner = str(row['winner_name'])
        loser  = str(row['loser_name'])
        score  = row.get('score', None)
        surface = str(row.get('surface', 'Hard')).lower()
        if surface not in ('hard', 'clay', 'grass'):
            surface = 'hard'

        parsed = parse_score(score)
        if parsed is None:
            cnt_no_score += 1
            continue
        w_g, l_g, n_sets, is_ret = parsed

        # Escludi ritiri: risultato incompleto
        if is_ret:
            cnt_ret += 1
            continue

        # Lookup Elo superficie
        _, elo_w = trova_giocatore_ta(winner, ratings)
        _, elo_l = trova_giocatore_ta(loser, ratings)
        if not elo_w or not elo_l:
            cnt_no_elo += 1
            continue

        ew = elo_w.get(surface, elo_w['elo'])
        el = elo_l.get(surface, elo_l['elo'])
        diff = abs(ew - el)

        # Margine dal punto di vista del favorito Elo
        if ew >= el:
            # favorito = winner
            favorito_ha_vinto = True
            margine_fav = w_g - l_g     # positivo
        else:
            # favorito = loser (ha perso)
            favorito_ha_vinto = False
            margine_fav = l_g - w_g     # negativo

        fascia = _fascia(diff)
        d = fasce_data[fascia]
        d['n'] += 1
        d['margini_fav'].append(margine_fav)
        if favorito_ha_vinto:
            d['favorito_vince'] += 1
        d['n_sets_dist'][n_sets] += 1

        # Punteggio normalizzato winner-loser per distribuzione
        sets_raw = re.findall(r'(\d+)-(\d+)(?:\(\d+\))?',
                              re.sub(r'\b(RET|DEF)\b', '', str(score).upper()))
        score_key = ' '.join(f"{w}-{l}" for w, l in sets_raw)
        d['punteggi_str'][score_key] += 1

        cnt_ok += 1

    print(f"   OK  Processate:       {cnt_ok}")
    print(f"   --  Ritiri esclusi:   {cnt_ret}")
    print(f"   !!  Senza Elo:        {cnt_no_elo}")
    print(f"   !!  Score non valido: {cnt_no_score}")

    # --- Stampa risultati per fascia ---
    print("\n" + "=" * 62)
    print("  RISULTATI PER FASCIA DI DIFFERENZA ELO (superficie)")
    print("=" * 62)

    for fascia_label in ORDINE_FASCE:
        d = fasce_data[fascia_label]
        n = d['n']
        if n == 0:
            print(f"\nFascia {fascia_label:>7}:  0 partite")
            continue

        margini = d['margini_fav']
        margine_medio = sum(margini) / n
        margine_std   = (sum((m - margine_medio)**2 for m in margini) / n) ** 0.5
        pct_fav       = 100.0 * d['favorito_vince'] / n

        dist_set = d['n_sets_dist']
        pct_2s = 100.0 * dist_set.get(2, 0) / n
        pct_3s = 100.0 * dist_set.get(3, 0) / n

        # Top-5 punteggi più frequenti
        top5 = sorted(d['punteggi_str'].items(), key=lambda x: -x[1])[:5]

        print(f"\n┌─ Fascia Elo: {fascia_label} punti {'─'*(40 - len(fascia_label))}")
        print(f"│  Partite analizzate  : {n}")
        print(f"│  Margine medio fav.  : {margine_medio:+.1f} games  (σ = {margine_std:.1f})")
        print(f"│  % favorito vince    : {pct_fav:.1f}%")
        print(f"│  In 2 set            : {pct_2s:.1f}%")
        print(f"│  In 3 set            : {pct_3s:.1f}%")
        print(f"│  Punteggi più comuni :")
        for score_k, cnt in top5:
            pct_s = 100.0 * cnt / n
            print(f"│    {score_k:<20} {cnt:>4}x  ({pct_s:.1f}%)")
        print(f"└{'─'*54}")

    # --- Riepilogo calibrazione ---
    print("\n" + "=" * 62)
    print("  CALIBRAZIONE SUGGERITA PER IL MODELLO HANDICAP")
    print("=" * 62)
    print("""
  Diff Elo    │ Handicap consigliato  │ Logica
  ────────────┼───────────────────────┼────────────────────────
  0-50        │ ±1.5 / ±2.5 games     │ match equilibrato
  50-100      │ -2.5 / -3.5 games     │ leggero vantaggio
  100-150     │ -4.5 / -5.5 games     │ vantaggio netto
  150-200     │ -5.5 / -7.5 games     │ forte vantaggio
  200+        │ -8.5+ games           │ dominio atteso
  (segno negativo = handicap sul favorito)
""")


if __name__ == '__main__':
    analizza_margine()
