"""Phase 1 MVPパイプラインの動作確認用CLI（M7の暫定UI）。

使い方:
    python -m keiba.cli run             # サンプルレースをスコアリングして表示
    python -m keiba.cli run --csv out.csv
    python -m keiba.cli backtest-demo   # 合成データでM8バックテストの動作確認
"""

import argparse

from keiba.demo_data import generate_backtest_cases
from keiba.m1_data_source import MockDataSource
from keiba.m5_feature_integration import build_features
from keiba.m6_scoring import score_race
from keiba.m7_output import export_csv, print_report
from keiba.m8_backtest import format_backtest_report, run_backtest


def cmd_run(args: argparse.Namespace) -> None:
    source = MockDataSource()
    card = source.fetch_race_card(args.race_id)
    jockey_rates = {e.jockey: source.fetch_jockey_stats(e.jockey).win_rate for e in card.entries}
    trainer_rates = {e.trainer: source.fetch_trainer_stats(e.trainer).win_rate for e in card.entries}
    past_performances = {e.horse_name: source.fetch_past_performances(e.horse_name) for e in card.entries}

    features = build_features(card, jockey_rates, trainer_rates, paddock_scores=None, past_performances_by_horse=past_performances)
    results = score_race(features)
    print_report(results)

    if args.csv:
        export_csv(results, args.csv)
        print(f"\nCSV出力: {args.csv}")


def cmd_backtest_demo(args: argparse.Namespace) -> None:
    print("※ 実過去データが未入手のため、合成データでパイプラインの動作確認のみ行います。")
    cases = generate_backtest_cases(n_races=args.races)
    report = run_backtest(cases)
    print(format_backtest_report(report))


def main() -> None:
    parser = argparse.ArgumentParser(description="競馬予想支援ツール Phase 1 MVP CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="サンプルレースをスコアリングして表示")
    p_run.add_argument("--race-id", default="SAMPLE-2026-01")
    p_run.add_argument("--csv", default=None, help="スコアをCSVに出力するパス")
    p_run.set_defaults(func=cmd_run)

    p_bt = sub.add_parser("backtest-demo", help="合成データでM8バックテストの動作確認")
    p_bt.add_argument("--races", type=int, default=20)
    p_bt.set_defaults(func=cmd_backtest_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
