"""M1〜M6で共通利用するデータモデル（仕様書 6章の入出力データ項目に対応）。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Race:
    race_id: str
    date: str  # ISO形式 YYYY-MM-DD
    course: str
    distance: int  # メートル
    race_class: str
    weather: str
    track_condition: str  # 良/稍重/重/不良


@dataclass(frozen=True)
class Entry:
    """出走馬情報（仕様書 6.1 出走馬情報）。"""

    race_id: str
    horse_number: int
    horse_name: str
    age: int
    sex: str
    jockey: str
    trainer: str
    weight_carried: float  # 斤量(kg)
    sire: str
    dam: str
    dam_sire: str


@dataclass(frozen=True)
class BodyWeight:
    race_id: str
    horse_number: int
    weight: int  # 当日馬体重(kg)
    weight_diff: int  # 前走からの増減(kg)


@dataclass(frozen=True)
class Odds:
    race_id: str
    horse_number: int
    win_odds: float  # 単勝
    place_odds_low: float  # 複勝(下限)
    place_odds_high: float  # 複勝(上限)


@dataclass(frozen=True)
class JockeyTrainerStats:
    """騎手・調教師の当該距離・馬場等での成績（簡易統計。M5で参照）。"""

    name: str
    win_rate: float  # 0.0-1.0


# --- M4 手動パドック評価入力 ---
#
# 採点基準の正式な加点/減点表はユーザー未確定のため、暫定仕様として以下を採用する:
#   各項目 -2 (悪い) 〜 +2 (良い) の5段階。
# 項目は「気配・状態系」（レースごとに変動する当日の状態）と「馬体系」（脚・胴・
# 筋肉量など、比較的変化の少ない体型的特徴）の2グループで構成する。
# 正式な採点基準表が決まったら各タプルと採点範囲をここで更新すること。
PADDOCK_CONDITION_ITEMS = ("気配", "毛艶", "気合い", "発汗", "落ち着き", "歩くリズム")
PADDOCK_CONFORMATION_ITEMS = ("脚の長さ", "胴の長さ", "トモの筋肉量", "胸前の筋肉")
PADDOCK_ITEMS = PADDOCK_CONDITION_ITEMS + PADDOCK_CONFORMATION_ITEMS
PADDOCK_ITEM_MIN = -2
PADDOCK_ITEM_MAX = 2


@dataclass(frozen=True)
class PaddockManualScore:
    race_id: str
    horse_number: int
    item_scores: dict[str, int] = field(default_factory=dict)  # PADDOCK_ITEMS -> 点数
    note: str = ""

    @property
    def total(self) -> int:
        return sum(self.item_scores.values())


@dataclass(frozen=True)
class RaceResult:
    """バックテスト(M8)用の確定結果。"""

    race_id: str
    horse_number: int
    finish_position: int


@dataclass(frozen=True)
class PastPerformance:
    """出走馬の過去成績1走分（仕様書 6.1 過去成績。JV-Data由来）。M6のクラス昇降・
    近走成績（スピード指数近似）の算出に用いる。"""

    horse_name: str
    race_date: str
    finish_position: int
    distance: int
    time_seconds: float
    last_3f_seconds: float  # 上がり3ハロン
    race_class: str
    track_condition: str


# クラスの強さを数値化する簡易テーブル（M6のクラス昇降算出に使用）。
# 不明なクラス名は中位（2勝クラス相当）として扱う。
CLASS_LEVELS = {
    "未勝利": 0,
    "1勝クラス": 1,
    "2勝クラス": 2,
    "3勝クラス": 3,
    "オープン": 4,
    "OP": 4,
    "G3": 5,
    "G2": 6,
    "G1": 7,
}
CLASS_LEVEL_DEFAULT = 2


def class_level(race_class: str) -> int:
    return CLASS_LEVELS.get(race_class, CLASS_LEVEL_DEFAULT)
