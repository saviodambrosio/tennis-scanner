import requests
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime
from modules.elo_tennisabstract import (
    carica_elo_aggiornato, trova_giocatore_ta, verifica_disponibilita
)
from modules.odds_apiio import get_partite_con_quote_oggi, get_quote_evento as get_quote_apiio
from modules.signals import genera_segnale
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SOFASCORE_URL = "https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{data}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    from config import ODDS_API_IO_KEY
except:
    ODDS_API_IO_KEY = ""

SUPERFICIE_MAP = {
    'clay': 'clay', 'red clay': 'clay', 'clay (red)': 'clay',
    'hard': 'hard', 'hardcourt outdoor': 'hard', 'hardcourt indoor': 'hard',
    'hard (indoor)': 'hard', 'grass': 'grass', 'carpet': 'hard',
}

def normalizza_superficie(s):
    if not s or str(s).lower() in ['nan','gwangju','']:
        return 'hard'
    return SUPERFICIE_MAP.get(str(s).strip().lower(), 'hard')

def superficie_da_torneo(torneo):
    t = torneo.lower()

    # GRASS — controllo che 'halle' non sia dentro 'challenger'
    if 'halle' in t and 'challenger' not in t:
        return 'grass'
    if 'queens club' in t:
        return 'grass'
    if any(x in t for x in [
        'wimbledon', 'hertogenbosch', 'eastbourne',
        'nottingham', 'newport', 'rosmalen'
    ]):
        return 'grass'

    # CLAY
    if any(x in t for x in [
        'madrid', 'rome', 'roma', 'roland', 'clay',
        'barcelona', 'monte carlo', 'hamburg', 'geneva',
        'lyon', 'munich', 'estoril', 'bucharest', 'istanbul',
        'marrakech', 'houston', 'rio', 'buenos aires', 'bogota',
        'santiago', 'lima', 'cordoba', 'bastad', 'umag', 'gstaad',
        'kitzbuhel', 'casablanca', 'cagliari', 'aix',
        'mauthausen', 'ostrava', 'abidjan', 'shymkent'
    ]):
        return 'clay'

    # HARD default
    return 'hard'

def get_quote_sofascore(event_id):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/odds/1/featured"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        data = resp.json()
        featured = data.get("featured", {}).get("default", {})
        choices = featured.get("choices", [])
        if len(choices) >= 2:
            def fraz_a_dec(fraz):
                try:
                    n, d = fraz.split("/")
                    return round(1 + int(n) / int(d), 3)
                except:
                    return None
            q1 = fraz_a_dec(choices[0].get("fractionalValue", ""))
            q2 = fraz_a_dec(choices[1].get("fractionalValue", ""))
            return q1, q2
    except:
        pass
    return None, None

def get_partite_sofascore(data=None):
    if data is None:
        data = datetime.now().strftime("%Y-%m-%d")
    try:
        resp = requests.get(
            SOFASCORE_URL.format(data=data),
            headers=HEADERS, timeout=10
        )
        eventi = resp.json().get("events", [])
    except:
        return []

    partite = []
    for e in eventi:
        filtri = e.get("eventFilters", {})
        if "singles" not in filtri.get("category", []):
            continue
        if "pro" not in filtri.get("level", []):
            continue
        tornei_validi = ['p1000', 'p500', 'p250', 'grand_slam', 'atp', 'wta', 'challenger']
        if not any(t in filtri.get("tournament", []) for t in tornei_validi):
            continue
        if e.get("status", {}).get("type") == "finished":
            continue

        p1 = e.get("homeTeam", {}).get("name", "")
        p2 = e.get("awayTeam", {}).get("name", "")
        torneo = e.get("uniqueTournament", {}).get("name", "")
        superficie = e.get("groundType", "")
        event_id = e.get("id")

        if p1 and p2:
            partite.append({
                "id": event_id,
                "p1": p1, "p2": p2,
                "torneo": torneo,
                "superficie": superficie,
                "source": "sofascore"
            })
    return partite

def salva_value_bets_excel(value_bets, filepath="data/value_bets_log.xlsx"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    verde_scuro  = PatternFill("solid", fgColor="1E7145")
    verde_chiaro = PatternFill("solid", fgColor="C6EFCE")
    bianco       = PatternFill("solid", fgColor="FFFFFF")
    giallo       = PatternFill("solid", fgColor="FFEB9C")
    azzurro      = PatternFill("solid", fgColor="BDD7EE")
    bordo = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    oggi = datetime.now().strftime("%Y-%m-%d")

    if os.path.exists(filepath):
        wb = load_workbook(filepath)
        ws = wb.active

        # Raccogli partite già presenti oggi per evitare duplicati
        partite_oggi = set()
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == oggi:
                # key = (giocatore, avversario)
                partite_oggi.add((str(row[2]).strip(), str(row[3]).strip()))

        prossima_riga = ws.max_row + 1
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Value Bets Log"
        partite_oggi = set()

        headers = [
            "Data", "Ora", "🎯 PUNTA SU", "Avversario",
            "Torneo", "Superficie", "Quota", "Quota Min",
            "Prob Elo %", "EV %", "Elo Usato", "Fonte", "Esito", "Profitto"
        ]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = verde_scuro
            cell.font = Font(bold=True, color="FFFFFF", size=11)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = bordo

        ws.row_dimensions[1].height = 30
        prossima_riga = 2

    ora_now = datetime.now()
    aggiunte = 0
    saltate = 0

    for i, v in enumerate(value_bets):
        giocatore = v['p1']
        avversario = v['p2']

        # Controlla duplicato
        key = (giocatore.strip(), avversario.strip())
        key_inv = (avversario.strip(), giocatore.strip())
        if key in partite_oggi or key_inv in partite_oggi:
            saltate += 1
            continue

        partite_oggi.add(key)
        riga = prossima_riga + aggiunte
        fill = verde_chiaro if aggiunte % 2 == 0 else bianco

        valori = [
            ora_now.strftime("%Y-%m-%d"),
            ora_now.strftime("%H:%M"),
            f"✅ {giocatore}",          # Chi scommettere
            avversario,
            v['torneo'],
            v['superficie'].upper(),
            v['quota_p1'],              # Quota attuale
            v['quota_equa'],            # Quota minima accettabile
            round(v['prob_reale'] * 100, 1),
            round(v['ev'] * 100, 1),
            v.get('elo_usato', ''),
            v.get('source', ''),
            "",
            ""
        ]

        for col, val in enumerate(valori, 1):
            cell = ws.cell(row=riga, column=col, value=val)
            cell.border = bordo
            cell.alignment = Alignment(horizontal="center", vertical="center")

            # Colonna "PUNTA SU" in azzurro con font bold
            if col == 3:
                cell.fill = azzurro
                cell.font = Font(bold=True, size=11)
                cell.alignment = Alignment(horizontal="left", vertical="center")
            # Colonna quota attuale
            elif col == 7:
                cell.fill = fill
                cell.font = Font(bold=True, size=12)
            # Colonna quota minima
            elif col == 8:
                cell.fill = PatternFill("solid", fgColor="FFE699")
                cell.font = Font(italic=True)
            # Colonna EV con colori
            elif col == 10 and isinstance(val, float):
                if val >= 50:
                    cell.fill = PatternFill("solid", fgColor="FF0000")
                    cell.font = Font(bold=True, color="FFFFFF")
                elif val >= 20:
                    cell.fill = PatternFill("solid", fgColor="FFC000")
                    cell.font = Font(bold=True)
                elif val >= 10:
                    cell.fill = giallo
                else:
                    cell.fill = fill
            else:
                cell.fill = fill

        ws.row_dimensions[riga].height = 22
        aggiunte += 1

    # Larghezze colonne
    larghezze = [12, 8, 28, 22, 30, 10, 8, 10, 10, 8, 12, 12, 8, 10]
    for col, width in enumerate(larghezze, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    ws.freeze_panes = "A2"
    wb.save(filepath)
    print(f"\n💾 {aggiunte} nuove value bet salvate | {saltate} duplicati saltati → {filepath}")

def analizza_partite(partite, ratings_ta, soglia_ev, get_quote_fn):
    value_bets = []
    no_value = []
    non_trovati = []
    senza_quote = []

    for p in partite:
        # Determina superficie
        sup_raw = p.get('superficie', '')
        sup = normalizza_superficie(sup_raw)
        if sup == 'hard' and not sup_raw:
            sup = superficie_da_torneo(p.get('torneo', ''))

        # Cerca giocatori in Tennis Abstract
        n1, r1 = trova_giocatore_ta(p['p1'], ratings_ta)
        n2, r2 = trova_giocatore_ta(p['p2'], ratings_ta)

        if not r1 or not r2:
            mancante = p['p1'] if not r1 else p['p2']
            non_trovati.append(f"{p['p1']} vs {p['p2']} (manca: {mancante})")
            continue

        # Elo specifico per superficie
        e1 = r1.get(sup, r1['elo'])
        e2 = r2.get(sup, r2['elo'])
        elo_usato = f"TA-{sup}"

        # Quote
        q1, q2 = get_quote_fn(p['id'])
        time.sleep(0.2)

        if not q1 or not q2:
            senza_quote.append(f"{p['p1']} vs {p['p2']}")
            continue

        # Calcola segnale P1
        segnale = genera_segnale(n1, e1, n2, e2, q1)

        entry = {
            "p1": p['p1'], "p2": p['p2'],
            "torneo": p['torneo'],
            "superficie": sup,
            "quota_p1": q1, "quota_p2": q2,
            "prob_reale": segnale['prob_reale'],
            "ev": segnale['ev'],
            "quota_equa": segnale['quota_equa'],
            "elo_usato": elo_usato,
            "source": p.get('source', ''),
        }

        if segnale['ev'] >= soglia_ev:
            value_bets.append(entry)
        else:
            # Controlla anche P2
            segnale2 = genera_segnale(n2, e2, n1, e1, q2)
            if segnale2['ev'] >= soglia_ev:
                value_bets.append({
                    "p1": p['p2'], "p2": p['p1'],
                    "torneo": p['torneo'],
                    "superficie": sup,
                    "quota_p1": q2, "quota_p2": q1,
                    "prob_reale": segnale2['prob_reale'],
                    "ev": segnale2['ev'],
                    "quota_equa": segnale2['quota_equa'],
                    "elo_usato": elo_usato,
                    "source": p.get('source', ''),
                })
            else:
                no_value.append(entry)

    return value_bets, no_value, non_trovati, senza_quote

def scansiona(soglia_ev=0.05):
    print(f"{'='*65}")
    print(f"  🎾 TENNIS SCANNER - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*65}\n")

    # ==========================================
    # SAFETY CHECK — blocca se fonti non disponibili
    # ==========================================
    print("🔒 Safety check fonti dati...")

    ok_ta, msg_ta = verifica_disponibilita()
    print(f"  Tennis Abstract : {'✅' if ok_ta else '❌'} {msg_ta}")

    ok_odds = False
    if ODDS_API_IO_KEY:
        try:
            r = requests.get(
                "https://api.odds-api.io/v3/sports",
                params={"apiKey": ODDS_API_IO_KEY}, timeout=5
            )
            ok_odds = r.status_code == 200
            print(f"  Odds-API.io     : {'✅' if ok_odds else '❌'} Status {r.status_code}")
        except Exception as e:
            print(f"  Odds-API.io     : ❌ {e}")

    if not ok_ta:
        print("\n🚨 BLOCCO: Tennis Abstract non disponibile.")
        print("   I rating Elo non sono aggiornati — scanner fermato.")
        print("   ⚠️  NON INVESTIRE senza dati Elo verificati.\n")
        return

    if not ok_odds:
        print("\n🚨 BLOCCO: Odds-API.io non disponibile.")
        print("   Le quote non sono recuperabili — scanner fermato.")
        print("   ⚠️  NON INVESTIRE senza quote verificate.\n")
        return

    print("\n✅ Tutte le fonti disponibili — procedo\n")

    # ==========================================
    # CARICA ELO AGGIORNATO
    # ==========================================
    print("⚙️  Caricamento Elo Tennis Abstract...")
    ratings_ta = carica_elo_aggiornato()
    if not ratings_ta:
        print("🚨 BLOCCO: Nessun dato Elo caricato — scanner fermato.")
        return
    print(f"✅ {len(ratings_ta)} giocatori caricati\n")

    # ==========================================
    # RECUPERA PARTITE
    # ==========================================
    all_value_bets = []
    all_no_value = []
    all_non_trovati = []
    all_senza_quote = []

    # Fonte 1: odds-api.io
    print("📅 Recupero partite da Odds-API.io...")
    partite_apiio = get_partite_con_quote_oggi()
    partite_apiio = [p for p in partite_apiio if any(
        x in p['torneo'] for x in ['ATP', 'WTA', 'Challenger']
    )]
    print(f"✅ {len(partite_apiio)} partite ATP/WTA trovate\n")

    vb, nv, nt, sq = analizza_partite(
        partite_apiio, ratings_ta, soglia_ev, get_quote_apiio
    )
    all_value_bets.extend(vb)
    all_no_value.extend(nv)
    all_non_trovati.extend(nt)
    all_senza_quote.extend(sq)

    # Fonte 2: Sofascore (per superficie e partite extra)
    print("📅 Recupero partite da Sofascore...")
    partite_sofa = get_partite_sofascore()
    print(f"✅ {len(partite_sofa)} partite trovate\n")

    nomi_apiio = {(p['p1'], p['p2']) for p in partite_apiio}
    partite_extra = [
        p for p in partite_sofa
        if (p['p1'], p['p2']) not in nomi_apiio
        and (p['p2'], p['p1']) not in nomi_apiio
    ]

    if partite_extra:
        print(f"✅ {len(partite_extra)} partite extra solo su Sofascore\n")
        vb2, nv2, nt2, sq2 = analizza_partite(
            partite_extra, ratings_ta, soglia_ev, get_quote_sofascore
        )
        all_value_bets.extend(vb2)
        all_no_value.extend(nv2)
        all_non_trovati.extend(nt2)
        all_senza_quote.extend(sq2)

    # Deduplicazione e ordinamento
    seen = set()
    value_bets_dedup = []
    for v in sorted(all_value_bets, key=lambda x: x['ev'], reverse=True):
        key = tuple(sorted([v['p1'], v['p2']]))
        if key not in seen:
            seen.add(key)
            value_bets_dedup.append(v)

    # ==========================================
    # OUTPUT
    # ==========================================
    print(f"{'='*65}")
    print(f"  RISULTATI SCANNER")
    print(f"{'='*65}")
    print(f"  Analizzate con quote : {len(value_bets_dedup) + len(all_no_value)}")
    print(f"  Senza quote          : {len(all_senza_quote)}")
    print(f"  Non trovati in Elo   : {len(all_non_trovati)}")
    print(f"  VALUE BET ✅         : {len(value_bets_dedup)}")
    print(f"{'='*65}\n")

    if value_bets_dedup:
        print("🎯 VALUE BET TROVATE:\n")
        for v in value_bets_dedup:
            print(f"  ✅ {v['p1']} vs {v['p2']}")
            print(f"     Torneo    : {v['torneo']}")
            print(f"     Superficie: {v['superficie']} | Elo: {v['elo_usato']}")
            print(f"     Quota     : {v['quota_p1']} | Quota equa: {v['quota_equa']}")
            print(f"     Prob Elo  : {v['prob_reale']*100:.1f}% | EV: {v['ev']*100:.1f}%")
            print()
    else:
        print("  Nessuna value bet trovata oggi.")

    if all_senza_quote:
        print(f"\n⚠️  Senza quote ({len(all_senza_quote)}):")
        for s in all_senza_quote[:5]:
            print(f"  - {s}")

    if all_non_trovati:
        print(f"\n⚠️  Non trovati in Elo ({len(all_non_trovati)}):")
        for n in all_non_trovati[:5]:
            print(f"  - {n}")

    salva_value_bets_excel(value_bets_dedup)

if __name__ == "__main__":
    scansiona()