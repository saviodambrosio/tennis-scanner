import requests
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def get_quote_tennis_oggi():
    url = "https://www.oddsportal.com/tennis/results/"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {resp.status_code}")
        print(f"Dimensione risposta: {len(resp.text)} caratteri")
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Salva HTML per debug
        with open("data/oddsportal_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("✅ HTML salvato in data/oddsportal_debug.html")
        
        # Cerca le partite
        righe = soup.find_all("div", class_=lambda c: c and "event" in c.lower())
        print(f"Trovati {len(righe)} elementi 'event'")
        
        # Stampa prime classi trovate per capire la struttura
        tutti = soup.find_all("div", limit=50)
        classi = set()
        for d in tutti:
            if d.get("class"):
                classi.add(" ".join(d["class"]))
        print("\nPrime classi DIV trovate:")
        for c in list(classi)[:20]:
            print(f"  {c}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    get_quote_tennis_oggi()