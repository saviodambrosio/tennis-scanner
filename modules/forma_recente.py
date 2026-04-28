import os
import pandas as pd
from datetime import datetime, timedelta

SUPERFICIE_MAP = {
    'clay': 'clay', 'red clay': 'clay', 'clay (red)': 'clay',
    'hard': 'hard', 'hardcourt outdoor': 'hard', 'hardcourt indoor': 'hard',
    'hard (indoor)': 'hard', 'grass': 'grass', 'carpet': 'hard',
}

def _normalizza_superficie(s):
    if not s or str(s).lower() in ['nan', '']:
        return 'hard'
    return SUPERFICIE_MAP.get(str(s).strip().lower(), 'hard')

def _rank_to_elo_approx(rank):
    # rank 1 ≈ 2100, rank 100 ≈ 1600, rank 500 ≈ 1200
    try:
        r = float(rank)
        if r > 0:
            return max(1200, int(2100 - r * 5))
    except (TypeError, ValueError):
        pass
    return 0


def _carica_df_sackmann(files, cutoff):
    dfs = []
    for f in files:
        if os.path.exists(f):
            try:
                dfs.append(pd.read_csv(f, low_memory=False))
            except Exception:
                pass
    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    df['tourney_date'] = pd.to_datetime(
        df['tourney_date'].astype(str), format='%Y%m%d', errors='coerce'
    )
    return df[df['tourney_date'] >= cutoff].copy()


def _carica_df_te(path, cutoff):
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()
    df['tourney_date'] = pd.to_datetime(
        df['tourney_date'].astype(str), format='%Y%m%d', errors='coerce'
    )
    df = df[df['tourney_date'] >= cutoff].copy()
    for col in ('winner_rank', 'loser_rank'):
        if col not in df.columns:
            df[col] = 0
    return df


def carica_partite_recenti(giorni=30):
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=giorni)

    df_sack = _carica_df_sackmann(
        ['data/storico/atp_2025_tml.csv', 'data/storico/atp_2026_tml.csv'],
        cutoff,
    )
    df_te = _carica_df_te('data/storico/risultati_recenti.csv', cutoff)

    all_dfs = [d for d in (df_sack, df_te) if not d.empty]
    if not all_dfs:
        return {}

    df = pd.concat(all_dfs, ignore_index=True)

    risultati = {}

    for _, row in df.iterrows():
        winner = row['winner_name']
        loser = row['loser_name']
        data = row['tourney_date']
        sup = _normalizza_superficie(row.get('surface', ''))
        elo_loser = _rank_to_elo_approx(row.get('loser_rank', 0))
        elo_winner = _rank_to_elo_approx(row.get('winner_rank', 0))

        if winner not in risultati:
            risultati[winner] = []
        risultati[winner].append({
            'data': data,
            'vinto': True,
            'superficie': sup,
            'avversario_elo': elo_loser,
        })

        if loser not in risultati:
            risultati[loser] = []
        risultati[loser].append({
            'data': data,
            'vinto': False,
            'superficie': sup,
            'avversario_elo': elo_winner,
        })

    return risultati


def calcola_forma(nome, partite_recenti, superficie=None, n_partite=10):
    partite = partite_recenti.get(nome, [])

    if superficie:
        partite = [p for p in partite if p['superficie'] == superficie]

    partite = sorted(partite, key=lambda x: x['data'], reverse=True)[:n_partite]

    if not partite:
        return 0.0

    oggi = pd.Timestamp.now()
    pesi_totali = 0.0
    score = 0.0

    for i, p in enumerate(partite):
        # Peso posizionale: la partita più recente pesa di più
        peso_posizione = 1.0 / (i + 1)

        # Peso temporale: partite degli ultimi 30gg pesano quasi 1, oltre decadono
        giorni_fa = max(0, (oggi - p['data']).days)
        peso_tempo = max(0.1, 1.0 - giorni_fa / 60.0)

        peso = peso_posizione * peso_tempo
        pesi_totali += peso

        if p['vinto']:
            score += peso

    if pesi_totali == 0:
        return 0.0

    win_rate = score / pesi_totali  # [0, 1]
    return round((win_rate * 2) - 1, 3)  # mappa in [-1, +1]


def aggiusta_elo_per_forma(elo_base, forma_score):
    return round(elo_base + (forma_score * 150), 1)
