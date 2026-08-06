"""バックテスト(M8)の動作確認用シード付き合成データ生成。

実際の過去レース結果（的中率・回収率検証に必須）はまだ入手できていないため
（オープン課題: JV-Data経由の履歴データ取得、または別途CSV入手）、パイプライン
自体が正しく動くことを確認するための架空データをここで生成する。実データが
入手できたら、このモジュール経由ではなくM1から取得したデータでbacktestを行うこと。
"""

import random
from dataclasses import dataclass

from keiba.m1_data_source import RaceCard
from keiba.m6_scoring import score_race
from keiba.m5_feature_integration import FeatureRow, build_features
from keiba.m8_backtest import BacktestCase
from keiba.models import CLASS_LEVELS, BodyWeight, Entry, Odds, PastPerformance, Race, RaceResult


@dataclass(frozen=True)
class BacktestFixture:
    """スコア計算前の特徴量ベースの合成データ1レース分。

    重み探索(m9_weight_tuning)では、レースデータそのものは再生成せず、この特徴量に
    対して異なる重みでscore_race()を繰り返し呼び出すことで高速に多数の重みを評価する。
    """

    race_id: str
    features: list[FeatureRow]
    results: list[RaceResult]
    odds: list[Odds]


def _synthesize_race(race_index: int, rng: random.Random) -> tuple[RaceCard, list[RaceResult], dict[str, list[PastPerformance]]]:
    race_id = f"DEMO-{race_index:03d}"
    n_horses = rng.randint(3, 8)
    race = Race(
        race_id=race_id,
        date="2026-01-01",
        course="デモ競馬場",
        distance=rng.choice([1200, 1600, 1800, 2000]),
        race_class="デモクラス",
        weather="晴",
        track_condition="良",
    )
    entries, body_weights, odds_list = [], [], []
    win_odds_values = sorted(rng.uniform(1.5, 30.0) for _ in range(n_horses))
    rng.shuffle(win_odds_values)
    for i in range(1, n_horses + 1):
        entries.append(
            Entry(race_id, i, f"デモ馬{i}", rng.randint(3, 7), rng.choice(["牡", "牝"]), f"騎手{i}", f"調教師{i}", 55.0, "父", "母", "母父")
        )
        diff = rng.randint(-8, 8)
        body_weights.append(BodyWeight(race_id, i, rng.randint(420, 520), diff))
        win_odds = win_odds_values[i - 1]
        odds_list.append(Odds(race_id, i, win_odds, 1.0 + win_odds * 0.15, 1.0 + win_odds * 0.35))

    win_odds_by_horse = {o.horse_number: o.win_odds for o in odds_list}

    # 人気(オッズが低い=implied_probが高い)ほど上位に来やすいように、疑似的な強さで並べ替える。
    # 過去成績用のability（下記）とは別の乱数を使い、「今回のレース特有の当日の巡り合わせ」を表す。
    strength = {e.horse_number: rng.random() / win_odds_by_horse[e.horse_number] for e in entries}
    finish_order = sorted(strength, key=lambda h: strength[h], reverse=True)
    results = [RaceResult(race_id, horse, pos + 1) for pos, horse in enumerate(finish_order)]

    # 過去成績は「オッズにある程度相関する潜在的な実力」を表す別系統の乱数から生成する
    # （今回のレース結果(strength)とは別の乱数のため、直接のリークにはならない）。
    ability = {e.horse_number: rng.random() / win_odds_by_horse[e.horse_number] for e in entries}
    ability_order = sorted(ability, key=lambda h: ability[h], reverse=True)
    ability_rank = {horse: pos + 1 for pos, horse in enumerate(ability_order)}
    past_performances_by_horse: dict[str, list[PastPerformance]] = {}
    class_names = list(CLASS_LEVELS.keys())
    for entry in entries:
        rank = ability_rank[entry.horse_number]
        pps = []
        for k in range(2):
            finish = max(1, min(n_horses, round(rank + rng.uniform(-1.5, 1.5))))
            last_3f = 33.5 + rank * 0.25 + rng.uniform(-0.4, 0.4)
            time_seconds = race.distance / 16.5 + rng.uniform(-1.5, 1.5)
            pps.append(
                PastPerformance(
                    entry.horse_name, f"2025-{k + 1:02d}-01", finish, race.distance, time_seconds, last_3f, rng.choice(class_names), "良"
                )
            )
        past_performances_by_horse[entry.horse_name] = pps

    return RaceCard(race, entries, body_weights, odds_list), results, past_performances_by_horse


def generate_backtest_fixtures(n_races: int = 20, seed: int = 42) -> list[BacktestFixture]:
    rng = random.Random(seed)
    fixtures = []
    for i in range(1, n_races + 1):
        card, results, past_performances = _synthesize_race(i, rng)
        jockey_rates = {e.jockey: rng.uniform(0.05, 0.20) for e in card.entries}
        trainer_rates = {e.trainer: rng.uniform(0.05, 0.20) for e in card.entries}
        features = build_features(card, jockey_rates, trainer_rates, paddock_scores=None, past_performances_by_horse=past_performances)
        fixtures.append(BacktestFixture(race_id=card.race.race_id, features=features, results=results, odds=card.odds))
    return fixtures


def generate_backtest_cases(n_races: int = 20, seed: int = 42, weights: dict[str, float] | None = None) -> list[BacktestCase]:
    fixtures = generate_backtest_fixtures(n_races, seed)
    return [
        BacktestCase(race_id=f.race_id, scores=score_race(f.features, weights), results=f.results, odds=f.odds)
        for f in fixtures
    ]
