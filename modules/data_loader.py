# modules/data_loader.py
# =====================================================
# Scarica e prepara i dati storici ATP/WTA (GRATUITI)
# Fonte: github.com/JeffSackmann - il dataset standard
# del settore usato da tutti i professionisti del quant betting
# =====================================================

import requests
import pandas as pd
import os
from config import ATP_DATA_URL, WTA_DATA_URL, ANNI_STORICI

DATA_DIR = "data/storico"

def scarica_dati_storici(forza_riscaricare=False):
    """
    Scarica i CSV storici da GitHub (Jeff Sackmann).
    Vengono salvati in data/storico/ e riusati nelle sessioni successive.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    file_scaricati = []

    for anno in ANNI_STORICI:
        for tour, url_template in [("atp", ATP_DATA_URL), ("wta", WTA_DATA_URL)]:
            nome_file = f"{DATA_DIR}/{tour}_{anno}.csv"
            
            if os.path.exists(nome_file) and not forza_riscaricare:
                print(f"  ✅ {tour.upper()} {anno} già presente, skip.")
                file_scaricati.append(nome_file)
                continue

            url = url_template.format(year=anno)
            print(f"  📥 Scaricando {tour.upper()} {anno}...")
            try:
                r = requests.get(url, timeout=15)
                if r.status_code == 200:
                    with open(nome_file, 'wb') as f:
                        f.write(r.content)
                    print(f"  ✅ Salvato: {nome_file}")
                    file_scaricati.append(nome_file)
                else:
                    print(f"  ⚠️  {anno} {tour}: HTTP {r.status_code}")
            except Exception as e:
                print(f"  ❌ Errore {anno} {tour}: {e}")

    return file_scaricati

def carica_tutti_i_match():
    """
    Carica tutti i CSV storici in un unico DataFrame pandas.
    Colonne principali che useremo:
      - tourney_date, surface, winner_name, loser_name
      - winner_rank, loser_rank
      - w_svpt, w_1stIn, w_1stWon, w_2ndWon (servizio vincitore)
      - l_svpt, l_1stIn, l_1stWon, l_2ndWon (servizio perdente)
    """
    dfs = []
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv"):
            try:
                df = pd.read_csv(os.path.join(DATA_DIR, f), low_memory=False)
                # Aggiungiamo la colonna tour (atp/wta) dal nome file
                df['tour'] = f.split('_')[0]
                dfs.append(df)
            except Exception as e:
                print(f"  ⚠️  Errore lettura {f}: {e}")

    if not dfs:
        print("❌ Nessun dato storico trovato. Esegui prima scarica_dati_storici().")
        return pd.DataFrame()

    df_totale = pd.concat(dfs, ignore_index=True)
    
    # Pulizia base
    df_totale['tourney_date'] = pd.to_datetime(
        df_totale['tourney_date'].astype(str), format='%Y%m%d', errors='coerce'
    )
    df_totale = df_totale.dropna(subset=['winner_name', 'loser_name'])
    
    print(f"✅ Caricati {len(df_totale):,} match storici ({df_totale['tourney_date'].min().year}-{df_totale['tourney_date'].max().year})")
    return df_totale


if __name__ == "__main__":
    print("🚀 Download dati storici tennis...")
    scarica_dati_storici()
    df = carica_tutti_i_match()
    print(df.head())
    print(f"\nColonne disponibili: {list(df.columns)}")
