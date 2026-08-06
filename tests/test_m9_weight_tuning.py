import random

from keiba.demo_data import BacktestFixture
from keiba.m5_feature_integration import FeatureRow
from keiba.m6_scoring import DEFAULT_WEIGHTS
from keiba.m9_weight_tuning import (
    _random_simplex_weights,
    build_tuning_result,
    evaluate_weights,
    random_search,
)
from keiba.models import Odds, RaceResult


def _sample_fixture() -> BacktestFixture:
    features = [
        FeatureRow("R1", 1, "A", implied_prob=0.6, weight_change_pct=0.0, jockey_win_rate=0.2, trainer_win_rate=0.2, paddock_score_normalized=1.0, class_fit=0.5, recent_form=80.0),
        FeatureRow("R1", 2, "B", implied_prob=0.1, weight_change_pct=5.0, jockey_win_rate=0.05, trainer_win_rate=0.05, paddock_score_normalized=-1.0, class_fit=-1.0, recent_form=20.0),
        FeatureRow("R1", 3, "C", implied_prob=0.3, weight_change_pct=1.0, jockey_win_rate=0.1, trainer_win_rate=0.1, paddock_score_normalized=0.0, class_fit=0.0, recent_form=50.0),
    ]
    results = [RaceResult("R1", 1, 1), RaceResult("R1", 2, 3), RaceResult("R1", 3, 2)]
    odds = [Odds("R1", 1, 3.0, 1.2, 1.5), Odds("R1", 2, 8.0, 2.0, 3.0), Odds("R1", 3, 5.0, 1.5, 2.0)]
    return BacktestFixture(race_id="R1", features=features, results=results, odds=odds)


def test_random_simplex_weights_sums_to_one():
    rng = random.Random(0)
    weights = _random_simplex_weights(list(DEFAULT_WEIGHTS.keys()), rng)
    assert set(weights) == set(DEFAULT_WEIGHTS)
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert all(v >= 0 for v in weights.values())


def test_evaluate_weights_runs_backtest():
    fixture = _sample_fixture()
    report = evaluate_weights([fixture], DEFAULT_WEIGHTS)
    assert report.race_count == 1
    assert report.win.bets == 1


def test_build_tuning_result_matches_evaluate_weights():
    fixture = _sample_fixture()
    result = build_tuning_result([fixture], DEFAULT_WEIGHTS)
    assert result.weights == DEFAULT_WEIGHTS
    assert result.objective == result.report.win.roi + result.report.win.hit_rate


def test_random_search_returns_sorted_results():
    fixture = _sample_fixture()
    results = random_search([fixture], n_trials=20, seed=1)
    assert len(results) == 20
    objectives = [r.objective for r in results]
    assert objectives == sorted(objectives, reverse=True)
    for r in results:
        assert abs(sum(r.weights.values()) - 1.0) < 1e-9
