# modules/signals.py
# =====================================================
# MOTORE SEGNALI - Calcola EV e genera verdetto
# =====================================================

def prob_da_elo(elo_p1, elo_p2):
    """
    Converte i rating Elo in probabilità di vittoria.
    Formula standard usata in tutti i sistemi professionali.
    """
    return 1 / (1 + 10 ** ((elo_p2 - elo_p1) / 400))

def rimuovi_margine_bookmaker(quota_decimale):
    """
    La quota del bookmaker include un margine (vig) tipicamente del 5-8%.
    Questa funzione restituisce la probabilità implicita LORDA
    (senza rimozione del margine - lo confrontiamo con la nostra prob reale).
    """
    return 1 / quota_decimale

def calcola_ev(prob_reale, quota_decimale):
    """
    Formula centrale del progetto:
    EV = (probabilità reale × quota) - 1
    EV > 0.05 = valore trovato (5% di vantaggio sul bookmaker)
    """
    return (prob_reale * quota_decimale) - 1

def genera_segnale(nome_p1, elo_p1, nome_p2, elo_p2, quota_p1, quota_p2, soglia_ev=0.05):
    """
    Funzione principale: dati due giocatori con i loro Elo
    e le quote offerte dal bookmaker, restituisce il verdetto completo.
    """
    prob_reale = prob_da_elo(elo_p1, elo_p2)
    prob_implicita_bk = rimuovi_margine_bookmaker(quota_p1)

    # Quota equa Elo: la quota che azzera l'EV secondo la nostra stima
    quota_equa = round(1 / prob_reale, 2) if prob_reale > 0 else 99

    ev = calcola_ev(prob_reale, quota_p1)

    verdetto = "VALUE_BET ✅" if ev >= soglia_ev else "NO VALUE ⏩"

    return {
        "p1": nome_p1,
        "p2": nome_p2,
        "elo_p1": elo_p1,
        "elo_p2": elo_p2,
        "prob_reale": round(prob_reale, 3),
        "prob_bookmaker": round(prob_implicita_bk, 3),
        "quota_mercato": quota_p1,
        "quota_equa": quota_equa,
        "ev": round(ev, 4),
        "verdetto": verdetto,
    }

def stampa_segnale(segnale):
    """Stampa il segnale in modo leggibile."""
    print(f"\n{'='*50}")
    print(f"🎾 {segnale['p1']} vs {segnale['p2']}")
    print(f"{'='*50}")
    print(f"  Elo {segnale['p1']:<20}: {segnale['elo_p1']}")
    print(f"  Elo {segnale['p2']:<20}: {segnale['elo_p2']}")
    print(f"  Probabilità reale     : {segnale['prob_reale']*100:.1f}%")
    print(f"  Probabilità bookmaker : {segnale['prob_bookmaker']*100:.1f}%")
    print(f"  Quota mercato         : {segnale['quota_mercato']}")
    print(f"  Quota equa            : {segnale['quota_equa']}")
    print(f"  Expected Value        : {segnale['ev']*100:.2f}%")
    print(f"  Verdetto              : {segnale['verdetto']}")
    print(f"{'='*50}")