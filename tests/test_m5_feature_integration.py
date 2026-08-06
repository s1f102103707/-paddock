from keiba.m1_data_source import MockDataSource
from keiba.m4_paddock_eval import make_score
from keiba.m5_feature_integration import build_features
from keiba.models import PADDOCK_ITEM_MAX, PADDOCK_ITEMS


def test_build_features_basic():
    source = MockDataSource()
    card = source.fetch_race_card("SAMPLE-2026-01")
    jockey_rates = {e.jockey: source.fetch_jockey_stats(e.jockey).win_rate for e in card.entries}
    trainer_rates = {e.trainer: source.fetch_trainer_stats(e.trainer).win_rate for e in card.entries}

    rows = build_features(card, jockey_rates, trainer_rates)

    assert len(rows) == len(card.entries)
    assert abs(sum(r.implied_prob for r in rows) - 1.0) < 1e-9
    # 馬体重-4kg、前走480kgなので変化率は負
    horse1 = next(r for r in rows if r.horse_number == 1)
    assert horse1.weight_change_pct < 0


def test_build_features_missing_paddock_score_is_neutral():
    source = MockDataSource()
    card = source.fetch_race_card("SAMPLE-2026-01")
    jockey_rates = {e.jockey: 0.1 for e in card.entries}
    trainer_rates = {e.trainer: 0.1 for e in card.entries}

    score = make_score("SAMPLE-2026-01", 1, {item: PADDOCK_ITEM_MAX for item in PADDOCK_ITEMS})
    rows = build_features(card, jockey_rates, trainer_rates, paddock_scores={1: score})

    horse1 = next(r for r in rows if r.horse_number == 1)
    horse2 = next(r for r in rows if r.horse_number == 2)
    assert horse1.paddock_score_normalized == 1.0  # 全項目満点評価
    assert horse2.paddock_score_normalized == 0.0  # 未評価は中立


def test_build_features_class_fit_and_recent_form_from_past_performances():
    source = MockDataSource()
    card = source.fetch_race_card("SAMPLE-2026-01")  # 現在のクラスは「3勝クラス」
    jockey_rates = {e.jockey: 0.1 for e in card.entries}
    trainer_rates = {e.trainer: 0.1 for e in card.entries}
    past_performances = {e.horse_name: source.fetch_past_performances(e.horse_name) for e in card.entries}

    rows = build_features(card, jockey_rates, trainer_rates, past_performances_by_horse=past_performances)

    horse_a = next(r for r in rows if r.horse_number == 1)  # 近走絶好調、1クラス上に挑戦
    horse_c = next(r for r in rows if r.horse_number == 3)  # オープンからの格下げ、近走不振

    assert horse_a.class_fit < 0  # 格上挑戦なので不利
    assert horse_c.class_fit > 0  # クラス下げなので有利
    assert horse_a.recent_form > horse_c.recent_form  # 近走成績はAの方が良い


def test_build_features_no_past_performance_is_neutral():
    source = MockDataSource()
    card = source.fetch_race_card("SAMPLE-2026-01")
    jockey_rates = {e.jockey: 0.1 for e in card.entries}
    trainer_rates = {e.trainer: 0.1 for e in card.entries}

    rows = build_features(card, jockey_rates, trainer_rates)  # past_performances_by_horse未指定

    assert all(r.class_fit == 0.0 and r.recent_form == 0.0 for r in rows)
