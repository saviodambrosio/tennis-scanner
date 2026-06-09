# TENNIS SCANNER — DOCUMENTO DI STATO
> Memoria tecnica del progetto. Aggiornato al 09/06/2026.

---

## OBIETTIVO DEL PROGETTO
Scanner per value bet nel tennis: stima le probabilità di vittoria con modelli
quantitativi (Elo e Markov punto-per-punto) e le confronta con le quote live dei
bookmaker per individuare scommesse a valore atteso positivo.
Progetto completato e pubblicato come portfolio — conclusione principale: il modello
non produce CLV positivo su mercati liquidi ATP/WTA.

---

## STACK TECNICO
- Python 3.10+
- VS Code + venv Windows
  - Attivare venv: `.\venv\Scripts\Activate.ps1`
- Librerie: pandas, numpy, requests, openpyxl, beautifulsoup4, python-dotenv
- GitHub pubblico: https://github.com/saviodambrosio/tennis-scanner (branch master)
- Cartella locale: C:\Users\savio\Desktop\tennis_scanner\

---

## ARCHITETTURA FILES

```
tennis_scanner/
├── config.py                    # Parametri e soglie (segreti via .env)
├── main.py                      # Entry point: lancia Scanner A poi Scanner B
├── valida_modelli.py            # Validazione CLV: Elo vs Markov vs closing line
├── test_markov.py               # Test unitari matematica Markov
├── requirements.txt
├── .env.example                 # Template chiavi (valori reali in .env, ignorato da git)
├── modules/
│   ├── markov.py                # Modello Markov punto-per-punto (Barnett-Clarke)
│   ├── elo_tennisabstract.py    # Scarica/carica Elo da Tennis Abstract (1060 giocatori)
│   ├── signals.py               # Probabilità da Elo + calcolo EV
│   ├── scanner.py               # Scanner A — Money Line
│   ├── scanner_handicap.py      # Scanner B — Handicap Games + Sets
│   ├── odds_apiio.py            # Quote ML + handicap da Odds-API.io
│   ├── forma_recente.py         # Forma recente, H2H, fatica
│   ├── data_2025.py             # Download dati TML-Database + Tennisexplorer
│   └── notifiche_telegram.py    # Invio report + Excel su Telegram
├── data/
│   ├── storico/                 # CSV partite ATP/WTA (Sackmann format)
│   └── elo_cache/               # Cache Elo Tennis Abstract (24h)
└── data/value_bets_log.xlsx     # Log giocate (2 sheet: Value Bets Log + Handicap Bets)
```

---

## CONFIG.PY — PARAMETRI PRINCIPALI

```python
# Segreti letti da .env (mai hardcoded)
ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "")

MODELLO = "markov"               # "elo" o "markov"
TELEGRAM_ABILITATO = True
EV_MINIMO = 0.09                 # 9% EV lordo minimo
EV_MAX = None
ODDS_MIN = 1.40
ODDS_MAX = 6.00
ODDS_MIN_VALUE = 1.80            # Filtro range Pro
ODDS_MAX_VALUE = 4.00
```

NOTA EV: L'EV è LORDO — non considera l'aggio del bookmaker (~6%).
Per avere valore reale positivo serve EV lordo > 9% (aggio 6% + margine 3%).
EV_MINIMO = 0.09 è calibrato per coprire l'aggio.

---

## FONTI DATI

- Tennis Abstract: Elo per 1060 giocatori (gen/clay/hard/grass) — cache 24h
- Odds-API.io (free): Quote ML + handicap — Bet365, Betano, Bwin IT, Eurobet IT
- TML-Database GitHub: Risultati ATP 2025-2026 formato Sackmann — download se >24h
- Tennisexplorer.com: Risultati recenti ultimi 60gg (ATP+WTA) — download se >24h

NOTA Odds-API.io: Il parametro market viene IGNORATO dall'API — restituisce sempre
tutti i mercati. Nome corretto per handicap games: "Spread (Games)" con chiave hdp.
Nome per handicap sets: "Spread (Sets)" con chiave hdp.

---

## SCANNER A — MONEY LINE (scanner.py)

Flusso:
1. Safety check — verifica Tennis Abstract e Odds-API.io raggiungibili
2. Carica Elo Tennis Abstract (cache 24h)
3. Download automatico dati 2026 e risultati recenti (se >24h)
4. Recupera partite Odds-API.io per i prossimi 1-4 giorni (NON oggi)
5. FASE 1: Calcola Elo aggiustato forma/H2H/fatica per ogni partita
6. FASE 2: Fetch quote in PARALLELO con ThreadPoolExecutor(max_workers=10)
   + rate limiter 10 req/s (2-5x più veloce del loop sequenziale)
7. FASE 3: Calcola EV, applica filtro range Pro (1.80-4.00),
   sanity check quote invertite via Elo
8. Filtro EV >= 9%
9. Salva Excel con deduplicazione su (data_partita, giocatore, avversario)
   — controlla TUTTA la storia, non solo oggi
   — pulizia automatica duplicati esistenti ad ogni esecuzione
10. Aggiorna esiti W/L da risultati_recenti.csv
11. Invia report Telegram

Formula EV: EV = (prob_elo × quota_mercato) - 1

---

## SCANNER B — HANDICAP (scanner_handicap.py)

Calibrazione empirica da 2500 partite ATP 2025:
- Diff Elo 0-50:   +0.4 games, 55.6% fav vince
- Diff Elo 50-100: +1.1 games, 61.3%
- Diff Elo 100-150: +2.1 games, 68.8%
- Diff Elo 150-200: +2.6 games, 74.6%
- Diff Elo 200+:   +4.2 games, 82.6%
- sigma = 4.8 games (costante)

Calibrazione set:
- Diff 0-50: P(2-0 fav) = 35%
- Diff 50-100: 42%
- Diff 100-150: 50%
- Diff 150-200: 58%
- Diff 200+: 65%

Logica:
- prob_copre = P(margine_reale > -H) con N(margine_atteso, 4.8)
- EV = (prob_copre × quota_handicap) - 1
- Filtro range Pro: solo quote handicap tra 1.80 e 4.00
- Salva in sheet "Handicap Bets" con colonna Tipo (Games/Sets)

---

## PESI DEL MODELLO (calibrati 12/05/2026)

- Forma recente: ±100 punti Elo (ridotto da 150 — era troppo aggressivo)
- H2H storico: ±50 punti Elo (ridotto da 75 — pochi dati su Challenger)
  - Decay esponenziale half-life 2 anni
  - Solo se >= 3 precedenti trovati, altrimenti 0.0
- Fatica: max -100 punti
  - Si attiva SOLO con 2+ partite negli ultimi 2 giorni (era: 1+ in 3 giorni)
  - 2 partite → -0.6, 3+ partite → -1.0

---

## LE GIOCATE DEI PRO — CONTESTO FONDAMENTALE

Chi sono i Pro: canale Telegram "sandrone" (alias "Supsporc"). ~10% ROI costante.
Le giocate arrivano da un amico e sono il benchmark del sistema.

PATTERN CHIAVE (analisi su ~230 giocate in pro_bets.csv):

1. SEMPRE pacchetti compositi per ogni match:
   - Riga 1: ML (Money Line — vincitore)
   - Riga 2-3: Handicap Games (+/- X.5 games)
   - Riga 4: Handicap Sets (+/- 1.5 sets)

2. QUASI SEMPRE sull'underdog o giocatore sfavorito
   Quote ML tipiche: 1.80-4.00. RARAMENTE sotto 1.80, mai sopra ~5.00

3. NON giocano sui favoriti netti sotto 1.80

4. Logica del pacchetto: riduce varianza. Anche se il giocatore perde la
   partita, handicap games/sets può comunque coprire.

Esempi reali (Madrid aprile 2026):
  WTA Madrid - Townsend (outsider) vs Boulter (favorita):
    Townsend ML: 2.08
    Townsend +0.5 games: 2.00
    Townsend +1.5 games: 1.88
    Townsend +1.5 sets: 1.46
  
  ATP Madrid - Monfils (outsider) vs Carabelli:
    Monfils ML: 2.50
    Monfils +2.5 games: 1.93
    Monfils +1.5 sets: 1.57
  
  ATP Challenger - Roncadelli (grande outsider a 4.05) vs Basavareddy:
    Roncadelli ML: 4.05
    Roncadelli +5.5 games: 1.70
    Roncadelli +4.5 games: 2.10

Formato pro_bets.csv:
date,tournament,type,player1,player2,bet_type,handicap,odds_decimal,odds_american,esito

---

## ANALISI CLV (dati reali aprile-maggio 2026)

CLV medio = -2.84% — sistematicamente negativo su ~20 giocate analizzate.

Il mercato si muove CONTRO di noi quasi sempre dopo i nostri scan.
Quote che salgono = mercato non d'accordo = segnale negativo.
Quote che scendono = mercato d'accordo = CLV positivo.

Causa: il modello trova value sui favoriti dove il mercato è già efficiente.
I bookmaker sui tornei ATP principali usano modelli molto sofisticati.

Dove i bookmaker sono più deboli:
1. Challenger minori (Shymkent, Abidjan, Brazzaville)
2. Prime 12-24 ore dopo apertura quote
3. Handicap games sui Challenger (linee automatiche)
4. Inizio stagione clay (aprile) — modelli ancora calibrati su hard

Lezione pratica:
- EV lordo 5-8% → probabilmente neutro/negativo dopo aggio
- EV lordo > 15% → potenzialmente interessante
- EV lordo > 40-50% → quasi certamente errore di matching, NON giocare

---

## COME LEGGERE I PUNTEGGI TENNIS

Struttura: vince chi vince 2 set su 3 (o 3 su 5 nei Grand Slam).
Ogni set: vince chi fa 6 games con 2 di vantaggio (tiebreak al 6-6).

6-4 6-3 = vincitore 12 games, perdente 7 games (vittoria 2-0 netta)
6-4 3-6 7-5 = partita combattuta, vinta 2-1 in set
7-6 6-7 7-6 = tre tiebreak, partita vicinissima

Calcolo handicap games:
Somma tutti i games di ciascun giocatore e aggiungi/sottrai l'handicap.
Esempio: 6-4 3-6 7-5 → vincitore 16 games, perdente 15 games.
Con +1.5 games al perdente: 15+1.5=16.5 vs 16 → VINCE l'handicap!

Handicap sets:
+1.5 sets = basta vincere almeno 1 set (molto probabile)
-1.5 sets = devi vincere 2-0 (devi dominare)

---

## TELEGRAM

TELEGRAM_CHAT_ID deve essere INTERO, non stringa.
Errore comune: "483228005" invece di 483228005 → errore 400 "chat not found"

Per aggiungere un amico al gruppo:
1. Crea gruppo Telegram con te, amico e il bot
2. Manda un messaggio nel gruppo
3. Vai su https://api.telegram.org/bot{TOKEN}/getUpdates
4. Il chat_id del gruppo è NEGATIVO (es. -123456789)
5. Aggiorna TELEGRAM_CHAT_ID con il numero negativo

---

## EXCEL — STRUTTURA

Sheet 1 "Value Bets Log" (ML):
Data, Ora, PUNTA SU, Avversario, Torneo, Superficie, Quota, Quota Min,
Prob Elo%, EV%, Elo Usato, Fonte, Quota Apertura, Quota Chiusura, CLV%, Esito, Profitto
Profitto: W = quota-1, L = -1

Sheet 2 "Handicap Bets":
Data, Ora, Tipo(Games/Sets), Punta su(handicap), Avversario, Handicap,
Quota, Quota di chiusura, Prob%, EV%, Torneo, Superficie, Elo Diff,
Margine Atteso, Elo Usato, Fonte

Deduplicazione: chiave (data_partita, giocatore, avversario)
Controlla TUTTA la storia, NON solo oggi.
Pulizia automatica duplicati ad ogni lancio.

---

## STATO FINALE DEL PROGETTO

### Implementato e funzionante
- Scanner A — Money Line (Elo + Markov, fetch quote in parallelo) ✅
- Scanner B — Handicap Games + Sets ✅
- Modello Markov punto-per-punto (Barnett-Clarke) con adjustment contestuali ✅
- Modello Elo con forma recente, H2H decay, fatica ✅
- Validazione CLV su 57 match — risultato negativo documentato ✅
- Log Excel con deduplicazione e aggiornamento esiti W/L ✅
- Notifiche Telegram con Excel allegato ✅
- Segreti in .env, mai hardcoded ✅
- README bilingue (EN + IT) con risultati onesti ✅
- Test unitari modello Markov ✅

### Deliberatamente abbandonato
- **VPS/scheduler automatico** — progetto finalizzato come portfolio locale; la complessità
  operativa (Task Scheduler, git pull automatico, Python 3.14 compatibility) non aggiungeva
  valore dimostrativo una volta che il CLV negativo era confermato
- **Dashboard ROI Excel** — irrilevante con CLV sistematicamente negativo
- **Filtro movement quote** — richiederebbe polling continuo incompatibile con uso locale
- **Completamento esiti Challenger** — dati troppo rumorosi per validazione statistica seria

### Direzioni future (documentate nel README)
- Mercati illiquidi (ITF / Challenger minori) dove i bookmaker usano modelli grezzi
- Segnali di line-movement nelle prime ore dopo apertura quote
- Dati proprietari (infortuni, calendario) non ancora nel prezzo di mercato

---

## COMANDI UTILI

# Attivare venv locale
.\venv\Scripts\Activate.ps1

# Lanciare scanner completo
python main.py

# Validazione modelli
python valida_modelli.py

# Test unitari Markov
python test_markov.py

# Commit e push
git add .
git commit -m "messaggio"
git push

---

## NOTE TECNICHE SPECIFICHE

Matching nomi: trova_giocatore_ta gestisce varianti (case, cognome, iniziale+cognome).
Odds-API.io usa "Cognome, Nome" → convertito in "Nome Cognome" prima del matching.

Superficie da torneo: i Challenger non hanno superficie nell'API.
superficie_da_torneo() la inferisce dal nome città/torneo. Default: hard.

Sanity check quote: se quota P1 > 8.0 ma Elo dice P1 è favorito → inverte.
Corregge casi in cui home/away sono scambiati nell'API.

Placeholder API: R16P1, WQF3, ecc. = partite future con giocatori non ancora noti.
Vengono sostituiti dai nomi reali man mano che i turni vengono giocati.

Python: testato su 3.10. Richiede beautifulsoup4 e openpyxl (inclusi in requirements.txt).
