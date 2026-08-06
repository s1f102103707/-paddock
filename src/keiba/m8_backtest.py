"""M8 バックテスト・検証モジュール。

過去レースの統合特徴量・実際の結果・確定オッズを用いて、M7の買い目候補ロジックを
適用した場合の的中率・回収率(ROI)を集計する。券種は現時点でM7が対応する単勝・複勝のみ。
"""

from dataclasses import dataclass, field

from keiba.m6_scoring import ScoreResult
from keiba.m7_output import recommend_bets
from keiba.models import Odds, RaceResult

STAKE_PER_BET = 100  # 円


@dataclass(frozen=True)
class BacktestCase:
    race_id: str
    scores: list[ScoreResult]
    results: list[RaceResult]
    odds: list[Odds]


@dataclass(frozen=True)
class BetTypeReport:
    bets: int
    hits: int
    stake_total: int
    payout_total: float

    @property
    def hit_rate(self) -> float:
        return self.hits / self.bets if self.bets else 0.0

    @property
    def roi(self) -> float:
        """回収率(%)。100%超で期待値上プラス。"""
        return (self.payout_total / self.stake_total * 100) if self.stake_total else 0.0


@dataclass(frozen=True)
class BacktestReport:
    race_count: int
    win: BetTypeReport
    place: BetTypeReport
    per_race_detail: list[dict] = field(default_factory=list)


def run_backtest(cases: list[BacktestCase]) -> BacktestReport:
    win_bets = win_hits = win_stake = 0
    win_payout = 0.0
    place_bets = place_hits = place_stake = 0
    place_payout = 0.0
    detail = []

    for case in cases:
        result_by_horse = {r.horse_number: r.finish_position for r in case.results}
        odds_by_horse = {o.horse_number: o for o in case.odds}
        bets = recommend_bets(case.scores)

        race_detail = {"race_id": case.race_id, "win_hit": False, "place_hits": []}

        for horse in bets["単勝"]:
            win_bets += 1
            win_stake += STAKE_PER_BET
            if result_by_horse.get(horse) == 1:
                win_hits += 1
                win_payout += STAKE_PER_BET * odds_by_horse[horse].win_odds
                race_detail["win_hit"] = True

        for horse in bets["複勝"]:
            place_bets += 1
            place_stake += STAKE_PER_BET
            if result_by_horse.get(horse, 99) <= 3:
                place_hits += 1
                o = odds_by_horse[horse]
                avg_place_odds = (o.place_odds_low + o.place_odds_high) / 2
                place_payout += STAKE_PER_BET * avg_place_odds
                race_detail["place_hits"].append(horse)

        detail.append(race_detail)

    return BacktestReport(
        race_count=len(cases),
        win=BetTypeReport(win_bets, win_hits, win_stake, win_payout),
        place=BetTypeReport(place_bets, place_hits, place_stake, place_payout),
        per_race_detail=detail,
    )


def format_backtest_report(report: BacktestReport) -> str:
    lines = [
        f"=== バックテスト結果（対象レース数: {report.race_count}） ===",
        f"単勝: {report.win.bets}件中{report.win.hits}件的中"
        f"（的中率{report.win.hit_rate * 100:.1f}%, 回収率{report.win.roi:.1f}%）",
        f"複勝: {report.place.bets}件中{report.place.hits}件的中"
        f"（的中率{report.place.hit_rate * 100:.1f}%, 回収率{report.place.roi:.1f}%）",
    ]
    return "\n".join(lines)
