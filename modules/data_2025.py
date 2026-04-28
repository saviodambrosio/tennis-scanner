# modules/data_2025.py
# =====================================================
# SCARICA DATI 2025 DA TML-DATABASE (GitHub)
# Gia' in formato Sackmann - nessuna conversione necessaria
# Fonte: github.com/Tennismylife/TML-Database
# =====================================================

import re
import time as _time
import requests
import pandas as pd
import os
import sys
from datetime import date, timedelta
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

def scarica_e_salva_2026(output_dir="data/storico"):
    return scarica_e_salva(2026, output_dir)

_CLAY_KW = [
    'roland garros', 'madrid', 'rome', 'roma', 'monte carlo', 'barcelona',
    'marrakech', 'estoril', 'lyon', 'munich', 'bucharest', 'budapest',
    'hamburg', 'kitzbuh', 'bastad', 'umag', 'gstaad', 'cordoba',
    'buenos aires', 'rio de janeiro', 'sao paulo', 'lima', 'cagliari',
    'santiago', 'casablanca', 'istanbul', 'geneva', 'marbella',
    'aix en provence', 'mauthausen', 'prostejov', 'heilbronn', 'poznan',
    'parma', 'belgrade', 'hamburg', 'bastad', 'gstaad', 'kitzbuhel',
]
_GRASS_KW = [
    'wimbledon', 'halle', 'queen', 'eastbourne', 'nottingham',
    'stuttgart', 'hertogenbosch', 'newport', 'mallorca', 'birmingham',
]

def _superficie_da_torneo(nome):
    n = nome.lower()
    if any(re.search(r'\b' + re.escape(k) + r'\b', n) for k in _CLAY_KW):
        return 'Clay'
    if any(re.search(r'\b' + re.escape(k) + r'\b', n) for k in _GRASS_KW):
        return 'Grass'
    return 'Hard'


def _pulisci_nome_te(nome):
    return re.sub(r'\s*\(\d+\)\s*$', '', nome).strip()


def _parse_giorno_te(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    matches = []

    for table in soup.find_all('table'):
        current_tourney = None
        waiting_winner = None

        for row in table.find_all('tr'):
            cls = row.get('class', [])
            tds = row.find_all('td')
            if not tds:
                continue

            texts = [td.get_text(strip=True) for td in tds]

            if 'head' in cls and 'flags' in cls:
                current_tourney = texts[0] if texts else None
                waiting_winner = None
                continue

            if current_tourney is None:
                continue

            if 'bott' in cls:
                # Winner: [time, name, sets_won, s1, ...] — time sempre presente
                if len(texts) >= 2 and re.match(r'^\d{1,2}:\d{2}', texts[0]):
                    winner_raw = texts[1]
                elif texts:
                    winner_raw = texts[0]
                else:
                    waiting_winner = None
                    continue
                waiting_winner = _pulisci_nome_te(winner_raw)

            elif waiting_winner is not None:
                # Loser: [name, sets_won, s1, ...]
                loser_name = _pulisci_nome_te(texts[0]) if texts else ''
                if loser_name and waiting_winner:
                    matches.append((current_tourney, waiting_winner, loser_name))
                waiting_winner = None

    return matches


def scarica_risultati_recenti_tennisexplorer(giorni=60, output_dir='data/storico'):
    os.makedirs(output_dir, exist_ok=True)
    oggi = date.today()
    start = oggi - timedelta(days=giorni)

    all_rows = []
    current_day = start
    last_log = start

    print(f"Download Tennisexplorer ATP+WTA dal {start} a {oggi - timedelta(days=1)}...")

    while current_day < oggi:
        y, m, d = current_day.year, current_day.month, current_day.day

        for tipo in ['atp-single', 'wta-single']:
            url = (
                f'https://www.tennisexplorer.com/results/'
                f'?type={tipo}&year={y}&month={m}&day={d}'
            )
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code == 200:
                    matches = _parse_giorno_te(r.text)
                    for tourney_name, winner_name, loser_name in matches:
                        all_rows.append({
                            'tourney_date': int(current_day.strftime('%Y%m%d')),
                            'tourney_name': tourney_name,
                            'surface': _superficie_da_torneo(tourney_name),
                            'winner_name': winner_name,
                            'loser_name': loser_name,
                        })
            except Exception as e:
                print(f'  Errore {tipo} {current_day}: {e}')
            _time.sleep(0.5)

        if (current_day - last_log).days >= 7:
            print(f'  ...{current_day} ({len(all_rows)} partite finora)')
            last_log = current_day

        current_day += timedelta(days=1)

    if not all_rows:
        print('Nessuna partita trovata.')
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df = df.drop_duplicates(subset=['tourney_date', 'winner_name', 'loser_name'])
    df = df.sort_values('tourney_date').reset_index(drop=True)

    output_path = os.path.join(output_dir, 'risultati_recenti.csv')
    df.to_csv(output_path, index=False)

    print(f'\nSalvato: {len(df)} partite in {output_path}')
    print(f'Date: {df["tourney_date"].min()} -> {df["tourney_date"].max()}')
    sup = df['surface'].value_counts().to_dict()
    print(f'Superfici: {sup}')
    tornei = df['tourney_name'].nunique()
    print(f'Tornei unici: {tornei}')

    return df


if __name__ == "__main__":
    scarica_e_salva(2025)
