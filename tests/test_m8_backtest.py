from keiba.m6_scoring import ScoreResult
from keiba.m8_backtest import BacktestCase, run_backtest
from keiba.models import Odds, RaceResult


def test_run_backtest_single_race_win_hit():
    scores = [
        ScoreResult("R1", 1, "A", 90.0, {}, rank=1),
        ScoreResult("R1", 2, "B", 50.0, {}, rank=2),
        ScoreResult("R1", 3, "C", 30.0, {}, rank=3),
    ]
    results = [RaceResult("R1", 1, 1), RaceResult("R1", 2, 2), RaceResult("R1", 3, 3)]
    odds = [Odds("R1", 1, 3.0, 1.2, 1.5), Odds("R1", 2, 5.0, 1.5, 2.0), Odds("R1", 3, 10.0, 2.0, 3.0)]

    report = run_backtest([BacktestCase("R1", scores, results, odds)])

    assert report.win.bets == 1
    assert report.win.hits == 1
    assert report.win.payout_total == 300  # 100円 x 3.0倍
    assert report.win.roi == 300.0

    assert report.place.bets == 2  # 複勝は上位2頭
    assert report.place.hits == 2  # 1位・2位はともに3着以内


def test_run_backtest_no_hit_gives_zero_roi():
    scores = [ScoreResult("R1", 1, "A", 90.0, {}, rank=1), ScoreResult("R1", 2, "B", 50.0, {}, rank=2)]
    results = [RaceResult("R1", 1, 4), RaceResult("R1", 2, 5)]
    odds = [Odds("R1", 1, 3.0, 1.2, 1.5), Odds("R1", 2, 5.0, 1.5, 2.0)]

    report = run_backtest([BacktestCase("R1", scores, results, odds)])

    assert report.win.hits == 0
    assert report.win.roi == 0.0
