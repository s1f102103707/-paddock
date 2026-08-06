"""Phase 1 MVPパイプラインの動作確認用CLI（M7の暫定UI）。

使い方:
    python -m keiba.cli run             # サンプルレースをスコアリングして表示
    python -m keiba.cli run --csv out.csv
    python -m keiba.cli backtest-demo   # 合成データでM8バックテストの動作確認
    python -m keiba.cli tune-weights    # 合成データで重み探索の仕組みを動作確認
"""

import argparse

from keiba.demo_data import generate_backtest_cases, generate_backtest_fixtures
from keiba.m1_data_source import MockDataSource
from keiba.m5_feature_integration import build_features
from keiba.m6_scoring import DEFAULT_WEIGHTS, score_race
from keiba.m7_output import export_csv, print_report
from keiba.m8_backtest import format_backtest_report, run_backtest
from keiba.m9_weight_tuning import build_tuning_result, format_tuning_summary, random_search


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


def cmd_tune_weights(args: argparse.Namespace) -> None:
    print(
        "※ 合成データは『オッズを基準にした疑似的な強さ』で結果を生成しているため、"
        "この探索は『オッズを最重視すべき』という自明な結論に偏ります。"
        "仕組みの動作確認用であり、実際の重み調整には実過去データが必要です。\n"
    )
    fixtures = generate_backtest_fixtures(n_races=args.races)
    baseline = build_tuning_result(fixtures, DEFAULT_WEIGHTS)
    results = random_search(fixtures, n_trials=args.trials)
    print(format_tuning_summary(baseline, results, top_n=args.top))


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

    p_tune = sub.add_parser("tune-weights", help="合成データで重み探索(M9)の仕組みを動作確認")
    p_tune.add_argument("--races", type=int, default=30)
    p_tune.add_argument("--trials", type=int, default=200)
    p_tune.add_argument("--top", type=int, default=5)
    p_tune.set_defaults(func=cmd_tune_weights)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
