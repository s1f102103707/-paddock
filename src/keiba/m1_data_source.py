"""M1 基礎データ収集モジュール。

JV-Link（Windows/ActiveX/COM）経由の実データ取得は未実装。JRA-VAN利用キーの
取得・DataLab契約が完了し、pywin32等でのCOM呼び出し部分を実装できる段階になったら
`JVLinkDataSource` を追加し、`DataSource` を継承させること。

それまでは `MockDataSource` を使い、M4以降のロジックを環境非依存で開発・検証する
（CLAUDE.md コーディング指針: データ取得部分はモック化）。ここで返す値は架空の
サンプルデータであり、実在するJRAレース・馬とは無関係。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from keiba.models import BodyWeight, Entry, JockeyTrainerStats, Odds, PastPerformance, Race


@dataclass
class RaceCard:
    race: Race
    entries: list[Entry]
    body_weights: list[BodyWeight]
    odds: list[Odds]


class DataSource(ABC):
    @abstractmethod
    def fetch_race_card(self, race_id: str) -> RaceCard: ...

    @abstractmethod
    def fetch_jockey_stats(self, jockey: str) -> JockeyTrainerStats: ...

    @abstractmethod
    def fetch_trainer_stats(self, trainer: str) -> JockeyTrainerStats: ...

    @abstractmethod
    def fetch_past_performances(self, horse_name: str) -> list[PastPerformance]: ...


class MockDataSource(DataSource):
    """開発・テスト用の架空データソース。JV-Link未接続でもパイプライン全体を動かせる。"""

    def __init__(self):
        self._race_cards: dict[str, RaceCard] = {}
        self._jockey_win_rates: dict[str, float] = {}
        self._trainer_win_rates: dict[str, float] = {}
        self._past_performances: dict[str, list[PastPerformance]] = {}
        self._seed_sample_data()

    def register_race_card(self, card: RaceCard) -> None:
        self._race_cards[card.race.race_id] = card

    def fetch_race_card(self, race_id: str) -> RaceCard:
        try:
            return self._race_cards[race_id]
        except KeyError:
            raise ValueError(f"race_id={race_id!r} のサンプルデータが登録されていません") from None

    def fetch_jockey_stats(self, jockey: str) -> JockeyTrainerStats:
        return JockeyTrainerStats(name=jockey, win_rate=self._jockey_win_rates.get(jockey, 0.10))

    def fetch_trainer_stats(self, trainer: str) -> JockeyTrainerStats:
        return JockeyTrainerStats(name=trainer, win_rate=self._trainer_win_rates.get(trainer, 0.10))

    def fetch_past_performances(self, horse_name: str) -> list[PastPerformance]:
        return self._past_performances.get(horse_name, [])

    def _seed_sample_data(self) -> None:
        race = Race(
            race_id="SAMPLE-2026-01",
            date="2026-08-01",
            course="サンプル競馬場",
            distance=1800,
            race_class="3勝クラス",
            weather="晴",
            track_condition="良",
        )
        entries = [
            Entry("SAMPLE-2026-01", 1, "サンプルホースA", 4, "牡", "騎手A", "調教師A", 57.0, "父A", "母A", "母父A"),
            Entry("SAMPLE-2026-01", 2, "サンプルホースB", 3, "牝", "騎手B", "調教師B", 54.0, "父B", "母B", "母父B"),
            Entry("SAMPLE-2026-01", 3, "サンプルホースC", 5, "牡", "騎手C", "調教師C", 58.0, "父C", "母C", "母父C"),
        ]
        body_weights = [
            BodyWeight("SAMPLE-2026-01", 1, 480, -4),
            BodyWeight("SAMPLE-2026-01", 2, 452, 2),
            BodyWeight("SAMPLE-2026-01", 3, 500, 8),
        ]
        odds = [
            Odds("SAMPLE-2026-01", 1, 3.5, 1.4, 1.8),
            Odds("SAMPLE-2026-01", 2, 5.2, 1.9, 2.6),
            Odds("SAMPLE-2026-01", 3, 12.0, 3.0, 4.5),
        ]
        self.register_race_card(RaceCard(race, entries, body_weights, odds))
        self._jockey_win_rates.update({"騎手A": 0.18, "騎手B": 0.12, "騎手C": 0.08})
        self._trainer_win_rates.update({"調教師A": 0.15, "調教師B": 0.10, "調教師C": 0.07})

        # 過去成績: Aは絶好調で1クラス上に挑戦、Bは平凡な近走で1クラス上、
        # Cはオープンからの格下げで近走は不振（クラス昇降と近走成績の対比サンプル）。
        self._past_performances.update(
            {
                "サンプルホースA": [
                    PastPerformance("サンプルホースA", "2026-06-01", 1, 1800, 106.5, 34.2, "2勝クラス", "良"),
                    PastPerformance("サンプルホースA", "2026-05-01", 2, 2000, 121.0, 35.0, "2勝クラス", "良"),
                    PastPerformance("サンプルホースA", "2026-04-01", 1, 1800, 107.0, 34.5, "1勝クラス", "稍重"),
                ],
                "サンプルホースB": [
                    PastPerformance("サンプルホースB", "2026-06-01", 3, 1600, 95.0, 35.5, "3勝クラス", "良"),
                    PastPerformance("サンプルホースB", "2026-05-01", 5, 1800, 108.0, 36.0, "3勝クラス", "重"),
                    PastPerformance("サンプルホースB", "2026-04-01", 2, 1800, 107.2, 35.0, "2勝クラス", "良"),
                ],
                "サンプルホースC": [
                    PastPerformance("サンプルホースC", "2026-06-01", 6, 2000, 122.0, 37.0, "オープン", "良"),
                    PastPerformance("サンプルホースC", "2026-05-01", 4, 1800, 108.5, 36.5, "オープン", "良"),
                    PastPerformance("サンプルホースC", "2026-04-01", 5, 2000, 122.5, 37.2, "3勝クラス", "稍重"),
                ],
            }
        )
