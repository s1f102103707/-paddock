"""M6の重み(DEFAULT_WEIGHTS)を探索するための補助モジュール（暫定・簡易版）。

重要な注意: 現時点で使える合成データ(demo_data.py)は、オッズを基準に疑似的な
「強さ」を作って結果を生成しているため、この仕組みで探索すると
「オッズに全重みを置くのが最適」という自明な結論に偏る。これはこの合成データの
生成方法そのものが原因であり、探索の仕組み自体の問題ではない。
実際に意味のある重み調整を行うには、m8_backtest.BacktestCase相当のデータを
実際の過去レース結果（M1実データ）から構築し、そちらに対して探索を行うこと。
"""

import math
import random
from dataclasses import dataclass

from keiba.m6_scoring import DEFAULT_WEIGHTS, score_race
from keiba.m8_backtest import BacktestCase, BacktestReport, run_backtest

# fixturesは race_id / features(m5_feature_integration.FeatureRowのリスト) / results / odds
# の4属性を持つオブジェクトであればよい（demo_data.BacktestFixture、または将来の実データ版）。


@dataclass(frozen=True)
class TuningResult:
    weights: dict[str, float]
    report: BacktestReport
    objective: float


def _random_simplex_weights(keys: list[str], rng: random.Random) -> dict[str, float]:
    """各キーの重みの合計が1.0になるようにランダムサンプリングする（単体上の一様分布）。

    指数分布からのサンプルを正規化することで単体上の一様分布が得られる（標準的な手法）。
    """
    draws = {k: -math.log(rng.random()) for k in keys}
    total = sum(draws.values())
    return {k: v / total for k, v in draws.items()}


def evaluate_weights(fixtures: list, weights: dict[str, float]) -> BacktestReport:
    cases = [
        BacktestCase(race_id=f.race_id, scores=score_race(f.features, weights), results=f.results, odds=f.odds)
        for f in fixtures
    ]
    return run_backtest(cases)


def objective(report: BacktestReport) -> float:
    """探索の目的関数（暫定）。単勝回収率(%)を主指標とし、的中率をわずかなタイブレークに使う。

    正式な評価指標（回収率と的中率のどちらをどの程度重視するか）が決まったら、
    仕様書10章の評価指標に合わせて更新すること。
    """
    return report.win.roi + report.win.hit_rate


def build_tuning_result(fixtures: list, weights: dict[str, float]) -> TuningResult:
    report = evaluate_weights(fixtures, weights)
    return TuningResult(weights=weights, report=report, objective=objective(report))


def random_search(
    fixtures: list,
    n_trials: int = 200,
    seed: int = 42,
    weight_keys: list[str] | None = None,
) -> list[TuningResult]:
    """ランダムサーチでn_trials件の重み候補を評価し、目的関数の降順で返す。"""
    rng = random.Random(seed)
    keys = weight_keys or list(DEFAULT_WEIGHTS.keys())
    results = [build_tuning_result(fixtures, _random_simplex_weights(keys, rng)) for _ in range(n_trials)]
    results.sort(key=lambda r: r.objective, reverse=True)
    return results


def format_tuning_summary(baseline: TuningResult, results: list[TuningResult], top_n: int = 5) -> str:
    def _fmt(r: TuningResult) -> str:
        weight_str = ", ".join(f"{k}={v:.2f}" for k, v in r.weights.items())
        return f"単勝回収率={r.report.win.roi:6.1f}% 的中率={r.report.win.hit_rate * 100:5.1f}%  重み: {weight_str}"

    lines = [
        "=== 現行重み(DEFAULT_WEIGHTS) ===",
        _fmt(baseline),
        "",
        f"=== ランダムサーチ上位{top_n}件（全{len(results)}件中） ===",
    ]
    for i, r in enumerate(results[:top_n], start=1):
        lines.append(f"{i}. {_fmt(r)}")
    return "\n".join(lines)
