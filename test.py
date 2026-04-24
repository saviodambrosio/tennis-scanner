import sys, os
sys.path.insert(0, '.')
import pandas as pd
from modules.elo import costruisci_elo_da_csv, normalizza_superficie
from modules.signals import genera_segnale

def inverti_nome(nome):
    parti = nome.strip().split()
    if len(parti) == 2:
        return f"{parti[1]} {parti[0]}"
    elif len(parti) == 3:
        return f"{parti[1]} {parti[2]} {parti[0]}"
    return nome

def trova_giocatore(nome, ratings):
    if nome in ratings:
        return nome, ratings[nome]
    invertito = inverti_nome(nome)
    if invertito in ratings:
        return invertito, ratings[invertito]
    return None, None

print("⚙️  Costruzione database Elo...")
ratings_totale = {}
ratings_sup_totale = {}

file_da_caricare = [
    'data/storico/atp_2024.csv',
    'data/storico/challenger_atp2024.csv',
    'data/storico/ITFATP2024.csv',
    'data/storico/giapponesi2023.csv',
    'data/storico/wta_2024.csv',
]

for filepath in file_da_caricare:
    if os.path.exists(filepath):
        try:
            ratings, ratings_sup, _ = costruisci_elo_da_csv(filepath)
            ratings_totale.update(ratings)
            for nome, sup_dict in ratings_sup.items():
                if nome not in ratings_sup_totale:
                    ratings_sup_totale[nome] = sup_dict
                else:
                    # Media pesata se giocatore appare in più file
                    for s in ['clay', 'hard', 'grass']:
                        ratings_sup_totale[nome][s] = round(
                            (ratings_sup_totale[nome][s] + sup_dict[s]) / 2, 1
                        )
            print(f"  ✅ {os.path.basename(filepath)}: {len(ratings)} giocatori")
        except Exception as e:
            print(f"  ❌ {os.path.basename(filepath)}: errore - {e}")
    else:
        print(f"  ⚠️  {filepath} non trovato")

print(f"\n✅ Database totale: {len(ratings_totale)} giocatori\n")

# --- BACKTEST ---
df = pd.read_csv('data/pro_bets.csv')
singolari = df[(df['type'] == 'Singles') & (df['bet_type'] == 'ML')].copy()
print(f"📊 Giocate da testare: {len(singolari)}\n")

risultati = []
non_trovati = []

for _, row in singolari.iterrows():
    p1_raw = str(row['player1']).strip()
    p2_raw = str(row['player2']).strip()
    quota = float(row['odds_decimal'])

    nome_p1, elo_p1 = trova_giocatore(p1_raw, ratings_totale)
    nome_p2, elo_p2 = trova_giocatore(p2_raw, ratings_totale)

    if not elo_p1 or not elo_p2:
        mancante = p1_raw if not elo_p1 else p2_raw
        non_trovati.append(f"{p1_raw} vs {p2_raw} (manca: {mancante})")
        continue

    segnale = genera_segnale(nome_p1, elo_p1, nome_p2, elo_p2, quota)
    risultati.append(segnale)

value_bets = [r for r in risultati if r['ev'] >= 0.05]
no_value = [r for r in risultati if r['ev'] < 0.05]

print(f"{'='*55}")
print(f"  RISULTATI BACKTEST vs GIOCATE PRO")
print(f"{'='*55}")
print(f"  Giocate analizzate   : {len(risultati)}")
print(f"  Non trovati in Elo   : {len(non_trovati)}")
print(f"  VALUE BET ✅         : {len(value_bets)}")
print(f"  NO VALUE ⏩          : {len(no_value)}")
if risultati:
    pct = len(value_bets) / len(risultati) * 100
    print(f"  Coincidenza con Pro  : {pct:.1f}%")
print(f"{'='*55}")

print(f"\n✅ VALUE BET trovate dal modello:")
for r in sorted(value_bets, key=lambda x: x['ev'], reverse=True):
    print(f"  {r['p1']:<28} vs {r['p2']:<28} | quota {r['quota_mercato']} | EV {r['ev']*100:.1f}%")

if non_trovati:
    print(f"\n⚠️  Non trovati ({len(non_trovati)}):")
    for n in non_trovati:
        print(f"  - {n}")