import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from modules.notifiche_telegram import invia_messaggio, formatta_value_bets_ml, invia_report_giornaliero

# Test messaggio semplice
invia_messaggio("Test diretto dal modulo")

# Test con lista vuota
msg = formatta_value_bets_ml([])
print("Messaggio formattato:")
print(msg)
invia_messaggio(msg)

# Test invia_report_giornaliero con dati fittizi
vb_ml_test = [
    {
        "p1": "Novak Djokovic",
        "p2": "Carlos Alcaraz",
        "torneo": "ATP - Roland Garros",
        "superficie": "clay",
        "quota_p1": 2.35,
        "quota_equa": 2.10,
        "prob_reale": 0.48,
        "ev": 0.128,
    }
]
vb_hdp_test = [
    {
        "p1": "Jannik Sinner",
        "p2": "Alexander Zverev",
        "torneo": "ATP - Rome",
        "superficie": "clay",
        "handicap": -3.5,
        "quota_handicap": 1.90,
        "prob_stimata": 0.57,
        "ev": 0.083,
    }
]

print("\n--- Test invia_report_giornaliero con dati fittizi ---")
invia_report_giornaliero(vb_ml_test, vb_hdp_test)
