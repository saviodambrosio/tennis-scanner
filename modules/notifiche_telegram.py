import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ABILITATO
except ImportError:
    TELEGRAM_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
    TELEGRAM_ABILITATO = False


def invia_messaggio(testo):
    if not TELEGRAM_ABILITATO:
        print(f"[Telegram disabilitato] {testo}")
        return
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": testo, "parse_mode": "HTML"},
            timeout=10,
        )
        if not resp.ok:
            print(f"[Telegram] Errore API {resp.status_code}: {resp.text}")
        else:
            print(f"[Telegram] Messaggio inviato OK ({len(testo)} chars)")
    except Exception as e:
        print(f"[Telegram] Errore invio: {e}")


def formatta_value_bets_ml(value_bets):
    if not value_bets:
        return "🎾 <b>Scanner ML</b>\nNessuna value bet trovata oggi."
    righe = [f"🎾 <b>VALUE BET — MONEY LINE</b>  ({len(value_bets)})", ""]
    for v in value_bets:
        righe.append(f"✅ <b>{v['p1']}</b> vs {v['p2']}")
        righe.append(f"   📍 {v['torneo']} | {v['superficie'].upper()}")
        righe.append(f"   💶 Quota: {v['quota_p1']} | Equa: {v['quota_equa']}")
        righe.append(f"   📊 Prob: {v['prob_reale']*100:.1f}% | EV: {v['ev']*100:.1f}%")
        righe.append("")
    return "\n".join(righe)


def formatta_value_bets_handicap(value_bets):
    if not value_bets:
        return "🎲 <b>Scanner Handicap</b>\nNessuna value bet trovata oggi."
    righe = [f"🎲 <b>VALUE BET — HANDICAP GAMES</b>  ({len(value_bets)})", ""]
    for v in value_bets:
        righe.append(f"✅ <b>{v['p1']}</b> vs {v['p2']}")
        righe.append(f"   📍 {v['torneo']} | {v['superficie'].upper()}")
        righe.append(f"   🎯 Handicap: {v.get('handicap', '')} | Quota: {v.get('quota_handicap', '')}")
        righe.append(f"   📊 Prob: {v['prob_stimata']*100:.1f}% | EV: {v['ev']*100:.1f}%")
        righe.append("")
    return "\n".join(righe)


def invia_report_giornaliero(vb_ml, vb_handicap):
    import os
    import requests
    from datetime import datetime

    print(f"[Telegram] report chiamato: {len(vb_ml)} ML, {len(vb_handicap)} handicap")

    ora = datetime.now().strftime("%d/%m %H:%M")
    intestazione = (
        f"Report {ora}\n"
        f"ML: {len(vb_ml)} value bet\n"
        f"Handicap: {len(vb_handicap)} value bet\n"
        f"Vedi file Excel allegato"
    )
    invia_messaggio(intestazione)

    if not TELEGRAM_ABILITATO:
        return

    excel_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'value_bets_log.xlsx')
    excel_path = os.path.abspath(excel_path)

    if not os.path.exists(excel_path):
        print(f"[Telegram] WARNING: file Excel non trovato: {excel_path}")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
        with open(excel_path, 'rb') as f:
            resp = requests.post(
                url,
                data={"chat_id": TELEGRAM_CHAT_ID},
                files={"document": (os.path.basename(excel_path), f)},
                timeout=30,
            )
        if not resp.ok:
            print(f"[Telegram] Errore invio Excel {resp.status_code}: {resp.text}")
        else:
            print(f"[Telegram] File Excel inviato OK")
    except Exception as e:
        print(f"[Telegram] Errore invio Excel: {e}")
