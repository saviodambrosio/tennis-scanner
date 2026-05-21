"""
Modello Markov point-by-point per il tennis.
Implementazione Barnett-Clarke (2005) - "Analyzing Wimbledon".

Flusso:
  SPW_A, RPW_B  →  p_A_serve  →  P(hold game)  →  P(win set)  →  P(win match)

Fonte SPW/RPW: derivata da Elo Tennis Abstract con scaling calibrato.
Fallback pulito se Elo non disponibile.

Adjustments contestuali (Point 14, attivabili da config.py):
  1. Court Pace Index (CPI): delta SPW per velocità campo
  2. Fatica estesa 14 giorni: penalità su prob punto per stanchezza
  3. Timezone change: penalità se cambio >3 fusi negli ultimi 3 giorni
  4. Eta x superficie: over-33 calano di più sull'erba
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# ─── Medie circuito ATP (ricerca pubblica 2020-2025) ───────────────────────────
# Valori medi top-200: quando il server serve, vince questa % di punti.
# Nota: AVG_SPW + AVG_RPW = 1 per costruzione (ogni punto è vinto da uno).
AVG_STATS = {
    'hard':  {'spw': 0.637, 'rpw': 0.363},
    'clay':  {'spw': 0.600, 'rpw': 0.400},
    'grass': {'spw': 0.660, 'rpw': 0.340},
}

# Elo medio Tennis Abstract per top-200 ATP (calibrato su dati 2024-2025)
AVG_ELO_TA = 1700.0

# Scaling Elo → SPW/RPW: per ogni 100 punti Elo sopra la media,
# SPW aumenta di 1.5% (SPW) e 1.2% (RPW).
# Calibrazione: 400 Elo diff → ~6% SPW diff (coerente con ATP top vs media).
ELO_TO_SPW_K = 0.015
ELO_TO_RPW_K = 0.012  # Return leggermente meno correlato (più variabile)

# ─── Parametri adjustment contestuali ──────────────────────────────────────────
AGE_GRASS_THRESHOLD = 33          # anni: oltre questa soglia, penalità su erba
AGE_GRASS_PENALTY_PER_YEAR = 0.003  # -0.3% SPW per anno dopo i 33 su erba
TZ_PENALTY_PER_EXTRA_ZONE = -0.002  # -0.2% SPW per fuso orario extra (>3)
MAX_FATIGUE_PENALTY = -0.030       # max -3% SPW per fatica intensa (≥8 set/14gg)


# ─── Derivazione SPW/RPW da Elo ────────────────────────────────────────────────

def _spw_rpw_da_elo(elo_player: float, surface: str) -> tuple:
    """Stima SPW e RPW del giocatore dall'Elo superficie."""
    stats = AVG_STATS.get(surface, AVG_STATS['hard'])
    delta_100 = (elo_player - AVG_ELO_TA) / 100.0
    spw = stats['spw'] + delta_100 * ELO_TO_SPW_K
    rpw = stats['rpw'] + delta_100 * ELO_TO_RPW_K
    return max(0.35, min(0.85, spw)), max(0.15, min(0.65, rpw))


# ─── Matematica Markov ─────────────────────────────────────────────────────────

def prob_game(p: float) -> float:
    """
    P(server vince il game) dato p = prob vince punto al servizio.

    Somma esatta degli stati: 4-0, 4-1, 4-2, deuce.
    Test noto: prob_game(0.5) == 0.5 (simmetria).
    Test noto: prob_game(1.0) == 1.0, prob_game(0.0) == 0.0.
    """
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    q = 1.0 - p
    # Prob di vincere dal deuce (3-3): formula geometrica
    # P(deuce win) = p^2 / (p^2 + q^2)
    p_deuce_win = p * p / (p * p + q * q)
    p_reach_deuce = 20.0 * p ** 3 * q ** 3
    return (p ** 4
            + 4.0 * p ** 4 * q
            + 10.0 * p ** 4 * q ** 2
            + p_reach_deuce * p_deuce_win)


def prob_tiebreak(p_tb: float) -> float:
    """
    P(A vince il tiebreak) con probabilità media punto p_tb.

    Catena di Markov su stati (i, j) ∈ [0..13]×[0..13].
    Al deuce nel tiebreak (entrambi ≥6, stessa parità): formula geometrica.
    """
    memo: dict = {}

    def _f(i: int, j: int) -> float:
        # Terminali
        if i >= 7 and i >= j + 2:
            return 1.0
        if j >= 7 and j >= i + 2:
            return 0.0
        if (i, j) in memo:
            return memo[(i, j)]
        # Deuce nel tiebreak: stesso calcolo del deuce nel game
        if i >= 6 and j >= 6:
            r = p_tb * p_tb / (p_tb * p_tb + (1.0 - p_tb) ** 2)
            memo[(i, j)] = r
            return r
        r = p_tb * _f(i + 1, j) + (1.0 - p_tb) * _f(i, j + 1)
        memo[(i, j)] = r
        return r

    return _f(0, 0)


def prob_set(pa: float, pb_break: float) -> float:
    """
    P(A vince il set).

    Args:
        pa: P(A vince game quando A serve) = P(hold_A) = prob_game(p_A_serve)
        pb_break: P(A vince game quando B serve) = 1 - prob_game(p_B_serve)

    Catena di Markov sugli stati (a, b) = games vinti da A e B.
    Chi serve è determinato dalla parità di (a+b): 0 → A, 1 → B.
    Ritorna la media sui due casi (A serve primo / B serve primo).

    Terminali:
        a >= 6 e b <= a-2  → A vince
        b >= 6 e a <= b-2  → B vince
        a == b == 6         → tiebreak
    """
    # Prob media punto nel tiebreak (alternanza servizio ogni 2 punti)
    p_tb = (pa + pb_break) / 2.0
    tb = prob_tiebreak(p_tb)

    memo: dict = {}

    def _f(a: int, b: int, serve: int) -> float:
        # Terminali
        if a >= 6 and b <= a - 2:
            return 1.0
        if b >= 6 and a <= b - 2:
            return 0.0
        if a == 6 and b == 6:
            return tb
        if (a, b, serve) in memo:
            return memo[(a, b, serve)]
        if serve == 0:     # A serve
            pw = pa
            r = pw * _f(a + 1, b, 1) + (1.0 - pw) * _f(a, b + 1, 1)
        else:              # B serve
            pw = pb_break  # P(A fa break)
            r = pw * _f(a + 1, b, 0) + (1.0 - pw) * _f(a, b + 1, 0)
        memo[(a, b, serve)] = r
        return r

    return (_f(0, 0, 0) + _f(0, 0, 1)) / 2.0


def prob_match(ps: float, best_of: int = 3) -> float:
    """
    P(A vince il match) dato ps = P(A vince un set).

    best_of=3:  P = ps^2 * (3 - 2*ps)
    best_of=5:  P = ps^3 * (10 - 15*ps + 6*ps^2)
    """
    if best_of == 3:
        return ps ** 2 * (3.0 - 2.0 * ps)
    elif best_of == 5:
        return ps ** 3 * (10.0 - 15.0 * ps + 6.0 * ps ** 2)
    raise ValueError(f"best_of deve essere 3 o 5, non {best_of}")


# ─── Fatica estesa 14 giorni ────────────────────────────────────────────────────

def calcola_fatica_markov(nome: str, partite_recenti_dict: dict, giorni: int = 14) -> float:
    """
    Penalità SPW per fatica estesa (14 giorni di set giocati).

    Stima i set giocati nei ultimi `giorni` giorni e ritorna un delta SPW:
        0-3 set   → 0.0
        4-5 set   → -0.005
        6-7 set   → -0.015
        8+  set   → -0.030

    I set per match vengono stimati: best-of-3 = 2.3 set medi.
    """
    if not nome or not partite_recenti_dict:
        return 0.0
    try:
        import pandas as pd
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=giorni)
    except ImportError:
        return 0.0

    partite = [p for p in partite_recenti_dict.get(nome, []) if p['data'] >= cutoff]
    # Stima set: 2.3 set medi per match best-of-3
    set_stimati = len(partite) * 2.3

    if set_stimati < 4:
        return 0.0
    elif set_stimati < 6:
        return -0.005
    elif set_stimati < 8:
        return -0.015
    else:
        return MAX_FATIGUE_PENALTY


# ─── Funzione principale ────────────────────────────────────────────────────────

def calcola_probabilita_markov(
    elo_A: float,
    elo_B: float,
    surface: str,
    best_of: int = 3,
    adjustments: dict = None
) -> float:
    """
    Calcola P(A vince il match) con il modello Markov point-by-point.

    Args:
        elo_A: Elo superficie di A (da Tennis Abstract)
        elo_B: Elo superficie di B
        surface: 'hard', 'clay', 'grass'
        best_of: 3 (default) o 5 (Grand Slam)
        adjustments: dict con chiavi opzionali:
            cpi (float):     Court Pace Index, delta SPW per entrambi
            fatica_A (float ≤0): penalità fatica SPW di A (da calcola_fatica_markov)
            fatica_B (float ≤0): penalità fatica SPW di B
            tz_A (int):      fusi orari cambiati negli ultimi 3gg da A
            tz_B (int):      fusi orari cambiati negli ultimi 3gg da B
            eta_A (int):     età di A in anni (per adj erba)
            eta_B (int):     età di B in anni

    Returns:
        float: P(A vince il match) ∈ [0, 1]
    """
    if adjustments is None:
        adjustments = {}

    stats = AVG_STATS.get(surface, AVG_STATS['hard'])
    avg_spw = stats['spw']
    avg_rpw = stats['rpw']

    # ── SPW/RPW individuali stimati da Elo ──────────────────────────────────
    spw_A, rpw_A = _spw_rpw_da_elo(elo_A, surface)
    spw_B, rpw_B = _spw_rpw_da_elo(elo_B, surface)

    # ── Barnett-Clarke: prob punto al servizio ──────────────────────────────
    # p_A_serve = AVG_SPW + (SPW_A - AVG_SPW) - (RPW_B - AVG_RPW)
    p_A_serve = avg_spw + (spw_A - avg_spw) - (rpw_B - avg_rpw)
    p_B_serve = avg_spw + (spw_B - avg_spw) - (rpw_A - avg_rpw)

    # ── Adjustment 1: Court Pace Index ──────────────────────────────────────
    # CPI > 0: campo veloce → bonus servitori; CPI = 0: neutro
    cpi = float(adjustments.get('cpi', 0.0))
    p_A_serve += cpi
    p_B_serve += cpi

    # ── Adjustment 2: Fatica estesa 14 giorni ───────────────────────────────
    # fatica ∈ [-0.03, 0] come delta SPW
    p_A_serve += float(adjustments.get('fatica_A', 0.0))
    p_B_serve += float(adjustments.get('fatica_B', 0.0))

    # ── Adjustment 3: Timezone change ───────────────────────────────────────
    # Penalità se cambio > 3 fusi negli ultimi 3 giorni
    tz_A = int(adjustments.get('tz_A', 0))
    tz_B = int(adjustments.get('tz_B', 0))
    if tz_A > 3:
        p_A_serve += (tz_A - 3) * TZ_PENALTY_PER_EXTRA_ZONE
    if tz_B > 3:
        p_B_serve += (tz_B - 3) * TZ_PENALTY_PER_EXTRA_ZONE

    # ── Adjustment 4: Età × superficie (erba) ───────────────────────────────
    # Over-33 calano più sull'erba per ridotta mobilità / rimbalzo basso
    if surface == 'grass':
        for eta, side in [(adjustments.get('eta_A', 0), 'A'),
                          (adjustments.get('eta_B', 0), 'B')]:
            if eta and eta >= AGE_GRASS_THRESHOLD:
                pen = (eta - AGE_GRASS_THRESHOLD) * AGE_GRASS_PENALTY_PER_YEAR
                if side == 'A':
                    p_A_serve -= pen
                else:
                    p_B_serve -= pen

    # ── Clamp valori validi [0.30, 0.95] ────────────────────────────────────
    p_A_serve = max(0.30, min(0.95, p_A_serve))
    p_B_serve = max(0.30, min(0.95, p_B_serve))

    # ── Catena di Markov ────────────────────────────────────────────────────
    pa = prob_game(p_A_serve)              # P(A tiene servizio)
    pb_break = 1.0 - prob_game(p_B_serve)  # P(A fa break)

    ps = prob_set(pa, pb_break)
    pm = prob_match(ps, best_of=best_of)

    return round(pm, 6)
