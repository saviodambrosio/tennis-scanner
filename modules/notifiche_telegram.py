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
        requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": testo, "parse_mode": "HTML"},
            timeout=10,
        )
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
    from datetime import datetime
    intestazione = f"📋 <b>Report — {datetime.now().strftime('%d/%m/%Y %H:%M')}</b>"
    testo = f"{intestazione}\n\n{formatta_value_bets_ml(vb_ml)}\n\n{formatta_value_bets_handicap(vb_handicap)}"
    invia_messaggio(testo)
