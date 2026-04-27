# Tennis Scanner - Contesto Progetto

## Obiettivo
Scanner automatico per value bet nel tennis. Identifica partite dove
le quote di mercato sottovalutano la probabilità reale di vittoria,
calcolata tramite rating Elo aggiornati.

## Architettura Attuale
tennis_scanner/
├── config.py              # API keys e parametri
├── modules/
│   ├── elo.py             # Elo storico da CSV Sackmann (2024)
│   ├── elo_tennisabstract.py  # Elo aggiornato da Tennis Abstract
│   ├── signals.py         # Calcolo EV = (prob × quota) - 1
│   ├── scanner.py         # Scanner principale - CORE del progetto
│   ├── odds_apiio.py      # Quote da Odds-API.io
│   └── data_updater.py    # Downloader dati storici
├── data/
│   ├── storico/           # CSV Sackmann ATP/WTA 2024
│   ├── elo_cache/         # Cache Elo Tennis Abstract (24h)
│   └── value_bets_log.xlsx  # Log giocate con esito
└── test.py                # Backtest su giocate Pro

## Fonti Dati
- **Elo ratings**: Tennis Abstract (tennisabstract.com) - 1059 giocatori
  aggiornati settimanalmente, con Elo generale + clay + hard + grass
- **Partite del giorno**: Odds-API.io + Sofascore fallback
- **Quote**: Odds-API.io (Bet365, Betano, Bwin IT, Eurobet IT)

## Come Funziona lo Scanner (scanner.py)
1. Safety check — verifica che Tennis Abstract e Odds-API.io siano raggiungibili
2. Carica Elo aggiornato da Tennis Abstract (cache 24h)
3. Recupera partite del giorno da Odds-API.io
4. Per ogni partita: trova Elo giocatori, prende quote, calcola EV
5. Salva value bet in Excel con colori e formattazione

## Formula EV
EV = (probabilità_elo × quota_mercato) - 1
Se EV > 5% → VALUE BET

## Superficie
Inferita dal nome torneo tramite `superficie_da_torneo()`.
Madrid/Rome/Roland Garros → clay
Wimbledon/Halle → grass
Default → hard

## Problemi Noti / Da Migliorare
1. Tennis Abstract aggiornato solo settimanalmente — gap dati recenti
2. Odds-API.io piano free limitato a 5 bookmaker
3. Nessun tracking automatico risultati — esito compilato manualmente
4. Nessuna notifica automatica — scanner va lanciato manualmente
5. Dati storici fermi al 2024 — Sackmann non ha ancora 2025

## Prossimi Step Pianificati
1. Notifiche Telegram automatiche quando trova value bet
2. Cronjob automatico mattutino (Windows Task Scheduler)
3. Dashboard ROI — calcolo automatico win rate e profitto
4. Head-to-head tra i due giocatori come segnale aggiuntivo
5. Forma recente — ultime N partite pesano di più dell'Elo globale