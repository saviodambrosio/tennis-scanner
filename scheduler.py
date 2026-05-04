import sys
import os
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import SCHEDULER_ABILITATO, SCHEDULER_ORA_SERA, SCHEDULER_ORA_MATTINA
except ImportError:
    SCHEDULER_ABILITATO = False
    SCHEDULER_ORA_SERA = "21:00"
    SCHEDULER_ORA_MATTINA = "08:30"

os.makedirs("data", exist_ok=True)

logging.basicConfig(
    filename="data/scheduler.log",
    level=logging.INFO,
    format="%(asctime)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)


def log(msg):
    print(msg)
    logging.info(msg)


def esegui_scansione():
    from modules.scanner import scansiona
    from modules.scanner_handicap import scansiona_handicap
    from modules.notifiche_telegram import invia_report_giornaliero
    from config import EV_MAX

    log("Avvio scansione schedulata...")
    vb_ml = []
    vb_hdp = []

    try:
        vb_ml = scansiona(ev_max=EV_MAX) or []
        log(f"Scanner ML completato — {len(vb_ml)} value bet trovate")
    except Exception as e:
        log(f"ERRORE Scanner ML: {e}")

    try:
        vb_hdp = scansiona_handicap(ev_max=EV_MAX) or []
        log(f"Scanner Handicap completato — {len(vb_hdp)} value bet trovate")
    except Exception as e:
        log(f"ERRORE Scanner Handicap: {e}")

    try:
        invia_report_giornaliero(vb_ml, vb_hdp)
        log("Report inviato (Telegram o console)")
    except Exception as e:
        log(f"ERRORE notifica Telegram: {e}")


def loop():
    orari = {SCHEDULER_ORA_MATTINA, SCHEDULER_ORA_SERA}
    eseguiti_oggi = set()

    log(f"Scheduler avviato — orari: {SCHEDULER_ORA_MATTINA} e {SCHEDULER_ORA_SERA}")

    while True:
        now = datetime.now()
        ora_corrente = now.strftime("%H:%M")
        data_corrente = now.strftime("%Y-%m-%d")
        chiave = f"{data_corrente}_{ora_corrente}"

        if ora_corrente in orari and chiave not in eseguiti_oggi:
            eseguiti_oggi.add(chiave)
            log(f"Lancio scansione alle {ora_corrente}")
            esegui_scansione()

        if ora_corrente == "00:01":
            eseguiti_oggi.clear()

        time.sleep(30)


if __name__ == "__main__":
    if not SCHEDULER_ABILITATO:
        print("Scheduler disabilitato (SCHEDULER_ABILITATO = False in config.py).")
        print("Per attivarlo: imposta SCHEDULER_ABILITATO = True in config.py e rilancia.")
        sys.exit(0)
    loop()
