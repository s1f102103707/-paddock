"""M4 手動パドック評価入力モジュール。

採点基準表は未確定（仕様書11章オープン課題）。暫定仕様として models.py の
PADDOCK_ITEMS（毛艶・発汗・歩くリズム、各-2〜+2）を採用。
正式な基準表が決まったら、この暫定値を差し替えること。
"""

from keiba.models import PADDOCK_ITEM_MAX, PADDOCK_ITEM_MIN, PADDOCK_ITEMS, PaddockManualScore


def make_score(race_id: str, horse_number: int, item_scores: dict[str, int], note: str = "") -> PaddockManualScore:
    """入力値を採点基準の範囲・項目名でバリデーションしてPaddockManualScoreを生成する。"""
    unknown = set(item_scores) - set(PADDOCK_ITEMS)
    if unknown:
        raise ValueError(f"未定義の評価項目です: {sorted(unknown)}（定義済み項目: {PADDOCK_ITEMS}）")
    for item, score in item_scores.items():
        if not (PADDOCK_ITEM_MIN <= score <= PADDOCK_ITEM_MAX):
            raise ValueError(f"項目'{item}'の点数{score}が範囲外です（{PADDOCK_ITEM_MIN}〜{PADDOCK_ITEM_MAX}）")
    return PaddockManualScore(race_id=race_id, horse_number=horse_number, item_scores=dict(item_scores), note=note)


def prompt_score_cli(race_id: str, horse_number: int, horse_name: str) -> PaddockManualScore:
    """対話的にパドック評価を入力する簡易CLI（Streamlit導入前の暫定UI）。"""
    print(f"\n--- {horse_name}（{horse_number}番）のパドック評価 ---")
    item_scores: dict[str, int] = {}
    for item in PADDOCK_ITEMS:
        while True:
            raw = input(f"{item} ({PADDOCK_ITEM_MIN}〜{PADDOCK_ITEM_MAX}): ").strip()
            try:
                score = int(raw)
            except ValueError:
                print("整数で入力してください。")
                continue
            if not (PADDOCK_ITEM_MIN <= score <= PADDOCK_ITEM_MAX):
                print(f"{PADDOCK_ITEM_MIN}〜{PADDOCK_ITEM_MAX}の範囲で入力してください。")
                continue
            item_scores[item] = score
            break
    note = input("メモ（任意）: ").strip()
    return make_score(race_id, horse_number, item_scores, note)
