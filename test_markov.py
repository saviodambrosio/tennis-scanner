# -*- coding: utf-8 -*-
"""
Test unitari per la matematica del modello Markov.

Casi noti:
  - prob_game(0.5) == 0.5          (simmetria)
  - prob_game(1.0) == 1.0
  - prob_game(0.0) == 0.0
  - prob_tiebreak(0.5) == 0.5      (simmetria)
  - prob_set(pa, pb) con pa=pb_break -> ~0.5
  - prob_match(0.5) == 0.5
  - prob_match(0.5, best_of=5) == 0.5
  - prob_match(1.0) == 1.0
  - prob_match(0.0) == 0.0
  - calcola_probabilita_markov con elo_A==elo_B -> ~0.5
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.markov import (
    prob_game, prob_tiebreak, prob_set, prob_match,
    calcola_probabilita_markov, AVG_ELO_TA
)

EPSILON = 1e-9
APPROX = 1e-4  # tolleranza numerica per confronti floating-point


def assert_approx(actual, expected, tol=APPROX, label=""):
    ok = abs(actual - expected) < tol
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {label}: {actual:.6f} (atteso {expected})")
    if not ok:
        raise AssertionError(f"FAIL: {label} ->{actual:.6f} != {expected} (tol={tol})")


def test_prob_game():
    print("\n--- test_prob_game ---")
    # Simmetria: p=0.5 ->P(game)=0.5
    assert_approx(prob_game(0.5), 0.5, label="prob_game(0.5)==0.5")
    # Certezze
    assert_approx(prob_game(1.0), 1.0, label="prob_game(1.0)==1.0")
    assert_approx(prob_game(0.0), 0.0, label="prob_game(0.0)==0.0")
    # Valore noto: p=0.637 (media ATP hard) ->hold ~80%
    pg = prob_game(0.637)
    assert 0.78 < pg < 0.83, f"prob_game(0.637)={pg:.4f} fuori range [0.78, 0.83]"
    print(f"  [OK] prob_game(0.637)={pg:.4f} (range atteso 0.78-0.83)")
    # Monotonicità: p grande ->P(game) grande
    assert prob_game(0.7) > prob_game(0.6) > prob_game(0.5)
    print("  [OK] monotonicità verificata")


def test_prob_tiebreak():
    print("\n--- test_prob_tiebreak ---")
    assert_approx(prob_tiebreak(0.5), 0.5, label="prob_tiebreak(0.5)==0.5")
    # p > 0.5 ->prob > 0.5
    pt = prob_tiebreak(0.6)
    assert pt > 0.5, f"prob_tiebreak(0.6)={pt:.4f} deve essere >0.5"
    print(f"  [OK] prob_tiebreak(0.6)={pt:.4f} > 0.5")
    # p < 0.5 ->prob < 0.5
    pt_low = prob_tiebreak(0.4)
    assert pt_low < 0.5, f"prob_tiebreak(0.4)={pt_low:.4f} deve essere <0.5"
    print(f"  [OK] prob_tiebreak(0.4)={pt_low:.4f} < 0.5")


def test_prob_set():
    print("\n--- test_prob_set ---")
    # Giocatori identici: pa=pb_break ->P(set) ≈ 0.5
    pg = prob_game(0.637)
    pb = 1.0 - pg  # break prob uguale a hold prob dell'avversario (identici)
    ps = prob_set(pg, pb)
    # Con giocatori identici e alternanza simmetrica, deve essere ≈ 0.5
    assert_approx(ps, 0.5, tol=0.01, label="prob_set uguale ->~0.5")
    # Dominatore: pa altissima E pb_break altissima -> A vince quasi ogni game
    # pa=0.99: A tiene quasi sempre; pb_break=0.99: A fa break quasi sempre
    ps_dom = prob_set(0.99, 0.99)
    assert ps_dom > 0.98, f"prob_set dominatore={ps_dom:.4f}"
    print(f"  [OK] prob_set dominatore (pa=pb_break=0.99)={ps_dom:.4f} > 0.98")


def test_prob_match():
    print("\n--- test_prob_match ---")
    assert_approx(prob_match(0.5, best_of=3), 0.5, label="prob_match(0.5, bo3)==0.5")
    assert_approx(prob_match(0.5, best_of=5), 0.5, label="prob_match(0.5, bo5)==0.5")
    assert_approx(prob_match(1.0, best_of=3), 1.0, label="prob_match(1.0)==1.0")
    assert_approx(prob_match(0.0, best_of=3), 0.0, label="prob_match(0.0)==0.0")
    # Monotonicità
    assert prob_match(0.7) > prob_match(0.6) > prob_match(0.5)
    print("  [OK] monotonicità prob_match verificata")
    # bo5 più estremo di bo3 per ps ≠ 0.5
    assert prob_match(0.7, 5) > prob_match(0.7, 3)
    print("  [OK] best-of-5 più estremo di best-of-3 per p > 0.5")


def test_calcola_probabilita_markov():
    print("\n--- test_calcola_probabilita_markov ---")
    # Elo identici ->prob ≈ 0.5
    pm = calcola_probabilita_markov(AVG_ELO_TA, AVG_ELO_TA, 'hard', best_of=3)
    assert_approx(pm, 0.5, tol=0.01, label="Elo identici ->~0.5 (hard)")

    pm_clay = calcola_probabilita_markov(AVG_ELO_TA, AVG_ELO_TA, 'clay', best_of=3)
    assert_approx(pm_clay, 0.5, tol=0.01, label="Elo identici ->~0.5 (clay)")

    pm_grass = calcola_probabilita_markov(AVG_ELO_TA, AVG_ELO_TA, 'grass', best_of=3)
    assert_approx(pm_grass, 0.5, tol=0.01, label="Elo identici ->~0.5 (grass)")

    # Elo maggiore ->prob > 0.5
    pm_better = calcola_probabilita_markov(AVG_ELO_TA + 200, AVG_ELO_TA, 'hard')
    assert pm_better > 0.5, f"Elo +200 deve dare prob > 0.5, got {pm_better}"
    print(f"  [OK] Elo+200 ->{pm_better:.4f} > 0.5")

    # Simmetria: P(A|elo_A>elo_B) + P(B|elo_B<elo_A) ≈ 1
    pm_a = calcola_probabilita_markov(1900, 1700, 'hard')
    pm_b = calcola_probabilita_markov(1700, 1900, 'hard')
    assert_approx(pm_a + pm_b, 1.0, tol=0.01, label="Simmetria: P(A)+P(B)≈1")

    # Adjustments: fatica riduce la prob
    adj_fat = {'fatica_A': -0.02, 'fatica_B': 0.0}
    pm_fat = calcola_probabilita_markov(AVG_ELO_TA + 200, AVG_ELO_TA, 'hard',
                                        adjustments=adj_fat)
    assert pm_fat < pm_better, f"Fatica deve ridurre prob: {pm_fat} >= {pm_better}"
    print(f"  [OK] Fatica A riduce prob: {pm_better:.4f} ->{pm_fat:.4f}")


def test_best_of_5():
    print("\n--- test_best_of_5 ---")
    pm3 = calcola_probabilita_markov(1900, 1700, 'hard', best_of=3)
    pm5 = calcola_probabilita_markov(1900, 1700, 'hard', best_of=5)
    # Bo5 amplifica il vantaggio ->prob più alta per il favorito
    assert pm5 > pm3, f"Bo5 deve amplificare vantaggio: {pm5:.4f} vs {pm3:.4f}"
    print(f"  [OK] Bo5({pm5:.4f}) > Bo3({pm3:.4f}) per favorito")


def test_superficie():
    print("\n--- test_superficie ---")
    # Su erba (più veloce) il vantaggio del servitore forte è maggiore
    pm_hard = calcola_probabilita_markov(1900, 1700, 'hard')
    pm_grass = calcola_probabilita_markov(1900, 1700, 'grass')
    pm_clay = calcola_probabilita_markov(1900, 1700, 'clay')
    print(f"  Prob (hard={pm_hard:.4f}, clay={pm_clay:.4f}, grass={pm_grass:.4f})")
    # Su clay SPW è più bassa ->meno dominato dal servizio ->differenza più piccola
    # Su grass SPW è più alta ->più break difficili ->vantaggio Elo si esprime di meno sul servizio


if __name__ == "__main__":
    print("=" * 60)
    print("  TEST MODELLO MARKOV TENNIS")
    print("=" * 60)
    try:
        test_prob_game()
        test_prob_tiebreak()
        test_prob_set()
        test_prob_match()
        test_calcola_probabilita_markov()
        test_best_of_5()
        test_superficie()
        print("\n" + "=" * 60)
        print("  TUTTI I TEST SUPERATI ✅")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n❌ ERRORE: {e}")
        sys.exit(1)
