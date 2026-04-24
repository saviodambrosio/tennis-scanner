import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import BETFAIR_API_KEY

BETFAIR_ENDPOINT = "https://api.betfair.com/exchange/betting/json-rpc/v1"

HEADERS = {
    "X-Application": BETFAIR_API_KEY,
    "X-Authentication": "",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def test_connessione():
    payload = [
        {
            "jsonrpc": "2.0",
            "method": "SportsAPING/v1.0/listEventTypes",
            "params": {"filter": {}},
            "id": 1
        }
    ]
    try:
        resp = requests.post(BETFAIR_ENDPOINT, json=payload, headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Risposta: {resp.text[:500]}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_connessione()