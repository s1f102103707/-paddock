"""M6 スコアリング・予測モデルモジュール（Phase 1: ルールベース）。

採点基準はJV-Data（JRA-VAN経由で取得可能な基礎データ）で裏付けられる定量ファクターを
主軸に据える。具体的には:
    - オッズ(実勢人気度)                        … JV-Data オッズ
    - 馬体重の安定度                             … JV-Data 馬体重
    - 騎手/調教師成績                            … JV-Data 騎手・調教師データ
    - クラス昇降・近走成績(スピード指数近似)     … JV-Data 過去成績（着順/タイム/上がり3ハロン/クラス）
これに、JV-Dataでは取得できない手動パドック評価(M4)を組み合わせる。
血統は父・母・母父の「名前」だけでは強さを定量化できず、産駒成績等の外部データベースが
別途必要になるため、Phase 1のファクターには含めない（m5_feature_integration.py参照）。

重みはユーザー指定で「オッズ⇔パドック」を入れ替え、残りをクラス昇降・近走成績を
新設した分だけ他ファクターから配分し直した暫定値（合計1.0）。バックテスト(M8)の
結果を見ながら調整すること。
"""

from dataclasses import dataclass, field

from keiba.m5_feature_integration import FeatureRow

DEFAULT_WEIGHTS = {
    "paddock": 0.35,
    "odds": 0.25,
    "recent_form": 0.12,
    "class_fit": 0.10,
    "jockey": 0.08,
    "weight_stability": 0.05,
    "trainer": 0.05,
}


@dataclass(frozen=True)
class ScoreResult:
    race_id: str
    horse_number: int
    horse_name: str
    total_score: float  # 0-100
    breakdown: dict[str, float] = field(default_factory=dict)  # 各ファクターの寄与(点)
    rank: int = 0


def _min_max_normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [0.5 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def score_race(features: list[FeatureRow], weights: dict[str, float] | None = None) -> list[ScoreResult]:
    """1レース分の特徴量から出走馬ごとのスコアを算出し、スコア降順でランキングを付与する。"""
    if not features:
        return []
    weights = weights or DEFAULT_WEIGHTS

    normalized = {
        "odds": _min_max_normalize([f.implied_prob for f in features]),
        "weight_stability": _min_max_normalize([-abs(f.weight_change_pct) for f in features]),
        "jockey": _min_max_normalize([f.jockey_win_rate for f in features]),
        "trainer": _min_max_normalize([f.trainer_win_rate for f in features]),
        "paddock": _min_max_normalize([f.paddock_score_normalized for f in features]),
        "class_fit": _min_max_normalize([f.class_fit for f in features]),
        "recent_form": _min_max_normalize([f.recent_form for f in features]),
    }

    results = []
    for i, f in enumerate(features):
        breakdown = {factor: weights[factor] * normalized[factor][i] * 100 for factor in weights}
        total = sum(breakdown.values())
        results.append(
            ScoreResult(
                race_id=f.race_id,
                horse_number=f.horse_number,
                horse_name=f.horse_name,
                total_score=round(total, 2),
                breakdown={k: round(v, 2) for k, v in breakdown.items()},
            )
        )

    results.sort(key=lambda r: r.total_score, reverse=True)
    return [
        ScoreResult(r.race_id, r.horse_number, r.horse_name, r.total_score, r.breakdown, rank=i + 1)
        for i, r in enumerate(results)
    ]
