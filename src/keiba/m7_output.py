"""M7 出力・UIモジュール。

Streamlit導入は未着手（技術候補止まり）。まずCLI表示とCSV出力で運用できる形にする。
買い目候補の券種別優先順位・資金配分ルールは未確定のため、暫定として
「単勝=1位のみ、複勝=1-2位、馬連=1-3位のボックス」を採用する。正式なルールが
決まったら recommend_bets() を差し替えること。

内訳の列はM6の breakdown キーから動的に生成する（M6にファクターを追加/削除しても
本モジュールの変更は不要）。
"""

import csv
from itertools import combinations
from pathlib import Path

from keiba.m6_scoring import ScoreResult

FACTOR_LABELS = {
    "odds": "オッズ",
    "weight_stability": "馬体重",
    "jockey": "騎手",
    "trainer": "調教師",
    "paddock": "パドック",
    "class_fit": "クラス昇降",
    "recent_form": "近走成績",
}


def _factor_keys(results: list[ScoreResult]) -> list[str]:
    return list(results[0].breakdown.keys()) if results else []


def format_ranking_table(results: list[ScoreResult]) -> str:
    if not results:
        return ""
    factors = _factor_keys(results)
    header_labels = "/".join(FACTOR_LABELS.get(k, k) for k in factors)
    lines = [f"{'順位':>4} {'馬番':>4} {'馬名':<14} {'スコア':>7}  内訳({header_labels})"]
    for r in results:
        breakdown_str = "/".join(f"{r.breakdown.get(k, 0):5.1f}" for k in factors)
        lines.append(f"{r.rank:>4} {r.horse_number:>4} {r.horse_name:<14} {r.total_score:>7.2f}  {breakdown_str}")
    return "\n".join(lines)


def recommend_bets(results: list[ScoreResult]) -> dict[str, list]:
    ranked = sorted(results, key=lambda r: r.rank)
    top1 = [r.horse_number for r in ranked[:1]]
    top2 = [r.horse_number for r in ranked[:2]]
    top3 = [r.horse_number for r in ranked[:3]]
    return {
        "単勝": top1,
        "複勝": top2,
        "馬連(BOX)": [list(c) for c in combinations(sorted(top3), 2)],
    }


def format_bet_recommendation(results: list[ScoreResult]) -> str:
    bets = recommend_bets(results)
    lines = ["--- 買い目候補（暫定ロジック） ---"]
    lines.append(f"単勝: {bets['単勝']}")
    lines.append(f"複勝: {bets['複勝']}")
    lines.append(f"馬連(BOX): {bets['馬連(BOX)']}")
    return "\n".join(lines)


def print_report(results: list[ScoreResult]) -> None:
    if not results:
        print("スコア対象の出走馬がありません。")
        return
    print(f"=== {results[0].race_id} 予想ランキング ===")
    print(format_ranking_table(results))
    print()
    print(format_bet_recommendation(results))


def export_csv(results: list[ScoreResult], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    factors = _factor_keys(results)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "horse_number", "horse_name", "total_score", *factors])
        for r in results:
            writer.writerow([r.rank, r.horse_number, r.horse_name, r.total_score, *(r.breakdown.get(k) for k in factors)])
