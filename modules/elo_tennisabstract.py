# modules/elo_tennisabstract.py
# =====================================================
# IMPORTA ELO AGGIORNATO DA TENNIS ABSTRACT
# Fonte: tennisabstract.com - aggiornato settimanalmente
# =====================================================

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import sys
import unicodedata
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

URLS = {
    'atp': 'https://www.tennisabstract.com/reports/atp_elo_ratings.html',
    'wta': 'https://www.tennisabstract.com/reports/wta_elo_ratings.html',
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

CACHE_DIR = "data/elo_cache"
CACHE_FILE = os.path.join(CACHE_DIR, "tennis_abstract_elo.csv")
CACHE_META = os.path.join(CACHE_DIR, "last_update.txt")

def scarica_elo_tennisabstract(tour='atp'):
    """Scarica e parsea la tabella Elo da Tennis Abstract."""
    url = URLS.get(tour)
    if not url:
        return {}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ❌ Errore download Tennis Abstract ({tour}): {e}")
        return {}

    soup = BeautifulSoup(resp.text, 'html.parser')
    tables = soup.find_all('table')

    # Tabella dati è la seconda (indice 1)
    target_table = None
    for t in tables:
        rows = t.find_all('tr')
        if len(rows) > 100:
            target_table = t
            break

    if not target_table:
        print(f"  ❌ Tabella non trovata per {tour}")
        return {}

    ratings = {}
    rows = target_table.find_all('tr')

    for row in rows[1:]:  # skip header
        cells = [td.text.strip().replace('\xa0', ' ') for td in row.find_all(['td', 'th'])]
        if len(cells) < 10:
            continue

        try:
            # Struttura: rank, player, age, elo, '', hrank, helo, crank, celo, grank, gelo
            nome = cells[1].strip()
            age_raw = cells[2] if len(cells) > 2 else ''
            elo_gen = float(cells[3]) if cells[3] else None
            helo = float(cells[6]) if cells[6] else None
            celo = float(cells[8]) if cells[8] else None
            gelo = float(cells[10]) if cells[10] else None

            try:
                age = int(float(age_raw)) if age_raw else 0
            except (ValueError, TypeError):
                age = 0

            if nome and elo_gen:
                ratings[nome] = {
                    'elo': elo_gen,
                    'hard': helo or elo_gen,
                    'clay': celo or elo_gen,
                    'grass': gelo or elo_gen,
                    'age': age,
                    'tour': tour
                }
        except (ValueError, IndexError):
            continue

    return ratings

def carica_elo_aggiornato(forza_refresh=False):
    """
    Carica l'Elo aggiornato da Tennis Abstract.
    Usa cache locale se aggiornata nelle ultime 24 ore.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    # Controlla se cache è fresca (meno di 24 ore)
    if not forza_refresh and os.path.exists(CACHE_FILE) and os.path.exists(CACHE_META):
        with open(CACHE_META, 'r') as f:
            ultima = f.read().strip()
        try:
            dt_ultima = datetime.fromisoformat(ultima)
            ore_passate = (datetime.now() - dt_ultima).total_seconds() / 3600
            if ore_passate < 24:
                print(f"  📦 Cache Elo valida ({ore_passate:.1f}h fa) — uso quella")
                return _carica_da_cache()
        except:
            pass

    # Scarica fresh
    print("  🌐 Download Elo da Tennis Abstract...")
    ratings = {}

    for tour in ['atp', 'wta']:
        dati = scarica_elo_tennisabstract(tour)
        ratings.update(dati)
        print(f"  ✅ {tour.upper()}: {len(dati)} giocatori")

    if not ratings:
        print("  ⚠️  Download fallito — provo cache")
        return _carica_da_cache()

    # Salva cache
    righe = []
    for nome, d in ratings.items():
        righe.append({
            'nome': nome,
            'elo': d['elo'],
            'hard': d['hard'],
            'clay': d['clay'],
            'grass': d['grass'],
            'age': d.get('age', 0),
            'tour': d['tour']
        })
    df = pd.DataFrame(righe)
    df.to_csv(CACHE_FILE, index=False)

    with open(CACHE_META, 'w') as f:
        f.write(datetime.now().isoformat())

    print(f"  💾 Cache salvata: {len(ratings)} giocatori totali")
    return ratings

def _carica_da_cache():
    """Carica ratings dalla cache locale."""
    if not os.path.exists(CACHE_FILE):
        return {}
    df = pd.read_csv(CACHE_FILE)
    ratings = {}
    for _, row in df.iterrows():
        ratings[row['nome']] = {
            'elo': row['elo'],
            'hard': row['hard'],
            'clay': row['clay'],
            'grass': row['grass'],
            'age': int(row['age']) if 'age' in row and not pd.isna(row['age']) else 0,
            'tour': row['tour']
        }
    return ratings

_PARTICELLE = frozenset({
    'de', 'van', 'del', 'di', 'dos', 'da', 'den', 'der', 'von', 'le', 'la', 'du', 'el'
})

def _norm(s):
    """Rimuove accenti unicode e converte in minuscolo."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

def _parse_nome(nome):
    """Restituisce (primo_nome, cognome) gestendo particelle nobiliarie.

    Se il primo token è una particella (de, van, …) l'intero nome è cognome.
    Altrimenti: primo token = nome, resto = cognome.
    """
    parti = nome.strip().split()
    if not parti:
        return '', ''
    if len(parti) == 1:
        return '', parti[0]
    fn = parti[0]
    if _norm(fn).rstrip('.') in _PARTICELLE:
        return '', nome
    return fn, ' '.join(parti[1:])

def _is_te_format(nome):
    """Rileva formato TennisExplorer: 'Cognome I.' (ultimo token = singola iniziale)."""
    parti = nome.strip().split()
    return len(parti) >= 2 and len(parti[-1].rstrip('.')) == 1

def _parse_te(nome):
    """Parsa 'Cognome I.' → (cognome_norm, iniziale_norm)."""
    parti = nome.strip().split()
    return _norm(' '.join(parti[:-1])), _norm(parti[-1].rstrip('.'))

def trova_giocatore_ta(nome, ratings_ta):
    """
    Cerca un giocatore nei rating Tennis Abstract con matching robusto:
    - normalizzazione accenti (é→e, ü→u, ñ→n)
    - gestione particelle (de, van, del, di, dos, da, …)
    - matching iniziale+cognome ("A. De Minaur" → "Alex De Minaur")
    - cognome singolo solo se non ambiguo
    """
    if not nome:
        return None, None

    # 1. Exact match
    if nome in ratings_ta:
        return nome, ratings_ta[nome]

    # 2. Case-insensitive
    for k in ratings_ta:
        if k.lower() == nome.lower():
            return k, ratings_ta[k]

    # 3. Normalizzazione accenti
    nome_norm = _norm(nome)
    for k in ratings_ta:
        if _norm(k) == nome_norm:
            return k, ratings_ta[k]

    # 4. Matching nome+cognome con particelle e formato iniziale
    fn_in, ln_in = _parse_nome(nome)
    fn_in_norm = _norm(fn_in)
    ln_in_norm = _norm(ln_in)
    is_initial = bool(fn_in_norm) and len(fn_in_norm.rstrip('.')) == 1

    if ln_in_norm:
        candidati = []
        for k, v in ratings_ta.items():
            fn_k, ln_k = _parse_nome(k)
            if _norm(ln_k) != ln_in_norm:
                continue
            if fn_in_norm:
                if is_initial:
                    ini = fn_in_norm.rstrip('.')
                    if _norm(fn_k) and _norm(fn_k)[0] == ini:
                        candidati.append((k, v))
                else:
                    if _norm(fn_k) == fn_in_norm:
                        candidati.append((k, v))
            else:
                candidati.append((k, v))
        if len(candidati) == 1:
            return candidati[0]

    # 5. Solo ultima parola (cognome singolo), solo se non ambiguo
    ultimo_norm = _norm(nome.split()[-1])
    candidati_cog = [(k, v) for k, v in ratings_ta.items()
                     if _norm(k.split()[-1]) == ultimo_norm]
    if len(candidati_cog) == 1:
        return candidati_cog[0]

    # 6. Formato TennisExplorer inverso: "Jannik Sinner" → cerca "Sinner J."
    #    Applicato quando le chiavi del dict sono in formato "Cognome I."
    if fn_in_norm and ln_in_norm:
        ini_ricerca = fn_in_norm[0]
        candidati_te = [
            (k, v) for k, v in ratings_ta.items()
            if _is_te_format(k) and _parse_te(k) == (ln_in_norm, ini_ricerca)
        ]
        if len(candidati_te) == 1:
            return candidati_te[0]

    return None, None

def verifica_disponibilita():
    """
    Verifica che Tennis Abstract sia raggiungibile.
    Usato come safety check prima di ogni sessione.
    """
    try:
        resp = requests.get(URLS['atp'], headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return True, "Tennis Abstract raggiungibile"
        else:
            return False, f"Tennis Abstract risponde {resp.status_code}"
    except Exception as e:
        return False, f"Tennis Abstract non raggiungibile: {e}"

if __name__ == "__main__":
    print("🎾 Test Tennis Abstract Elo Scraper\n")

    ok, msg = verifica_disponibilita()
    print(f"Connessione: {'✅' if ok else '❌'} {msg}\n")

    if ok:
        ratings = carica_elo_aggiornato(forza_refresh=True)
        print(f"\nTotale giocatori: {len(ratings)}")

        # Test alcuni giocatori noti
        test = ['Jannik Sinner', 'Carlos Alcaraz', 'Aryna Sabalenka', 'Iga Swiatek']
        print("\nTest rating:")
        for nome in test:
            n, r = trova_giocatore_ta(nome, ratings)
            if r:
                print(f"  {nome}: Elo={r['elo']} | Clay={r['clay']} | Hard={r['hard']} | Grass={r['grass']}")
            else:
                print(f"  {nome}: NON TROVATO")