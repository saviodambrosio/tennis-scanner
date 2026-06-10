# 🎾 Tennis Value Betting Scanner

> An automated system that scans professional tennis matches for betting value by comparing model-derived probabilities against live bookmaker odds — and an honest quantitative study of whether such an edge actually exists.

🇮🇹 *[Versione italiana →](README.it.md)*

---

## TL;DR

This project builds an end-to-end pipeline that:
1. **Scrapes** player ratings (Elo + serve/return stats) from public sources
2. **Estimates** win probabilities using two independent models (Elo and a point-by-point Markov model)
3. **Compares** those probabilities against live odds from The Odds API and Betfair to flag "value bets" (positive expected value)
4. **Logs and validates** every pick to measure real predictive performance

**The most important finding is a negative one:** rigorous analysis of Closing Line Value (CLV) showed the model does *not* beat the market. This README documents both the engineering and that conclusion, because knowing *when a strategy doesn't work* — and being able to prove it — matters more than a backtest that looks good.

---

## Why this project

I wanted to answer a concrete question: **can a model built on publicly available data find systematic value in tennis betting markets?**

It's a good question for a portfolio because it touches a lot of real skills — web scraping, probabilistic modelling, API integration, statistical validation, and automation — and because the *honest* answer requires resisting the temptation to overfit until the numbers look nice.

---

## Architecture

```
tennis-scanner/
├── main.py                      # Entry point: runs ML + Handicap scanners
├── config.py                    # Configuration (thresholds, model choice, secrets via .env)
├── modules/
│   ├── scanner.py               # Money Line scanner
│   ├── scanner_handicap.py      # Handicap scanner
│   ├── markov.py                # Point-by-point model (Barnett-Clarke)
│   ├── signals.py               # Elo-based probability (prob_da_elo)
│   ├── elo_tennisabstract.py    # Scrapes Elo + age from Tennis Abstract
│   ├── forma_recente.py         # Recent-form adjustment
│   └── notifiche_telegram.py    # Telegram report delivery
├── valida_modelli.py            # Validation: Elo vs Markov vs closing line
├── test_markov.py               # Unit tests for the Markov model
└── data/                        # Elo cache, history, Excel log (gitignored)
```

### Data flow

```
Tennis Abstract (Elo, serve/return, age)
            │
            ▼
   ┌─────────────────┐      ┌──────────────────────┐
   │  Elo model      │      │  Markov model        │
   │  (signals.py)   │      │  (markov.py)         │
   └────────┬────────┘      └──────────┬───────────┘
            │                          │
            └────────────┬─────────────┘
                         ▼
              Win probability estimate
                         │
                         ▼
   ┌──────────────────────────────────────────┐
   │  Live odds (The Odds API + Betfair)       │
   └────────────────────┬─────────────────────┘
                         ▼
            Expected Value (EV) calculation
                         │
                         ▼
        Value bets → Excel log + Telegram alert
                         │
                         ▼
              valida_modelli.py (CLV analysis)
```

---

## The two models

### 1. Elo model

Uses surface-specific Elo ratings (hard / clay / grass) scraped from Tennis Abstract, with adjustments for recent form, head-to-head, and fatigue. Win probability is derived from the standard Elo formula on the rating difference.

### 2. Markov point-by-point model

A more granular approach based on the **Barnett-Clarke** framework. Instead of collapsing a match into a single rating difference, it:

- Estimates each player's probability of winning a point on serve from serve/return statistics
- Propagates that to **game** probability (closed-form),
- then to **set** probability (Markov chain over game states, including the tiebreak),
- then to **match** probability (best-of-3 or best-of-5).

It also supports **contextual adjustments** — extended fatigue (sets played in the last 14 days), age × surface interaction (players over ~33 decline faster on grass), and a parameterised court-pace index.

Both models share the same interface, so the scanner can switch between them via `config.py` for A/B comparison.

---

## Example output

Running `python main.py` launches both scanners sequentially, fetches live odds, and
sends a Telegram report with the Excel log attached. Below is a trimmed real run
(10 June 2026, grass-court season in full swing):

```
$ python main.py
=================================================================
  TENNIS SCANNER SUITE - 10/06/2026 09:48
=================================================================

=================================================================
  SCANNER A — MONEY LINE
=================================================================

🔒 Safety check fonti dati...
  Tennis Abstract : ✅ Tennis Abstract raggiungibile
  Odds-API.io     : ✅ Status 200

✅ Tutte le fonti disponibili — procedo

⚙️  Caricamento Elo Tennis Abstract...
  📦 Cache Elo valida (0.4h fa) — uso quella
✅ 1055 giocatori caricati

📅 Recupero partite da Odds-API.io...
  [+] 2026-06-10: 357 partite trovate
✅ 146 partite ATP/WTA trovate

=================================================================
  RISULTATI SCANNER
=================================================================
  Analizzate con quote : 20
  Senza quote          : 14
  Non trovati in Elo   : 99
  VALUE BET ✅         : 5
=================================================================

🎯 VALUE BET TROVATE:

  ✅ Panna Udvardy vs Daria Snigur
     Torneo    : WTA - S-Hertogenbosch, Netherlands
     Superficie: grass | Elo: TA-grass+forma [markov]
     Quota     : 3.1
     Elo    : prob 43.2% | equa 2.31 | EV +34.1%
     Markov : prob 46.0% | equa 2.18 | EV +42.5%

  ✅ Martin Landaluce vs Taylor Fritz
     Torneo    : ATP - Stuttgart, Germany
     Superficie: hard | Elo: TA-hard+forma [markov]
     Quota     : 3.0
     Elo    : prob 46.5% | equa 2.15 | EV +39.5%
     Markov : prob 38.5% | equa 2.60 | EV +15.4%

  ✅ Jaqueline Cristian vs Katie Boulter
     Torneo    : WTA - London, Great Britain
     Superficie: hard | Elo: TA-hard+forma [markov]
     Quota     : 2.15
     Elo    : prob 51.9% | equa 1.93 | EV +11.5%
     Markov : prob 51.9% | equa 1.93 | EV +11.6%

=================================================================
  SCANNER B — HANDICAP GAMES
=================================================================

  Partite analizzate   : 148
  VALUE BET ✅         : 13

  ✅ Marin Cilic (-1.5 games)  vs  Nuno Borges
     Torneo : ATP - S-Hertogenbosch, Netherlands  |  GRASS  |  Elo diff: 160
     Quota  : 3.1  |  Prob: 57.8%  |  EV: +79.3%

  ✅ Panna Udvardy (+3.5 games)  vs  Daria Snigur
     Torneo : WTA - S-Hertogenbosch, Netherlands  |  GRASS  |  Elo diff: 47
     Quota  : 2.1  |  Prob: 71.9%  |  EV: +51.1%

=================================================================
  RIEPILOGO TOTALE
=================================================================
  Value bet ML trovate       : 5
  Value bet Handicap trovate : 13
  Risultati salvati in data/value_bets_log.xlsx
=================================================================
[Telegram] Messaggio inviato OK
[Telegram] File Excel inviato OK
```

> *Note: the high EV figures shown are the model's own estimates. As detailed in the
> Key results section below, these are systematically inflated — the CLV analysis shows
> the real edge is far smaller. This output illustrates what the scanner produces, not a
> profitable strategy.*

---

## Key results

The system was run on real matches (ATP/WTA Rome, Wuxi Challenger, and others), and every pick was logged with the odds taken and the closing odds.

### Model accuracy (57 matches with recorded closing odds)

| Metric | Elo | Markov | Winner |
|---|---|---|---|
| Brier Score | 0.18503 | 0.18329 | Markov (lower = better) |
| Log-Loss | 0.54916 | 0.54360 | Markov (lower = better) |
| MAE vs Closing Line | 0.0704 | 0.0724 | Elo (marginally closer to market) |

The Markov model predicts outcomes slightly more accurately than Elo — a small but consistent improvement.

### The honest conclusion: Closing Line Value

CLV — how your odds compare to the market's closing odds — is the gold-standard measure of betting edge, because the closing line is the most informed price available. Short-term ROI is dominated by variance; CLV is not.

The calibration analysis was unambiguous:

| Quantity | Value |
|---|---|
| Average probability the **model** assigned | 57% |
| Average probability the **market** (closing) implied | 46% |
| **Actual** win rate | 30% |
| EV the model *calculated* | **+28.2%** |
| EV that was *real* (based on closing odds) | **+1.4%** |

**The model systematically overestimates underdog probabilities.** The "expected value" it reports is mostly the gap between a miscalibrated model and an efficient market — not real edge. The `EV ≥ 9%` filter, far from finding value, was effectively selecting the model's *largest errors*.

This is the central lesson of the project: **on a liquid market, a model built from public data competes against prices that have already absorbed that same information.** The market wins.

### Why this is a feature, not a failure

The temptation in this situation is to keep adding filters ("only clay, only underdogs between 2.1 and 2.4, only on Wednesdays") until a subset shows positive returns. That is textbook **overfitting** — measuring noise in a tiny sample. This project explicitly *refuses* to do that, and instead reports the negative result honestly. Being able to design an experiment, run it, and accept the answer it gives is the actual skill on display here.

---

## Tech stack

- **Python 3.10+**
- **pandas / numpy** — data handling and numerical work
- **requests / BeautifulSoup** — scraping and API calls
- **openpyxl** — structured Excel logging
- **python-dotenv** — secret management
- Concurrent odds fetching with a thread pool
- Unit tests for the Markov mathematics (`test_markov.py`)

---

## Running it

```bash
# 1. Clone and enter the project
git clone https://github.com/saviodambrosio/tennis-scanner.git
cd tennis-scanner

# 2. Create the virtual environment
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# then edit .env with your own API keys

# 5. Run the scanner
python main.py

# Run the model validation
python valida_modelli.py

# Run the Markov unit tests
python test_markov.py
```

### Configuration

Key settings in `config.py`:

| Setting | Description |
|---|---|
| `MODELLO` | `"elo"` or `"markov"` — which model to use |
| `EV_MINIMO` | Minimum expected value to flag a bet (e.g. `0.09`) |
| `MARKOV_ETA_SUPERFICIE` | Toggle the age × surface adjustment |
| `TELEGRAM_ABILITATO` | Master switch for Telegram notifications |

API keys and tokens are read from a `.env` file (never committed).

---

## What I'd do differently / future directions

The honest CLV result points to where a *real* edge might live — none of it accessible through public pre-match data:

- **Illiquid markets** (ITF / minor Challengers) where bookmakers use cruder models and make genuine pricing errors
- **Line-movement signals** — following sharp money in the minutes after a market opens, rather than competing with the closing price
- **Proprietary data** — injury signals, travel/scheduling effects priced before the market reacts

The point-by-point model would be far more interesting deployed against a lazy bookmaker on a 15k ITF event than against Pinnacle on an ATP match.

---

## Disclaimer

This is a research and portfolio project. It is **not** betting advice, and its own central finding is that the strategy does not produce a profitable edge against efficient markets. Gamble responsibly, if at all.

---

**Author:** [saviodambrosio](https://github.com/saviodambrosio)
**License:** MIT
