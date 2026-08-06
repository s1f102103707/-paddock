from keiba.m5_feature_integration import FeatureRow
from keiba.m6_scoring import score_race


def test_score_race_ranks_by_score_descending():
    features = [
        FeatureRow(
            "R1", 1, "A", implied_prob=0.6, weight_change_pct=0.0, jockey_win_rate=0.2, trainer_win_rate=0.2,
            paddock_score_normalized=1.0, class_fit=0.5, recent_form=80.0,
        ),
        FeatureRow(
            "R1", 2, "B", implied_prob=0.1, weight_change_pct=5.0, jockey_win_rate=0.05, trainer_win_rate=0.05,
            paddock_score_normalized=-1.0, class_fit=-1.0, recent_form=20.0,
        ),
        FeatureRow(
            "R1", 3, "C", implied_prob=0.3, weight_change_pct=1.0, jockey_win_rate=0.1, trainer_win_rate=0.1,
            paddock_score_normalized=0.0, class_fit=0.0, recent_form=50.0,
        ),
    ]
    results = score_race(features)

    assert [r.horse_number for r in results] == [1, 3, 2]
    assert [r.rank for r in results] == [1, 2, 3]
    for r in results:
        # 各内訳値は個別に小数第2位で四捨五入するため、合計との誤差は丸め誤差の範囲に収まればよい
        assert abs(sum(r.breakdown.values()) - r.total_score) < 0.05


def test_score_race_empty_input():
    assert score_race([]) == []


def test_score_race_all_equal_does_not_crash():
    features = [
        FeatureRow(
            "R1", i, f"H{i}", implied_prob=0.5, weight_change_pct=0.0, jockey_win_rate=0.1, trainer_win_rate=0.1,
            paddock_score_normalized=0.0, class_fit=0.0, recent_form=0.0,
        )
        for i in range(1, 4)
    ]
    results = score_race(features)
    assert len(results) == 3
    assert all(r.total_score == results[0].total_score for r in results)
