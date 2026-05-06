import sys
import os
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import EV_MAX
from modules.scanner import scansiona
from modules.scanner_handicap import scansiona_handicap
from modules.notifiche_telegram import invia_report_giornaliero

SEP = "=" * 65

def main():
    print(SEP)
    print(f"  TENNIS SCANNER SUITE - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(SEP)
    print()

    print(SEP)
    print("  SCANNER A — MONEY LINE")
    print(SEP)
    vb_ml = scansiona(ev_max=EV_MAX) or []

    print()
    print(SEP)
    print("  SCANNER B — HANDICAP GAMES")
    print(SEP)
    vb_hdp = scansiona_handicap(ev_max=EV_MAX) or []

    print()
    print(SEP)
    print("  RIEPILOGO TOTALE")
    print(SEP)
    print(f"  Value bet ML trovate       : {len(vb_ml)}")
    print(f"  Value bet Handicap trovate : {len(vb_hdp)}")
    print(f"  Risultati salvati in data/value_bets_log.xlsx")
    print(SEP)

    invia_report_giornaliero(vb_ml, vb_hdp)

if __name__ == "__main__":
    main()
