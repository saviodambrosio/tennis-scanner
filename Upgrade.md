# TASK: Sostituire il modello Elo con un modello point-by-point Markov

## CONTESTO
Questo è un progetto di scanner per value betting sul tennis (TENNIS_BET_CALCULATOR).
Struttura attuale:
- `scanner.py` — scanner Money Line
- `scanner_handicap.py` — scanner Handicap
- `main.py` — lancia entrambi
- `config.py` — configurazione
- `modules/` — moduli (contiene la logica Elo)
- Dati Elo presi da Tennis Abstract

Attualmente la probabilità di vittoria è stimata via Elo con la funzione
`calcola_probabilita_elo()`. Il modello Elo dà un edge insufficiente (CLV medio
+1.38%, sotto la soglia di break-even ~+2.5%). Serve un salto di classe di modello.

## PRIMA DI SCRIVERE CODICE
1. Esplora tutto il codebase e mappa dove viene chiamata `calcola_probabilita_elo()`
2. Leggi il PLAN.md per il contesto completo del progetto
3. NON cancellare il modello Elo — mantienilo come fallback e per confronto A/B

## OBIETTIVO PUNTO 13: Modello Markov point-by-point

Implementare un modello che simula la partita punto per punto invece di ridurla
a un singolo rating differenziale.

### Dati necessari (da Tennis Abstract)
Per ogni giocatore, per superficie (clay/hard/grass):
- Service Points Won % (SPW)
- Return Points Won % (RPW)
Scaricare e cachare come già si fa per l'Elo (cache 24h, decay esponenziale
per dare più peso ai match recenti).

### Matematica del modello
Per un match A vs B su una data superficie:

1. Probabilità che A vinca un punto al proprio servizio (approccio Barnett-Clarke):
   p_A_serve = AVG_SPW + (SPW_A - AVG_SPW) - (RPW_B - AVG_RPW)
   p_B_serve = AVG_SPW + (SPW_B - AVG_SPW) - (RPW_A - AVG_RPW)
   dove AVG_SPW e AVG_RPW sono le medie del circuito sulla superficie.

2. Probabilità di tenere il servizio (game), dato p = prob punto al servizio:
   P(game) = p^4 + 4·p^4·(1-p) + 10·p^4·(1-p)^2
           + 20·p^3·(1-p)^3 · [p^2 / (p^2 + (1-p)^2)]

3. Probabilità di vincere un set: catena di Markov sugli stati di game
   (0-0 fino a 6-6), con tiebreak a 6-6. Il tiebreak è una catena analoga
   (primo a 7 punti, scarto di 2).

4. Probabilità di vincere il match: best-of-3
   P(match) = pS^2 · (3 - 2·pS)   dove pS = P(vincere un set)
   (prevedere anche best-of-5 per gli Slam, parametrizzabile)

### Output
Nuova funzione `calcola_probabilita_markov(player_A, player_B, surface, best_of=3)`
che restituisce P(A vince) — stessa interfaccia logica di `calcola_probabilita_elo()`
così da minimizzare le modifiche allo scanner.

## OBIETTIVO PUNTO 14: Adjustment contestuali

Aggiungere come correzioni alle probabilità di punto al servizio (NON come tweak
empirici post-hoc). Renderli attivabili/disattivabili da config.py:

1. **Court Pace Index (CPI)**: superfici diverse hanno velocità diverse anche
   a parità di tipo. Campi veloci → bonus ai servitori forti. Se non si trova
   una fonte CPI affidabile, lasciare il parametro a 0 (neutro) e documentarlo.

2. **Fatica estesa**: contare i set giocati negli ultimi 14 giorni (non solo 24h).
   Penalità progressiva sulla prob. di punto.

3. **Time zone change**: differenza di fuso tra torneo precedente e attuale del
   giocatore. Penalità se cambio >3 fusi negli ultimi 3 giorni.

4. **Età × superficie**: interazione età/superficie (gli over-33 calano più
   sull'erba). Coefficiente da stimare su dati storici.

## VINCOLI
- Mantenere intatta l'infrastruttura: scanner, threading parallelo quote,
  invio Telegram, formato Excel di output, filtro range quote
- Il modello Markov deve essere selezionabile da config.py
  (es. `MODELLO = "markov"` o `"elo"`) per poter fare confronti A/B
- Codice commentato e con docstring
- Aggiungere test unitari per la matematica del Markov (casi noti:
  p=0.5 deve dare P(game)=0.5, ecc.)

## VALIDAZIONE
Dopo l'implementazione, su un set di match storici confrontare:
- Probabilità Elo vs Probabilità Markov vs Probabilità implicita dalle quote
- Quale dei due modelli è più vicino alle quote di chiusura (closing line)

## RIFERIMENTI
- Klaassen & Magnus, "Analyzing Wimbledon" — base teorica del modello
- Tennis Abstract — fonte dati serve/return per superficie