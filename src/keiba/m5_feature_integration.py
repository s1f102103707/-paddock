"""M5 特徴量統合・前処理モジュール。

M1（基礎データ・過去成績）・M4（手動パドック評価）を出走馬単位で結合し、欠損値処理・
派生特徴量の生成を行う。M3（パドックAI歩様特徴量）はPhase 2以降のため未統合。

血統評価は、JV-Dataの父・母・母父の「名前」だけでは血統的な強さを定量化できず
（父系の産駒成績等の外部データベースが別途必要）、Phase 1の対応範囲外とする。
一方でクラス昇降・近走成績（スピード指数近似）はJV-Dataの過去成績（着順・タイム・
上がり3ハロン・クラス）から算出可能なため、本モジュールで追加した。
"""

from dataclasses import dataclass

from keiba.m1_data_source import RaceCard
from keiba.models import (
    PADDOCK_ITEM_MAX,
    PADDOCK_ITEM_MIN,
    PADDOCK_ITEMS,
    PastPerformance,
    PaddockManualScore,
    class_level,
)

PADDOCK_SCORE_MIN = PADDOCK_ITEM_MIN * len(PADDOCK_ITEMS)
PADDOCK_SCORE_MAX = PADDOCK_ITEM_MAX * len(PADDOCK_ITEMS)

RECENT_RACES_WINDOW = 3  # 近走何走分を集計対象にするか


@dataclass(frozen=True)
class FeatureRow:
    race_id: str
    horse_number: int
    horse_name: str
    implied_prob: float  # オッズから算出した勝率相当（過剰配当分を除去して正規化）
    weight_change_pct: float  # 前走からの馬体重変化率(%)
    jockey_win_rate: float
    trainer_win_rate: float
    paddock_score_normalized: float  # -1.0〜1.0 に正規化した手動パドック評価
    class_fit: float  # 直近クラス平均 - 今回クラス（正=クラスが楽、負=格上挑戦）
    recent_form: float  # 近走の着順・上がり3ハロンから算出した簡易スピード指数近似


def _implied_probabilities(win_odds_by_horse: dict[int, float]) -> dict[int, float]:
    raw = {h: 1.0 / o for h, o in win_odds_by_horse.items() if o > 0}
    total = sum(raw.values())
    if total == 0:
        return {h: 0.0 for h in win_odds_by_horse}
    return {h: v / total for h, v in raw.items()}


def _class_fit(current_class: str, past_performances: list[PastPerformance]) -> float:
    """クラス昇降。直近走の平均クラスが今回より低ければ正（今回は楽）、高ければ負（格上挑戦）。"""
    recent = past_performances[:RECENT_RACES_WINDOW]
    if not recent:
        return 0.0
    avg_level = sum(class_level(p.race_class) for p in recent) / len(recent)
    return avg_level - class_level(current_class)


def _recent_form(past_performances: list[PastPerformance]) -> float:
    """近走成績（スピード指数近似）。着順の良さと上がり3ハロンの速さを近走分集計する。

    実際のJRA-VAN等が提供するスピード指数（コース・馬場差補正込みの走破時計指数）は
    より精緻だが、Phase 1では過去成績のみから算出できる簡易近似とする。
    """
    recent = past_performances[:RECENT_RACES_WINDOW]
    if not recent:
        return 0.0
    finish_component = sum(1.0 / p.finish_position for p in recent if p.finish_position > 0) / len(recent)
    last3f_component = sum(1.0 / p.last_3f_seconds for p in recent if p.last_3f_seconds > 0) / len(recent)
    return finish_component * 100 + last3f_component * 100


def build_features(
    card: RaceCard,
    jockey_win_rates: dict[str, float],
    trainer_win_rates: dict[str, float],
    paddock_scores: dict[int, PaddockManualScore] | None = None,
    past_performances_by_horse: dict[str, list[PastPerformance]] | None = None,
) -> list[FeatureRow]:
    """1レース分の出走馬について特徴量テーブルを構築する。

    paddock_scores未指定の馬は「未評価」として中立値(0.0)を割り当てる
    （M4評価はPhase1でも任意入力を許容する運用のため、欠損値処理として扱う）。
    past_performances_by_horse未指定（デビュー戦等で過去成績が無い場合を含む）の馬も
    同様にclass_fit/recent_formを中立値(0.0)とする。
    """
    paddock_scores = paddock_scores or {}
    past_performances_by_horse = past_performances_by_horse or {}
    win_odds_by_horse = {o.horse_number: o.win_odds for o in card.odds}
    implied = _implied_probabilities(win_odds_by_horse)
    bw_by_horse = {bw.horse_number: bw for bw in card.body_weights}

    rows = []
    for entry in card.entries:
        bw = bw_by_horse.get(entry.horse_number)
        if bw is not None and bw.weight > 0:
            prev_weight = bw.weight - bw.weight_diff
            weight_change_pct = (bw.weight_diff / prev_weight * 100) if prev_weight > 0 else 0.0
        else:
            weight_change_pct = 0.0

        score = paddock_scores.get(entry.horse_number)
        if score is not None:
            span = PADDOCK_SCORE_MAX - PADDOCK_SCORE_MIN
            paddock_norm = (2 * (score.total - PADDOCK_SCORE_MIN) / span - 1) if span else 0.0
        else:
            paddock_norm = 0.0

        past_performances = past_performances_by_horse.get(entry.horse_name, [])

        rows.append(
            FeatureRow(
                race_id=card.race.race_id,
                horse_number=entry.horse_number,
                horse_name=entry.horse_name,
                implied_prob=implied.get(entry.horse_number, 0.0),
                weight_change_pct=weight_change_pct,
                jockey_win_rate=jockey_win_rates.get(entry.jockey, 0.0),
                trainer_win_rate=trainer_win_rates.get(entry.trainer, 0.0),
                paddock_score_normalized=paddock_norm,
                class_fit=_class_fit(card.race.race_class, past_performances),
                recent_form=_recent_form(past_performances),
            )
        )
    return rows
