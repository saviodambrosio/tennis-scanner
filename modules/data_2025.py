# modules/data_2025.py
# =====================================================
# SCARICA DATI 2025 DA TML-DATABASE (GitHub)
# Gia' in formato Sackmann - nessuna conversione necessaria
# Fonte: github.com/Tennismylife/TML-Database
# =====================================================

import requests
import pandas as pd
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

GITHUB_URL = "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/{anno}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def scarica_e_salva(anno=2025, output_dir="data/storico"):
    os.makedirs(output_dir, exist_ok=True)

    url = GITHUB_URL.format(anno=anno)
    print(f"Download {anno} da TML-Database GitHub...")

    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()

    from io import StringIO
    df = pd.read_csv(StringIO(r.text))
    print(f"{len(df)} partite scaricate")

    output_path = os.path.join(output_dir, f"atp_{anno}_tml.csv")
    df.to_csv(output_path, index=False)
    print(f"Salvato in {output_path}")

    print(f"\nStatistiche:")
    print(f"  Partite: {len(df)}")
    print(f"  Date: {df['tourney_date'].min()} -> {df['tourney_date'].max()}")
    print(f"  Superfici: {df['surface'].value_counts().to_dict()}")
    print(f"  Livelli: {df['tourney_level'].value_counts().to_dict()}")
    tornei_g = df[df['tourney_level']=='G']['tourney_name'].unique().tolist()
    tornei_m = df[df['tourney_level']=='M']['tourney_name'].unique().tolist()
    print(f"  Grand Slam: {tornei_g}")
    print(f"  Masters: {tornei_m}")

    return df

if __name__ == "__main__":
    scarica_e_salva(2025)
